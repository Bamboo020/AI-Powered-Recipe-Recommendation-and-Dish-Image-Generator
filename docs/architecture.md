# Architecture v0.2

See [AI architecture and configuration](ai-architecture.md) for implemented optional providers and current limits.

Browser → Vite dev proxy → FastAPI → SQLite recipe repository → rule ranking.

The backend owns filtering and scoring. UI renders source metadata and original steps. Recommendation returns immediately without model calls. Explanation and image requests are separate actions.

## API contracts

- `GET /api/health`: dataset count and provider readiness.
- `POST /api/recommend`: ingredients (1–50), max_cooking_time (1–1440), cuisine, servings (1–20), excluded_ingredients, top_k (1–10). Returns recommendations, total_candidates, ranking_method, dataset_notice.
- `POST /api/explain`: recipe_id. Returns a grounded Ollama explanation if configured, otherwise a labeled template.
- `POST /api/generate-image`: legacy synchronous recipe image request.
- `POST /api/image-jobs`: creates a persistent, single-worker local image job; `GET /api/image-jobs/{job_id}` reports state and `DELETE` cancels a queued job.
- `POST /api/classify-food`: raw image body, capped at 5 MB; optional custom ResNet18 Top-3 inference, or 503.

## Ranking v1

Normalize aliases → exclude recipes containing forbidden ingredients → exclude unknown or excessive times → require at least one available ingredient match → rank → stable recipe ID tie-break → Top-K.

Score = 0.60 × ingredient coverage + 0.20 × time fit + 0.20 × cuisine fit.
Coverage = matched / all listed ingredients (including oil/salt). Time fit = 1 − recipe time / time budget. Cuisine is a soft preference; `any` scores 1 for all. Weights are hypotheses. Optional semantic scoring uses hybrid weights documented in the AI architecture; failures revert to this baseline.

## Remaining work

Real dataset import, five-class CNN training/evaluation, confirmed category mapping and upload UI are implemented. Durable generation jobs, human relevance evaluation and production deployment remain pending. No credentials or weights are bundled.

Version 0.3 adds `dataset` (real/demo/all) and optional confirmed `dish_category` to recommendation requests. Ingredients can be empty only with a supported confirmed category. Semantic reranking is capped at 128 rule-shortlisted candidates. Photo category mapping uses explicit title/source-category rules and excludes obvious dessert/dough mismatches.
