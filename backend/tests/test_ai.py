import httpx
from fastapi.testclient import TestClient
from app import main
from app.ai import services


def test_hybrid_keeps_hard_filters(monkeypatch):
    seen = []
    def scores(query, recipes):
        seen.extend(recipes)
        return [.8] * len(recipes)
    monkeypatch.setattr(main, 'semantic_scores', scores)
    with TestClient(main.app) as client:
        data = client.post('/api/recommend', json={'ingredients':['tomato','egg'], 'excluded_ingredients':['egg'], 'max_cooking_time':20}).json()
    assert data['ranking_method'] == 'hybrid_semantic_v1'
    assert seen
    assert all(r['total_minutes'] <= 20 and 'egg' not in [i['name'] for i in r['ingredient_items']] for r in seen)
    assert all('semantic_similarity' in r['match_factors'] for r in data['recommendations'])


def test_llm_success_and_timeout(monkeypatch):
    monkeypatch.setenv('OLLAMA_MODEL','test-model')
    def success(url, **kwargs):
        assert kwargs['json']['stream'] is False
        assert 'demo-001' in kwargs['json']['messages'][1]['content']
        return httpx.Response(200,json={'message':{'content':'基于原食谱的说明'}},request=httpx.Request('POST',url))
    monkeypatch.setattr(services.httpx,'post',success)
    with TestClient(main.app) as client:
        data = client.post('/api/explain',json={'recipe_id':'demo-001'}).json()
        assert data['is_llm_generated'] is True and data['source_recipe_id']=='demo-001'
        def timeout(*args,**kwargs):
            raise httpx.ReadTimeout('timeout')
        monkeypatch.setattr(services.httpx,'post',timeout)
        data = client.post('/api/explain',json={'recipe_id':'demo-001'}).json()
        assert data['is_llm_generated'] is False and data['status']=='fallback'


def test_semantic_load_failure_falls_back(monkeypatch):
    monkeypatch.setenv('EMBEDDING_MODEL','missing')
    def broken():
        raise RuntimeError('missing dependency or weights')
    monkeypatch.setattr(services,'encoder',broken)
    assert services.semantic_scores('egg',[{'title':'test','ingredient_items':[], 'cuisine_tags':[]}]) is None


def test_image_generation_saves_asset(monkeypatch,tmp_path):
    monkeypatch.setenv('DIFFUSION_MODEL','test')
    class Image:
        def save(self,path):
            path.write_bytes(b'test-image')
    class Output:
        images=[Image()]
    monkeypatch.setattr(services,'diffusion',lambda:lambda **kwargs:Output())
    recipe={'title':'test','ingredient_items':[{'name':'egg'}]}
    result=services.generate_recipe_image(recipe,tmp_path)
    assert result['is_ai_generated'] is True
    assert (tmp_path/result['url'].split('/')[-1]).read_bytes()==b'test-image'


def test_image_upload_limit():
    with TestClient(main.app) as client:
        response=client.post('/api/classify-food',content=b'x'*(5*1024*1024+1))
        assert response.status_code==413


def test_ollama_embeddings_are_used_and_cached(monkeypatch):
    monkeypatch.setenv('OLLAMA_EMBED_MODEL','test-embed')
    services.ollama_document_embeddings.cache_clear()
    calls=[]
    def embed(url, **kwargs):
        calls.append(kwargs['json']['input'])
        return httpx.Response(200,json={'embeddings':[[3.,4.] for _ in kwargs['json']['input']]},request=httpx.Request('POST',url))
    monkeypatch.setattr(services.httpx,'post',embed)
    recipes=[{'title':'test','ingredient_items':[], 'cuisine_tags':[]}]
    assert services.semantic_scores('egg',recipes)==[1.]
    assert services.semantic_scores('tomato',recipes)==[1.]
    assert len(calls)==3
    assert calls[0][0].startswith('search_document: ')
    assert calls[1][0].startswith('search_query: ')
    services.ollama_document_embeddings.cache_clear()
