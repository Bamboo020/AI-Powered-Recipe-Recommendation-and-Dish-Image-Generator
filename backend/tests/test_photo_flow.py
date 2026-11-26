from fastapi.testclient import TestClient
from app import main


def test_confirmed_category_search_and_dataset_filter(monkeypatch):
    records=[{'recipe_id':'foodcom-1','title':'Chicken Fried Rice','ingredient_items':[{'name':'egg'}],'total_minutes':15,'cuisine_tags':[],'steps':['Cook.'],'source':'test','servings':2}, {'recipe_id':'demo-1','title':'Vegetable Fried Rice','ingredient_items':[{'name':'egg'}],'total_minutes':15,'cuisine_tags':[],'steps':['Cook.'],'source':'fixture','servings':2}]
    monkeypatch.setattr(main,'read_recipes',lambda:records)
    monkeypatch.setattr(main,'semantic_scores',lambda q,r:None)
    with TestClient(main.app) as client:
        data=client.post('/api/recommend',json={'dish_category':'fried_rice','dataset':'real','ingredients':[]}).json()
        assert [r['recipe_id'] for r in data['recommendations']]==['foodcom-1']
        assert data['category_mapping']=='title_keyword_heuristic'
        assert client.post('/api/recommend',json={'dish_category':'unknown'}).status_code==422
        assert client.post('/api/recommend',json={'ingredients':[]}).status_code==422
        assert client.post('/api/recommend',json={'dish_category':'fried_rice','excluded_ingredients':['egg']}).json()['recommendations']==[]


def test_photo_api_returns_confirmation_not_auto_recipe(monkeypatch):
    def classify(content):
        assert content==b'image-bytes'
        return {'predictions':[{'label':'pizza','confidence':.8}],'requires_confirmation':True}
    monkeypatch.setattr(main,'classify_image',classify)
    with TestClient(main.app) as client:
        result=client.post('/api/classify-food',content=b'image-bytes').json()
        assert result['requires_confirmation'] is True
        assert 'recommendations' not in result


def test_invalid_image_rejected_when_classifier_configured(monkeypatch):
    import pytest
    pytest.importorskip('PIL')
    monkeypatch.setenv('CNN_CHECKPOINT','configured')
    monkeypatch.setenv('CNN_LABELS_PATH','configured')
    with TestClient(main.app) as client:
        assert client.post('/api/classify-food',content=b'not-an-image').status_code==422


def test_category_mapping_rejects_keyword_side_dishes():
    from app.dishes import matches_dish
    assert not matches_dish({'title':'Pot Sticker Dipping Sauce'},'dumplings')
    assert not matches_dish({'title':'Citrus Dumplings','source_keywords':['Dessert']},'dumplings')
    assert not matches_dish({'title':'Basic Ramen Broth # 1'},'ramen')
    assert matches_dish({'title':'Asian Ramen Noodle Soup'},'ramen')
    assert matches_dish({'title':'Pork Gyoza'},'dumplings')
