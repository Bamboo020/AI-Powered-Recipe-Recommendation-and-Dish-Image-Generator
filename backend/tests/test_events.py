from datetime import datetime, timezone
import time
import httpx
import pytest
from defusedxml.common import DefusedXmlException
from app import events
from app.events import BOSTON, parse_feed, geocode
from fastapi.testclient import TestClient
from app.main import app


def feed(*items):
    return ('<rss><channel>'+''.join(items)+'</channel></rss>').encode()


def item(title='Art workshop', url='https://www.boston.gov/calendar/example', address='23 Drydock Ave',start='Wed, 11/18/2026 - 5:00pm',end='Wed, 11/18/2026 - 7:00pm'):
    return f'''<item><title>{title}</title><link>{url}</link><description><![CDATA[
    <div class="date-recur-date"><time datetime="2026-11-18T17:00:00Z">{start}</time><time>{end}</time></div>
    <p class="address"><span class="address-line1">{address}</span><span class="locality">Boston</span><span class="administrative-area">MA</span><span class="postal-code">02210</span></p>]]></description></item>'''


@pytest.fixture(autouse=True)
def isolate_state(monkeypatch):
    monkeypatch.setattr(events,'_coordinates',{})
    monkeypatch.setattr(events,'_snapshot',None)
    monkeypatch.setattr(events,'_last_attempt',0.0)
    monkeypatch.setattr(events,'_last_error',False)


def test_feed_deduplicates_occurrences_and_uses_visible_boston_clock():
    data,counts=parse_feed(feed(item(),item(),item(start='Thu, 11/19/2026 - 5:00pm',end='Thu, 11/19/2026 - 7:00pm')))
    assert len(data)==2 and counts['duplicates_removed']==1
    assert data[0]['start_at']=='2026-11-18T17:00:00-05:00'
    assert data[0]['category']=='culture'
    assert data[0]['coordinates'] is None
    assert data[0]['_geocode_query']=='23 Drydock Ave, Boston, MA, 02210'


def test_virtual_cancelled_unsafe_and_invalid_time_handling():
    data,counts=parse_feed(feed(item(address='VIRTUAL VIA ZOOM'),item(title='Cancelled: Art',url='https://www.boston.gov/calendar/cancelled'),item(url='http://127.0.0.1/private'),item(start='missing')))
    assert len(data)==2 and counts['skipped_invalid_items']==2
    assert data[0]['virtual'] and data[0]['_geocode_query'] is None
    assert data[1]['cancelled']
    # DST's repeated local clock has no unique offset; do not guess.
    assert parse_feed(feed(item(start='Sun, 11/01/2026 - 1:30am')))[0]==[]


def test_entity_expansion_is_rejected():
    with pytest.raises(DefusedXmlException):
        parse_feed(b'<!DOCTYPE rss [<!ENTITY a "boom">]><rss><channel><title>&a;</title></channel></rss>')


def test_geocoder_coordinates_are_real_validated_and_cached():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'result':{'addressMatches':[{'coordinates':{'x':-71.03,'y':42.34},'matchedAddress':'23 DRY DOCK AVE, BOSTON, MA'}]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first=geocode(client,'23 Drydock Ave, Boston, MA')
        assert first['accuracy'].startswith('Approximate')
        assert geocode(client,'23 Drydock Ave, Boston, MA')==first
    assert len(calls)==1 and calls[0].url.host=='geocoding.geo.census.gov'


@pytest.mark.parametrize('matches', [[],[{'coordinates':{'x':0,'y':0}}],[{},{}]])
def test_geocoder_does_not_substitute_a_city_center(matches):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'result':{'addressMatches':matches}}))) as client:
        assert geocode(client,'missing street') is None


def test_failed_refresh_keeps_timestamp_and_marks_stale(monkeypatch):
    stamp=datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(events,'_snapshot',{'events':[],'fetched_at':stamp})
    def fail(client):
        raise httpx.ConnectError('upstream unavailable')
    monkeypatch.setattr(events,'_refresh',fail)
    data=events.get_events()
    assert data['status']=='stale' and data['fetched_at']==stamp
    assert data['warning']


def test_refresh_cooldown_and_no_key_endpoint(monkeypatch):
    calls=[]
    def refresh(client):
        calls.append(True)
        return {'events':[],'fetched_at':datetime.now(timezone.utc).isoformat()}
    monkeypatch.setattr(events,'_refresh',refresh)
    with TestClient(app) as client:
        first=client.get('/api/events/boston')
        assert first.status_code==200 and first.headers['cache-control']=='no-store'
        second=client.get('/api/events/boston?refresh=true').json()
        assert second['status']=='cached'
    assert len(calls)==1


def test_unavailable_without_snapshot_returns_503(monkeypatch):
    def fail(client):
        raise httpx.ReadTimeout('upstream unavailable')
    monkeypatch.setattr(events,'_refresh',fail)
    with TestClient(app) as client:
        response=client.get('/api/events/boston')
        assert response.status_code==503
        assert 'temporarily unavailable' in response.json()['detail']
