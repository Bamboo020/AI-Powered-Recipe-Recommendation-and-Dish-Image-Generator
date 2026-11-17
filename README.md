# Pantry Studio — AI Recipe Recommendation & Dish Image Generator

A CSYE 7380 project in progress. Start with ingredients, discover up to three recipes, inspect missing ingredients and original steps, then request an explanation or dish image.

## Implemented in v0.1

- React + Vite responsive Chinese interface with ingredient input, cooking time, cuisine preference, servings, exclusions, result cards, and recipe detail.
- FastAPI + SQLite repository with six explicitly labeled project-authored illustrative recipes.
- Chinese/English ingredient normalization, strict time/exclusion filtering, deterministic explainable ranking, and empty/error states.
- Optional SentenceTransformer reranking, Ollama explanation, Diffusers generation and custom ResNet18 classification, with explicit disabled/error states.
- API validation tests and GitHub Actions checks.

**This is a runnable foundation, not a completed AI system.** No Food.com data or model weights are bundled. Optional AI adapters are implemented; see [AI setup](docs/ai-architecture.md). Demo recipes are unreviewed fixtures. Exclusion matching is exact after aliases and is not an allergy safety guarantee. Servings are captured, but ingredient quantities retain the original recipe yield.

## Quick start

Use Python 3.11+ and Node.js 20.19+ (or 22.12+).

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs.
The frontend proxies `/api` to port 8000. Run both servers for local development. SQLite is initialized on API startup; set `RECIPE_DB_PATH` to override its path. Demo records are inserted if absent, without overwriting existing records.

## Verify

```sh
cd backend
python -m pytest tests -q
```

```sh
cd frontend
npm run build
```

Try `鸡蛋，番茄，熟米饭` / 30 minutes / 中式家常. Excluding 鸡蛋 must remove every recipe listing egg. A 1-minute limit returns no matches. Image generation reports that the service is unavailable.

## Layout

```text
frontend/       React UI and Vite dev proxy
backend/        API, normalization, SQLite, ranking, tests
data_metadata/  Labeled fixture recipes and data provenance notes
model_assets/   Model integration plan (no weights)
evaluation/     Evaluation protocol (no fabricated metrics)
docs/           Architecture and milestone plan
```

See [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [data notes](data_metadata/README.md). No credentials or model weights should be committed. See `.env.example` for opt-in provider settings. Use local environment variables when adding providers.

## Known dependency issue

The current npm audit reports four high-severity findings in the Vite development-tool dependency chain (picomatch/fdir/tinyglobby). `npm audit fix` does not resolve them with the available dependency versions. Development servers bind to loopback only; review and update these dependencies before deployment.
