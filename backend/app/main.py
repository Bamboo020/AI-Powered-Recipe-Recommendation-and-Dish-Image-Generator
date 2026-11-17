from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
from fastapi import FastAPI, HTTPException
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
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS recipes (recipe_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        for recipe in json.loads((ROOT / "data_metadata/demo_recipes.json").read_text()):
            connection.execute("INSERT OR IGNORE INTO recipes VALUES (?, ?)", (recipe["recipe_id"], json.dumps(recipe, ensure_ascii=False)))
    yield


app = FastAPI(title="Pantry Studio Recipe API", version="0.1.0", lifespan=lifespan)
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
    return {"status": "ok", "recipe_count": len(read_recipes()), "dataset": "illustrative_demo", "services": {"semantic_encoder": "not_configured", "llm": "not_configured", "diffusion": "not_configured", "cnn": "not_configured"}}


@app.post("/api/recommend")
def recommend(request: RecipeRequest):
    available = set(request.ingredients)
    excluded = set(request.excluded_ingredients)
    results = []
    for recipe in read_recipes():
        needed = {normalize(item["name"]) for item in recipe["ingredient_items"]}
        if needed & excluded or recipe["total_minutes"] is None or recipe["total_minutes"] > request.max_cooking_time:
            continue
        matched = needed & available
        if not matched:
            continue
        coverage = len(matched) / len(needed)
        time_fit = 1 - recipe["total_minutes"] / request.max_cooking_time
        cuisine_fit = float(normalize(request.cuisine) in ["any", *recipe["cuisine_tags"]])
        factors = {"ingredient_match": round(coverage, 4), "time_fit": round(time_fit, 4), "cuisine_fit": cuisine_fit}
        score = .6 * coverage + .2 * time_fit + .2 * cuisine_fit
        results.append({**recipe, "available_ingredients": sorted(matched), "missing_ingredients": sorted(needed - available), "match_factors": factors, "final_score": round(score, 4), "requested_servings": request.servings, "quantity_note": "Quantities and steps retain the original recipe yield; adjust portions manually.", "llm_explanation": None, "generated_image": {"status": "not_configured", "url": None, "is_ai_generated": False}})
    results.sort(key=lambda item: (-item["final_score"], item["recipe_id"]))
    return {"recommendations": results[:request.top_k], "total_candidates": len(results), "ranking_method": "ingredient_rules_v1", "dataset_notice": "Illustrative project fixtures, not imported Food.com records. Not validated dietary or allergy advice."}


@app.post("/api/explain")
def explain(request: SelectedRecipe):
    recipe = find_recipe(request.recipe_id)
    return {"recipe_id": recipe["recipe_id"], "provider": "template", "status": "fallback", "is_llm_generated": False, "text": f"{recipe['title']} takes {recipe['total_minutes']} minutes and serves {recipe['servings']}. Review all listed ingredients and follow the original steps below. LLM service is not configured.", "source": recipe["source"]}


@app.post("/api/generate-image")
def generate_image(request: SelectedRecipe):
    find_recipe(request.recipe_id)
    raise HTTPException(status_code=503, detail="Diffusion service is not configured. No image was generated.")


@app.post("/api/classify-food")
def classify_food():
    raise HTTPException(status_code=503, detail="CNN classifier is not configured. Photo classification is unavailable.")
