"""Source-backed free meals/groceries; never confuse free admission with free food."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from threading import Lock
import time
import httpx
from bs4 import BeautifulSoup
from .events import BOSTON, HEADERS, fetch_bytes, geocode, get_events, EventsUnavailable

AB='https://abfoodpantry.com/services/'
FRIDAY='https://www.fridaynightsupper.org/be-our-guest'
# Manually reviewed source summaries, not a complete directory or live stock feed.
REGISTRY=[
 {'id':'ab-hot-meal','title':'Allston Brighton · hot meal & groceries','resource_type':'meal','address':'404 Washington Street, Brighton, MA 02135','source_url':AB,'food_offer':'Freshly prepared hot takeout meal and a bag of groceries.','full_meal':True,'eligibility':'Provider welcomes everyone; no proof of need required.','schedule_note':'Published Wednesday distribution: 3–6 PM. Confirm holiday changes with the provider.','weekday':2,'hours':(15,18)},
 {'id':'ab-fridge','title':'Allston-Brighton Community Fridge','resource_type':'fridge','address':'404 Washington Street, Brighton, MA 02135','source_url':AB,'food_offer':'Self-service donated food and pantry items. Contents vary; a prepared meal is not guaranteed.','full_meal':None,'eligibility':'Provider describes self-service access for the community.','schedule_note':'Provider lists 24/7 access. Stock and fridge operation are not monitored.','weekday':None,'hours':None},
 {'id':'ab-groceries','title':'Allston Brighton · grocery pickup','resource_type':'groceries','address':'404 Washington Street, Brighton, MA 02135','source_url':AB,'food_offer':'Fresh groceries for cooking; pantry baskets also have a separate Saturday schedule.','full_meal':False,'eligibility':'Provider welcomes everyone; no proof of need required.','schedule_note':'Wednesday 3–6 PM. Saturday pickup times must be checked with the provider.','weekday':2,'hours':(15,18)},
 {'id':'friday-supper','title':'Friday Night Supper · free prepared dinner','resource_type':'meal','address':'351 Boylston Street, Boston, MA 02116','source_url':FRIDAY,'food_offer':'Prepared dinner service; soup and drinks are also described. Exact menu changes.','full_meal':True,'eligibility':'Everyone welcome. Provider says no registration or sign-up is required.','schedule_note':'Published Friday service: 5–7 PM, lower level of Arlington Street Church. Confirm changes before travel.','weekday':4,'hours':(17,19)}]
_cache=None
_attempt=0.
_lock=Lock()


def free_food_evidence(text):
    """High precision English phrases only; free-entry and donation drives do not qualify."""
    import re
    text=' '.join(text.split())
    for sentence in re.split(r'(?<=[.!?])\s+|[\n\r]+',text):
        if re.search(r'\b(no|not|without|cannot|can\x27t|never|donate|donations)\b',sentence,re.I):
            continue
        if re.search(r'\b(food drive|fundraiser|donation drive)\b',sentence,re.I):
            continue
        match=re.search(r'\b(?:free|complimentary)\s+(?:(?:hot|prepared|takeout|community)\s+)?(meals?|food|lunch|dinner|breakfast|groceries|snacks?|refreshments)\b',sentence,re.I)
        if match:
            kind=match.group(1).lower()
            return {'evidence': ' '.join(sentence.split()[:25]),'full_meal':kind in ['meal','meals','lunch','dinner','breakfast'],'offer_kind':kind}
    return None


def next_service(record,now):
    if record['weekday'] is None:
        return now,now+timedelta(days=7)
    day=now.date()+timedelta(days=(record['weekday']-now.weekday())%7)
    start=datetime.combine(day,datetime.min.time(),tzinfo=BOSTON).replace(hour=record['hours'][0])
    end=start.replace(hour=record['hours'][1])
    if end<=now:
        start+=timedelta(days=7);end+=timedelta(days=7)
    return start,end


def _source_check(client,url):
    try:
        text=BeautifulSoup(fetch_bytes(client,url,2*1024*1024),'html.parser').get_text(' ',strip=True).lower()
        if url==AB:
            return all(x in text for x in ['hot meal','free community fridge','3–6pm'])
        return all(x in text for x in ['free nutritious meal','5:00pm-7:00pm'])
    except (httpx.HTTPError,ValueError):
        return False


def get_food_resources(refresh=False):
    global _cache,_attempt
    with _lock:
        if _cache is None or time.monotonic()-_attempt >= (60 if refresh else 300):
            _attempt=time.monotonic()
            now=datetime.now(timezone.utc)
            with httpx.Client(timeout=8,headers=HEADERS,follow_redirects=False) as client:
                urls=list(dict.fromkeys(r['source_url'] for r in REGISTRY))
                with ThreadPoolExecutor(max_workers=2) as pool:
                    checked=dict(zip(urls,pool.map(lambda url:_source_check(client,url),urls)))
                addresses=list(dict.fromkeys(r['address'] for r in REGISTRY))
                with ThreadPoolExecutor(max_workers=2) as pool:
                    points=dict(zip(addresses,pool.map(lambda address:geocode(client,address),addresses)))
            _cache={'checks':checked,'points':points,'checked_at':now.isoformat()}
        snapshot=deepcopy(_cache)
    now=datetime.now(BOSTON)
    items=[]
    for record in REGISTRY:
        start,end=next_service(record,now)
        confirmed=snapshot['checks'][record['source_url']]
        items.append({**{k:v for k,v in record.items() if k not in ('weekday','hours')},'start_at':start.isoformat(),'end_at':end.isoformat(),
                      'category':record['resource_type'],'virtual':False,'cancelled':False,'source':'Provider-published program',
                      'coordinates':snapshot['points'][record['address']], 'source_status':'source_matches_reviewed_details' if confirmed else 'needs_recheck',
                      'schedule_basis':'Recurring published schedule; not a verified booking or live opening status',
                      'reviewed_on':'2026-11-17','source_checked_at':snapshot['checked_at'], 'stock_status':'unknown','calories_kcal':None})
    warning=None
    event_count=0
    try:
        city=get_events(force_refresh=refresh)
        for event in city['events']:
            if not event.get('free_food') or event['cancelled']:
                continue
            event_count+=1
            items.append({**event,'resource_type':'event','category':'event','food_offer':'Organizer text explicitly mentions '+event['free_food']['offer_kind']+'.',
                          'full_meal':event['free_food']['full_meal'],'eligibility':'Check event registration and eligibility with the organizer.',
                          'schedule_note':'One-off event from the city feed. Confirm food arrangements before attending.',
                          'source_status':'event_feed_evidence','source_checked_at':city['fetched_at'], 'evidence':event['free_food']['evidence'],
                          'stock_status':'unknown','calories_kcal':None})
        if city['status']=='stale': warning='City event refresh failed; dated listings may be out of date.'
    except EventsUnavailable:
        warning='City event feed unavailable. Showing reviewed provider programs only.'
    return {'events':items,'status':'partial' if warning or not all(snapshot['checks'].values()) else 'updated',
            'warning':warning,'fetched_at':snapshot['checked_at'],'refresh_interval_seconds':300,
            'free_food_event_count':event_count,'timezone':'America/New_York',
            'coverage_note':'Reviewed Boston food programs plus city events explicitly mentioning free food. Free entry alone does not qualify.',
            'freshness_note':'Published schedules and source checks only. No live food stock, menu, holiday opening or food-safety guarantee.',
            'source_url':'https://www.boston.gov/departments/food-justice/food-resources',
            'directories':[{'title':'Boston food resource directory','url':'https://www.boston.gov/departments/food-justice/food-resources'},
                           {'title':'Project Bread · find meals and groceries','url':'https://projectbread.org/get-help'}]}
