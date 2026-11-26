from fastapi.testclient import TestClient
from app.main import app


def test_recommendation_contract():
    with TestClient(app) as client:
        response = client.post("/api/recommend", json={"ingredients": ["eggs", "tomatoes", "cooked rice"], "max_cooking_time": 30, "cuisine": "Chinese"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) == 3
        assert data["ranking_method"] == "ingredient_rules_v1"
        for item in data["recommendations"]:
            assert item["total_minutes"] <= 30
            assert item["source"] and item["steps"]
            assert item["llm_explanation"] is None
        scores = [r["final_score"] for r in data["recommendations"]]
        assert scores == sorted(scores, reverse=True)


def test_exclusions_are_hard_constraints():
    with TestClient(app) as client:
        data = client.post("/api/recommend", json={"ingredients": ["tomatoes", "eggs"], "excluded_ingredients": ["egg"], "top_k": 10}).json()
        assert data["recommendations"]
        assert all("egg" not in [x["name"] for x in r["ingredient_items"]] for r in data["recommendations"])


def test_raw_rice_does_not_match_cooked_rice():
    with TestClient(app) as client:
        data = client.post("/api/recommend", json={"ingredients": ["raw rice"]}).json()
        assert data["recommendations"] == []


def test_time_and_empty_results():
    with TestClient(app) as client:
        assert client.post("/api/recommend", json={"ingredients": ["egg"], "max_cooking_time": 1}).json()["recommendations"] == []
        for body in [{"ingredients": []}, {"ingredients": [" "]}, {"ingredients": ["egg"], "max_cooking_time": 0}]:
            assert client.post("/api/recommend", json=body).status_code == 422


def test_unavailable_services_are_honest():
    with TestClient(app) as client:
        selected = {"recipe_id": "demo-001"}
        assert client.get("/api/health").json()["recipe_count"] == 6
        explanation = client.post("/api/explain", json=selected).json()
        assert explanation["is_llm_generated"] is False
        assert client.post("/api/generate-image", json=selected).status_code == 503
        assert client.post("/api/classify-food").status_code == 503
        assert client.post("/api/explain", json={"recipe_id": "missing"}).status_code == 404


def test_photo_meal_scope_excludes_desserts_and_single_ingredient_records(monkeypatch):
    from app import main
    def record(key,title,ingredients,category='Lunch'):
        return {'recipe_id':key,'title':title,'source_category':category,'source':'test','total_minutes':10,'servings':1,'ingredient_items':[{'name':i} for i in ingredients],'steps':['Review source.'],'cuisine_tags':[]}
    monkeypatch.setattr(main,'read_recipes',lambda:[record('a','Lemon Cookies',['egg']),record('b','Scrambled eggs with tomato',['egg','tomato']),record('c','Quick egg',['egg']),record('d','Tomato Sauce',['tomato','salt'],'Sauces')])
    with TestClient(app) as client:
        data=client.post('/api/recommend',json={'ingredients':['egg','tomato'],'meal_only':True}).json()
        assert [r['recipe_id'] for r in data['recommendations']]==['b']
