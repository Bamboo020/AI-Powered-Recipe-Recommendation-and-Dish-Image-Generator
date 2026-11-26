from datetime import datetime
from app.food_resources import free_food_evidence,next_service,REGISTRY,get_food_resources,load_registry
from app.events import BOSTON
from app import food_resources as foods


def test_free_admission_does_not_imply_food():
    for text in ['Free admission to the farmers market. Food for sale.','Free cooking workshop. Bring your own lunch.','Free food donations accepted for our charity drive.','No free lunch is provided.','Free event with refreshments for sale.','Free food drive. Please bring donations.']:
        assert free_food_evidence(text) is None
    assert free_food_evidence('Join us for a free hot meal.')['full_meal']
    assert not free_food_evidence('Complimentary snacks will be provided.')['full_meal']


def test_next_service_and_fridge_have_different_meanings():
    now=datetime(2026,11,18,19,0,tzinfo=BOSTON)
    start,end=next_service(REGISTRY[0],now)
    assert start==datetime(2026,11,25,15,0,tzinfo=BOSTON)
    assert end>start
    assert REGISTRY[1]['full_meal'] is None


def test_source_failure_is_explicit_and_stock_is_never_claimed(monkeypatch):
    monkeypatch.setattr(foods,'_cache',None)
    monkeypatch.setattr(foods,'_source_check',lambda *a:False)
    monkeypatch.setattr(foods,'geocode',lambda *a:None)
    monkeypatch.setattr(foods,'get_events',lambda **kw:{'events':[],'status':'updated'})
    result=get_food_resources()
    assert result['status']=='partial'
    assert all(e['source_status']=='needs_recheck' and e['stock_status']=='unknown' for e in result['events'])
    assert all(e['calories_kcal'] is None for e in result['events'])


def test_registry_is_data_driven_and_rejects_unknown_sources(tmp_path):
    import json
    assert len(REGISTRY)==4 and all('reviewed_on' in item for item in REGISTRY)
    path=tmp_path/'registry.json'
    path.write_text(json.dumps({'sources':[], 'resources':[{'id':'bad'}]}),encoding='utf-8')
    import pytest
    with pytest.raises(ValueError):
        load_registry(path)
