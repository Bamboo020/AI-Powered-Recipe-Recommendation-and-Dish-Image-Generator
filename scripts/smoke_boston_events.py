"""Verify the running API against the real public feed; never substitute fixtures."""
import json
from pathlib import Path
from datetime import datetime
import httpx

ROOT=Path(__file__).resolve().parents[1]
response=httpx.get('http://127.0.0.1:8000/api/events/boston',timeout=35)
response.raise_for_status()
data=response.json()
assert data['status'] in ('updated','cached'), 'A stale snapshot does not prove live connectivity'
assert data['events'], 'No source events returned'
ids=[e['id'] for e in data['events']]
assert len(ids)==len(set(ids))
for event in data['events']:
    assert event['source_url'].startswith('https://www.boston.gov/')
    assert datetime.fromisoformat(event['start_at']).utcoffset() is not None
    if event['virtual']:
        assert event['coordinates'] is None
mapped=[e for e in data['events'] if e['coordinates']]
assert mapped, 'No locations verified; map integration needs investigation'
for event in mapped:
    assert 42.1<=event['coordinates']['latitude']<=42.6
    assert -71.4<=event['coordinates']['longitude']<=-70.8
report={'verification':'Real local API + Boston.gov RSS + U.S. Census Geocoder',
        'status':data['status'],'fetched_at':data['fetched_at'],'source_url':data['source_url'],
        'counts':data['counts'],'mapped_events':len(mapped),'online_events':sum(e['virtual'] for e in data['events']),
        'location_samples':[{'title':e['title'],'source_url':e['source_url'],'coordinates':e['coordinates']} for e in mapped],
        'limitations':['Snapshot counts change as the source updates.','Census coordinates are approximate; no exact entrance, route or travel time is verified.','City-published subset, not all Boston events.']}
path=ROOT/'evaluation/results/boston_events_smoke.json'
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
