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
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal
from .dishes import DISH_PATTERNS, matches_dish
from .planner import GOALS, PlanRequest, plan

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("RECIPE_DB_PATH", str(ROOT / "recipes.sqlite3")))
ALIASES = {
    "eggs": "egg", "鸡蛋": "egg", "番茄": "tomato", "西红柿": "tomato",
    "tomatoes": "tomato", "熟米饭": "cooked_rice", "米饭": "cooked_rice",
    "cooked rice": "cooked_rice", "raw rice": "raw_rice", "uncooked rice": "raw_rice", "rice": "raw_rice", "生米": "raw_rice",
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
            connection.execute("INSERT INTO recipes VALUES (?, ?) ON CONFLICT(recipe_id) DO UPDATE SET payload=excluded.payload", (recipe["recipe_id"], json.dumps(recipe, ensure_ascii=False)))
    yield


app = FastAPI(title="Pantry Studio Recipe API", version="0.3.0", lifespan=lifespan)
IMAGE_DIR = ROOT / "generated"
app.mount("/generated", StaticFiles(directory=str(IMAGE_DIR), check_dir=False), name="generated")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class RecipeRequest(BaseModel):
    ingredients: list[str] = Field(default_factory=list, max_length=50)
    max_cooking_time: int = Field(default=30, ge=1, le=1440)
    cuisine: str = Field(default="any", max_length=80)
    servings: int = Field(default=1, ge=1, le=20)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=3, ge=1, le=10)

    dish_category: Literal['fried_rice', 'omelette', 'pizza', 'ramen', 'dumplings'] | None = None
    dataset: Literal['all', 'real', 'demo'] = 'all'

    @model_validator(mode='after')
    def require_query(self):
        if not self.ingredients and not self.dish_category:
            raise ValueError('Provide ingredients or a confirmed dish category')
        return self

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
    recipes = read_recipes()
    real = sum(r['recipe_id'].startswith('foodcom-') for r in recipes)
    return {"status": "ok", "recipe_count": len(recipes), "real_recipe_count": real, "demo_recipe_count": len(recipes)-real, "dataset": "foodcom_and_labeled_fixtures" if real else "illustrative_demo", "services": configured_services(), "supported_dish_categories": list(DISH_PATTERNS)}


@app.post("/api/recommend")
def recommend(request: RecipeRequest):
    available = set(request.ingredients)
    excluded = set(request.excluded_ingredients)
    results = []
    candidates = []
    for recipe in read_recipes():
        is_real = recipe['recipe_id'].startswith('foodcom-')
        if request.dataset == 'real' and not is_real or request.dataset == 'demo' and is_real:
            continue
        if request.dish_category and not matches_dish(recipe, request.dish_category):
            continue
        needed = {normalize(item["name"]) for item in recipe["ingredient_items"]}
        if needed & excluded or recipe["total_minutes"] is None or recipe["total_minutes"] > request.max_cooking_time:
            continue
        matched = needed & available
        if not matched and not request.dish_category:
            continue
        candidates.append((recipe, needed, matched))
    eligible_count = len(candidates)
    # Bound encoder work on real datasets; shortlist by the existing deterministic baseline.
    candidates.sort(key=lambda entry: (- (.6 * len(entry[2])/len(entry[1]) + .2 * (1-entry[0]['total_minutes']/request.max_cooking_time) + .2 * float(normalize(request.cuisine) in ['any', *entry[0]['cuisine_tags']])), entry[0]['recipe_id']))
    candidates = candidates[:128]
    similarities = semantic_scores(" ".join(request.ingredients) + " " + (request.dish_category or '') + " " + normalize(request.cuisine), [r for r, _, _ in candidates])
    for index, (recipe, needed, matched) in enumerate(candidates):
        coverage = len(matched) / len(needed)
        time_fit = 1 - recipe["total_minutes"] / request.max_cooking_time
        cuisine_fit = float(normalize(request.cuisine) in ["any", *recipe["cuisine_tags"]])
        factors = {"ingredient_match": round(coverage, 4), "time_fit": round(time_fit, 4), "cuisine_fit": cuisine_fit}
        score = .6 * coverage + .2 * time_fit + .2 * cuisine_fit
        if similarities is not None:
            factors["semantic_similarity"] = round(similarities[index], 4)
            score = .4 * coverage + .25 * time_fit + .2 * cuisine_fit + .15 * similarities[index]
        results.append({**recipe, "available_ingredients": sorted(matched), "missing_ingredients": sorted(needed - available), "match_factors": factors, "final_score": round(score, 4), "requested_servings": request.servings, "quantity_note": "Quantities and steps retain the original recipe yield; adjust portions manually.", "llm_explanation": None, "generated_image": {"status": "not_requested" if os.getenv("DIFFUSION_MODEL") else "not_configured", "url": None, "is_ai_generated": False}})
    results.sort(key=lambda item: (-item["final_score"], item["recipe_id"]))
    return {"recommendations": results[:request.top_k], "total_candidates": eligible_count, "reranked_candidates": len(results), "confirmed_dish_category": request.dish_category, "category_mapping": "title_keyword_heuristic" if request.dish_category else None, "ranking_method": "hybrid_semantic_v1" if similarities is not None else "ingredient_rules_v1", "semantic_status": "used" if similarities is not None else "unavailable_or_disabled", "dataset_notice": "Food.com records and/or explicitly labeled fixtures, according to dataset selection. Quantities retain source text; aliases and exclusions are limited, not allergy safety guarantees."}


@app.get('/api/goals')
def goals():
    return [{'id': key, 'label': value[0], 'guidance': value[1]} for key, value in GOALS.items()]


@app.post('/api/plan')
def meal_plan(request: PlanRequest):
    return plan(request, read_recipes(), normalize)


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
