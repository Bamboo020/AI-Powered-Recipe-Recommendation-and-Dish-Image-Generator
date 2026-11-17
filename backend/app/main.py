from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from .ai.services import AIUnavailable, configured_services, semantic_scores, explain_recipe, generate_recipe_image, classify_image
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("RECIPE_DB_PATH", str(ROOT / "recipes.sqlite3")))
ALIASES = {
    "eggs": "egg", "鸡蛋": "egg", "番茄": "tomato", "西红柿": "tomato",
    "tomatoes": "tomato", "熟米饭": "cooked_rice", "米饭": "cooked_rice",
    "cooked rice": "cooked_rice", "rice": "raw_rice", "生米": "raw_rice",
    "大米": "raw_rice", "鸡肉": "chicken", "土豆": "potato", "potatoes": "potato",
    "洋葱": "onion", "大蒜": "garlic", "面条": "noodles", "豆腐": "tofu",
    "酱油": "soy_sauce", "soy sauce": "soy_sauce", "葱": "scallion",
    "橄榄油": "olive_oil", "olive oil": "olive_oil", "油": "oil", "盐": "salt",
    "中式家常": "chinese_home_style", "chinese": "chinese_home_style",
    "意式": "italian", "不限": "any",
}

def normalize(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip().lower())
    return ALIASES.get(value, value.replace(" ", "_"))


def read_recipes():
    with sqlite3.connect(DB_PATH) as connection:
        return [json.loads(row[0]) for row in connection.execute("SELECT payload FROM recipes ORDER BY recipe_id")]


@asynccontextmanager
async def lifespan(app):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS recipes (recipe_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        for recipe in json.loads((ROOT / "data_metadata/demo_recipes.json").read_text()):
            connection.execute("INSERT OR IGNORE INTO recipes VALUES (?, ?)", (recipe["recipe_id"], json.dumps(recipe, ensure_ascii=False)))
    yield


app = FastAPI(title="Pantry Studio Recipe API", version="0.2.0", lifespan=lifespan)
IMAGE_DIR = ROOT / "generated"
app.mount("/generated", StaticFiles(directory=str(IMAGE_DIR), check_dir=False), name="generated")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class RecipeRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1, max_length=50)
    max_cooking_time: int = Field(default=30, ge=1, le=1440)
    cuisine: str = Field(default="any", max_length=80)
    servings: int = Field(default=1, ge=1, le=20)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=3, ge=1, le=10)

    @field_validator("ingredients", "excluded_ingredients")
    @classmethod
    def clean_ingredients(cls, values):
        if any(not v.strip() or len(v) > 80 for v in values):
            raise ValueError("Ingredients must contain 1–80 non-whitespace characters")
        return sorted(set(normalize(v) for v in values))


class SelectedRecipe(BaseModel):
    recipe_id: str = Field(min_length=1, max_length=100)


def find_recipe(recipe_id):
    for recipe in read_recipes():
        if recipe["recipe_id"] == recipe_id:
            return recipe
    raise HTTPException(status_code=404, detail="Recipe not found")


@app.get("/api/health")
def health():
    return {"status": "ok", "recipe_count": len(read_recipes()), "dataset": "illustrative_demo", "services": configured_services()}


@app.post("/api/recommend")
def recommend(request: RecipeRequest):
    available = set(request.ingredients)
    excluded = set(request.excluded_ingredients)
    results = []
    candidates = []
    for recipe in read_recipes():
        needed = {normalize(item["name"]) for item in recipe["ingredient_items"]}
        if needed & excluded or recipe["total_minutes"] is None or recipe["total_minutes"] > request.max_cooking_time:
            continue
        matched = needed & available
        if not matched:
            continue
        candidates.append((recipe, needed, matched))
    similarities = semantic_scores(" ".join(request.ingredients) + " " + normalize(request.cuisine), [r for r, _, _ in candidates])
    for index, (recipe, needed, matched) in enumerate(candidates):
        coverage = len(matched) / len(needed)
        time_fit = 1 - recipe["total_minutes"] / request.max_cooking_time
        cuisine_fit = float(normalize(request.cuisine) in ["any", *recipe["cuisine_tags"]])
        factors = {"ingredient_match": round(coverage, 4), "time_fit": round(time_fit, 4), "cuisine_fit": cuisine_fit}
        score = .6 * coverage + .2 * time_fit + .2 * cuisine_fit
        if similarities is not None:
            factors["semantic_similarity"] = round(similarities[index], 4)
            score = .4 * coverage + .25 * time_fit + .2 * cuisine_fit + .15 * similarities[index]
        results.append({**recipe, "available_ingredients": sorted(matched), "missing_ingredients": sorted(needed - available), "match_factors": factors, "final_score": round(score, 4), "requested_servings": request.servings, "quantity_note": "Quantities and steps retain the original recipe yield; adjust portions manually.", "llm_explanation": None, "generated_image": {"status": "not_configured", "url": None, "is_ai_generated": False}})
    results.sort(key=lambda item: (-item["final_score"], item["recipe_id"]))
    return {"recommendations": results[:request.top_k], "total_candidates": len(results), "ranking_method": "hybrid_semantic_v1" if similarities is not None else "ingredient_rules_v1", "semantic_status": "used" if similarities is not None else "unavailable_or_disabled", "dataset_notice": "Illustrative project fixtures, not imported Food.com records. Not validated dietary or allergy advice."}


@app.post("/api/explain")
def explain(request: SelectedRecipe):
    recipe = find_recipe(request.recipe_id)
    try:
        text = explain_recipe(recipe)
        return {"recipe_id": recipe["recipe_id"], "provider": "ollama", "status": "completed", "is_llm_generated": True, "text": text, "source": recipe["source"], "source_recipe_id": recipe["recipe_id"]}
    except AIUnavailable:
        return {"recipe_id": recipe["recipe_id"], "provider": "template", "status": "fallback", "is_llm_generated": False, "text": f"{recipe['title']} takes {recipe['total_minutes']} minutes and serves {recipe['servings']}. Review the original ingredients and steps. LLM unavailable.", "source": recipe["source"]}


@app.post("/api/generate-image")
def generate_image(request: SelectedRecipe):
    recipe = find_recipe(request.recipe_id)
    try:
        return generate_recipe_image(recipe, IMAGE_DIR)
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/classify-food")
async def classify_food(request: Request):
    # Raw image body avoids multipart buffering. Enforce limit even without Content-Length.
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image must be under 5 MB")
    from starlette.concurrency import run_in_threadpool
    try:
        return await run_in_threadpool(classify_image, bytes(content))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
