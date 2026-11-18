"""Keyless Boston.gov RSS + Census geocoding. Never invent events or coordinates."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import re
from threading import Lock
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
import httpx

BOSTON = ZoneInfo('America/New_York')
FEED_URL = 'https://www.boston.gov/rss/events'
GEOCODER_URL = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
HEADERS = {'User-Agent': 'PantryStudioCourseProject/0.4 (Boston public events reader)'}
REFRESH_SECONDS = 300
MIN_REFRESH_SECONDS = 60
_lock = Lock()
_snapshot = None
_last_attempt = 0.0
_last_error = False
_coordinates = {}


class EventsUnavailable(Exception):
    pass


def official_url(value):
    parsed = urlsplit(value or '')
    return value if parsed.scheme == 'https' and parsed.netloc == 'www.boston.gov' else None


def parse_local_time(node):
    """The feed's visible local clock can disagree with its UTC-suffixed attribute."""
    text = node.get_text(' ', strip=True)
    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}:\d{2})(am|pm)', text, re.I)
    if not match:
        return None
    day, clock, marker = match.groups()
    month, date, year = map(int, day.split('/'))
    hour, minute = map(int, clock.split(':'))
    if not 1 <= hour <= 12 or not 0 <= minute <= 59:
        return None
    hour = hour % 12 + (12 if marker.lower() == 'pm' else 0)
    try:
        naive = datetime(year, month, date, hour, minute)
        first = naive.replace(tzinfo=BOSTON, fold=0)
        second = naive.replace(tzinfo=BOSTON, fold=1)
        # An ambiguous or nonexistent DST clock cannot safely become an exact instant.
        if first.utcoffset() != second.utcoffset():
            return None
        return first
    except ValueError:
        return None


def category_for(title, department):
    text = (title+' '+department).lower()
    if re.search(r'\b(bike|bikes|cycling|walk|walking|run|running|yoga|fitness|sports|hike|hiking)\b', text):
        return 'movement'
    if re.search(r'\b(food|cooking|cook|farmers|market|nutrition|garden|gardening)\b', text):
        return 'food'
    if re.search(r'\b(art|artist|music|poetry|poet|verse|freeverse|dance|film|theater|museum|culture)\b', text):
        return 'culture'
    return 'community'


def parse_feed(content):
    root = ElementTree.fromstring(content)
    items = root.findall('./channel/item')
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Unexpected event feed format')
    events, seen, skipped = [], set(), 0
    for item in items[:100]:
        title = (item.findtext('title') or '').strip()
        url = official_url(item.findtext('link'))
        soup = BeautifulSoup(item.findtext('description') or '', 'html.parser')
        dates = soup.select('.date-recur-date time')
        start = parse_local_time(dates[0]) if dates else None
        end = parse_local_time(dates[1]) if len(dates) > 1 else None
        if not title or not url or not start:
            skipped += 1
            continue
        key = (url, start.isoformat())
        if key in seen:
            continue
        seen.add(key)
        address_node = soup.select_one('.address')
        address = address_node.get_text(', ', strip=True) if address_node else ''
        address = re.sub(r'\s*,\s*,+', ', ', address).replace(', United States', '').strip(' ,')
        virtual = bool(re.search(r'virtual|zoom|online|by phone|phone only', address, re.I))
        department_node = item.find('{http://purl.org/dc/elements/1.1/}creator')
        department = ''.join(department_node.itertext()).strip() if department_node is not None else ''
        department = BeautifulSoup(department, 'html.parser').get_text(' ', strip=True)
        # Derive an address query only from numbered street lines, not a venue or city name.
        street = None
        if address_node and not virtual:
            for node in address_node.select('.address-line1, .address-line2'):
                candidate = node.get_text(' ', strip=True)
                if re.match(r'^\d+[\w-]*\s+\S', candidate):
                    street = candidate
                    break
        locality = address_node.select_one('.locality') if address_node else None
        state = address_node.select_one('.administrative-area') if address_node else None
        postal = address_node.select_one('.postal-code') if address_node else None
        query = ', '.join([street, locality.get_text(strip=True) if locality else 'Boston',
                           state.get_text(strip=True) if state else 'MA', postal.get_text(strip=True) if postal else '']) if street else None
        from .food_resources import free_food_evidence
        evidence = free_food_evidence(title+' '+soup.get_text(' ', strip=True).split('Contact Department:')[0])
        events.append({'free_food': evidence, 'id': hashlib.sha256('|'.join(key).encode()).hexdigest()[:20],
                       'title': title, 'source_url': url, 'source': 'City of Boston',
                       'start_at': start.isoformat(), 'end_at': end.isoformat() if end and end > start else None,
                       'time_basis': 'Visible event clock interpreted in America/New_York; feed UTC attributes may disagree.',
                       'address': address or 'Location not supplied', 'virtual': virtual,
                       'category': category_for(title, department), 'department': department,
                       'cancelled': bool(re.search(r'\bcancel(?:led|ed|lation)\b', title, re.I)),
                       'coordinates': None, 'location_status': 'online' if virtual else 'not_located',
                       '_geocode_query': query})
    return events, {'feed_items': len(items), 'unique_events': len(events), 'skipped_invalid_items': skipped,
                    'duplicates_removed': len(items)-len(events)-skipped}


def fetch_bytes(client, url, limit):
    with client.stream('GET', url) as response:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > limit:
                raise ValueError('Upstream response exceeds limit')
        return bytes(content)


def geocode(client, query):
    now = time.monotonic()
    if query in _coordinates and now < _coordinates[query][0]:
        return _coordinates[query][1]
    result = None
    try:
        response = client.get(GEOCODER_URL, params={'address': query, 'benchmark': 'Public_AR_Current', 'format': 'json'}, timeout=4)
        response.raise_for_status()
        matches = response.json().get('result', {}).get('addressMatches', [])
        # Ambiguous matches stay unplaced. Census street-range coordinates are approximate.
        if len(matches) == 1:
            match = matches[0]
            latitude, longitude = float(match['coordinates']['y']), float(match['coordinates']['x'])
            if 42.1 <= latitude <= 42.6 and -71.4 <= longitude <= -70.8:
                result = {'latitude': latitude, 'longitude': longitude, 'source': 'U.S. Census Geocoder',
                          'accuracy': 'Approximate street-range match, not an entrance or route',
                          'matched_address': match.get('matchedAddress')}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        pass
    if len(_coordinates) >= 512:
        _coordinates.clear()
    _coordinates[query] = (now+(86400 if result else REFRESH_SECONDS), result)
    return result


def _refresh(client):
    content = fetch_bytes(client, FEED_URL, 2*1024*1024)
    events, counts = parse_feed(content)
    now = datetime.now(timezone.utc)
    queries = list(dict.fromkeys(e['_geocode_query'] for e in events if e['_geocode_query'] and not e['cancelled']))[:8]
    with ThreadPoolExecutor(max_workers=3) as pool:
        locations = dict(zip(queries, pool.map(lambda query: geocode(client, query), queries)))
    for event in events:
        query = event.pop('_geocode_query')
        if query and not event['cancelled']:
            event['coordinates'] = locations.get(query)
            event['location_status'] = 'approximate' if event['coordinates'] else 'not_located'
    return {'events': events, 'counts': counts, 'source_url': FEED_URL, 'source_name': 'City of Boston Events RSS',
            'fetched_at': now.isoformat(), 'timezone': 'America/New_York', 'refresh_interval_seconds': REFRESH_SECONDS,
            'coverage_note': 'City-published events only. This feed is limited and is not a complete Boston events directory.',
            'freshness_note': 'Periodically refreshed listings, not a live attendance, capacity or cancellation guarantee. Check the organizer before leaving.',
            'category_note': 'Categories are title/department keyword suggestions; they are not provided by the organizer.',
            'geocoding_note': 'Only public event street addresses are sent to the U.S. Census Geocoder. Missing or ambiguous locations stay off the map.'}


def get_events(force_refresh=False):
    global _snapshot, _last_attempt, _last_error
    with _lock:
        age = time.monotonic()-_last_attempt
        threshold = MIN_REFRESH_SECONDS if force_refresh else REFRESH_SECONDS
        fetched = False
        if _last_attempt == 0 or age >= threshold:
            _last_attempt = time.monotonic()
            try:
                with httpx.Client(timeout=httpx.Timeout(8, connect=4), headers=HEADERS, follow_redirects=False) as client:
                    _snapshot = _refresh(client)
                _last_error = False
                fetched = True
            except (httpx.HTTPError, ValueError, ElementTree.ParseError, DefusedXmlException):
                _last_error = True
        if _snapshot is None:
            raise EventsUnavailable('The official Boston event feed is temporarily unavailable. Please try again later.')
        result = deepcopy(_snapshot)
        if datetime.now(timezone.utc)-datetime.fromisoformat(result['fetched_at']) > timedelta(hours=24):
            raise EventsUnavailable('The event feed has not updated for over 24 hours. Please check the official calendar.')
        result['status'] = 'stale' if _last_error else ('updated' if fetched else 'cached')
        result['warning'] = 'Refresh failed. Showing the last successful snapshot; details may have changed.' if _last_error else None
        return result
