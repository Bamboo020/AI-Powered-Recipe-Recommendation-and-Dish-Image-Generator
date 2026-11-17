import os
from pathlib import Path
import tempfile
os.environ["RECIPE_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.sqlite3")
from fastapi.testclient import TestClient
from app.main import app


def test_recommendation_contract():
    with TestClient(app) as client:
        response = client.post("/api/recommend", json={"ingredients": ["鸡蛋", "番茄", "熟米饭"], "max_cooking_time": 30, "cuisine": "中式家常"})
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
        data = client.post("/api/recommend", json={"ingredients": ["tomatoes", "eggs"], "excluded_ingredients": ["鸡蛋"], "top_k": 10}).json()
        assert data["recommendations"]
        assert all("egg" not in [x["name"] for x in r["ingredient_items"]] for r in data["recommendations"])


def test_raw_rice_does_not_match_cooked_rice():
    with TestClient(app) as client:
        data = client.post("/api/recommend", json={"ingredients": ["生米"]}).json()
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
