import base64
import json
from io import BytesIO
import httpx
import pytest
from pydantic import ValidationError
from app.ai import ingredients as vision
from fastapi.testclient import TestClient
from app.main import app


def photo():
    Image=pytest.importorskip('PIL.Image')
    out=BytesIO();Image.new('RGB',(20,20),'red').save(out,format='JPEG')
    return base64.b64encode(out.getvalue()).decode()


def test_batch_count_and_invalid_image_rejected_before_inference():
    with pytest.raises(ValidationError):vision.PhotoBatch(images=['x']*4)
    with pytest.raises(ValueError):vision.validate_photo('not-base64')
    with TestClient(app) as client:
        assert client.post('/api/identify-ingredients',json={'images':[]}).status_code==422
        assert client.post('/api/identify-ingredients',json={'images':['bad']}).status_code==422


def test_each_photo_has_attribution_and_confirmation(monkeypatch):
    monkeypatch.setenv('OLLAMA_VISION_MODEL','test-vision')
    calls=[]
    def post(url,**kwargs):
        calls.append(kwargs['json'])
        content='The photo shows tomatoes.'
        return httpx.Response(200,json={'message':{'content':content}},request=httpx.Request('POST',url))
    monkeypatch.setattr(vision.httpx,'post',post)
    result=vision.identify_ingredients([photo(),photo()])
    assert [p['photo_index'] for p in result['photos']]==[1,2]
    assert result['requires_confirmation']
    assert len(calls)==2 and all(len(c['messages'][0]['images'])==1 for c in calls)


def test_non_food_and_invalid_provider_output_do_not_invent_ingredients(monkeypatch):
    monkeypatch.setenv('OLLAMA_VISION_MODEL','test-vision')
    def post(url,**kwargs):
        return httpx.Response(200,json={'message':{'content':'This is non-food, not an egg.'}},request=httpx.Request('POST',url))
    monkeypatch.setattr(vision.httpx,'post',post)
    assert vision.identify_ingredients([photo()])['photos'][0]['ingredients']==[]
    monkeypatch.setattr(vision.httpx,'post',lambda url,**kwargs:httpx.Response(200,json={'message':{'content':None}},request=httpx.Request('POST',url)))
    result=vision.identify_ingredients([photo()])
    assert result['status']=='partial_or_unavailable' and result['photos'][0]['ingredients']==[]
