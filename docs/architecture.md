# Architecture v0.4 — current source state

Status date: 2026-11-22.

Pantry Studio is a modular local web application:

```text
React/Vite UI -> FastAPI -> SQLite recipes
                         -> deterministic filtering/ranking
                         -> optional local AI providers
                         -> public Boston information sources
```

The recommendation path does not require an AI model. LLM explanations, generated images, image classification and ingredient-photo recognition are optional actions with explicit fallbacks or 503 responses.

## Current checkout state

- The source code, metadata, tests and historical evaluation reports are present.
- `D:\CondaEnvs\myenv` contains the verified Windows training environment.
- The ignored `data/` directories exist but contain no datasets in this checkout.
- No root `.env`, `recipes.sqlite3` or `image_jobs.sqlite3` currently exists.
- `model_assets/food101_5class/labels.json` is present, but the ResNet18 checkpoint is not.
- On first backend startup, SQLite is created and six labeled `demo-` recipes are inserted. Real `foodcom-` recipes appear only after the import pipeline is run.

## Components

| Component | Responsibility | Current source implementation |
| --- | --- | --- |
| React/Vite | Recipe search, photo upload, ingredient-photo confirmation, meal planning and Boston resource UI | Implemented |
| FastAPI | Validation, orchestration, provider fallbacks and static generated-image serving | Implemented |
| SQLite | Recipe payloads and image-job state | Created locally at runtime |
| Rule recommender | Time, exclusions, optional meal/category filters and stable ranking | Implemented |
| Semantic reranker | Optional Sentence Transformer or Ollama embeddings over at most 128 shortlisted candidates | Implemented, not configured in the current checkout |
| Ollama LLM | Source-grounded recipe explanation | Implemented, not configured |
| Diffusers | Local text-to-image generation | Implemented, not configured |
| ResNet18 | Five-category food-image classification | Adapter implemented; checkpoint absent |
| Ollama vision | Up to three ingredient photos followed by user confirmation | Implemented, not configured |
| Boston services | Boston.gov events, Census geocoding and reviewed food-resource registry | Implemented; live refresh requires network access |

## API contracts

- `GET /api/health`: recipe counts, dataset mode and provider configuration state.
- `POST /api/recommend`: ingredient/category recommendation with dataset and meal filters.
- `GET /api/goals`, `POST /api/plan`: heuristic lifestyle-goal meal planning.
- `GET /api/events/boston`: Boston.gov event feed with cached/geocoded results.
- `GET /api/food-resources/boston`: reviewed recurring programs plus qualifying city events.
- `POST /api/explain`: Ollama explanation or deterministic template fallback.
- `POST /api/generate-image`: legacy synchronous image generation.
- `POST /api/image-jobs`, `GET/DELETE /api/image-jobs/{job_id}`: single-worker local image jobs.
- `POST /api/classify-food`: raw JPEG/PNG/WebP classification, maximum 5 MB.
- `POST /api/identify-ingredients`: one to three base64 images, each maximum 5 MB and 16 MP.

## Recommendation behavior

The deterministic baseline normalizes limited aliases, applies dataset/category/meal filters, rejects excluded ingredients and excessive or unknown cooking times, and requires an ingredient match unless a confirmed category is supplied.

Baseline score:

```text
0.60 ingredient coverage + 0.20 time fit + 0.20 cuisine fit
```

When semantic embeddings are available:

```text
0.40 ingredient coverage + 0.25 time fit
+ 0.20 cuisine fit + 0.15 semantic similarity
```

These weights are engineering hypotheses, not learned or clinically validated. Exclusion matching is not an allergy guarantee. Meal-plan goal scores are also transparent keyword heuristics, not medical or nutrition prescriptions.

See `ai-architecture.md` for model boundaries and `windows-training.zh.md` for the prepared training environment.
