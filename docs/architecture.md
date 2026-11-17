# Architecture v0.2

See [AI architecture and configuration](ai-architecture.md) for implemented optional providers and current limits.

Browser → Vite dev proxy → FastAPI → SQLite recipe repository → rule ranking.

The backend owns filtering and scoring. UI renders source metadata and original steps. Recommendation returns immediately without model calls. Explanation and image requests are separate actions.

## API contracts

- `GET /api/health`: dataset count and provider readiness.
- `POST /api/recommend`: ingredients (1–50), max_cooking_time (1–1440), cuisine, servings (1–20), excluded_ingredients, top_k (1–10). Returns recommendations, total_candidates, ranking_method, dataset_notice.
- `POST /api/explain`: recipe_id. Returns a grounded Ollama explanation if configured, otherwise a labeled template.
- `POST /api/generate-image`: recipe_id. Validates recipe existence, calls optional local Diffusers pipeline; returns image metadata or 503.
- `POST /api/classify-food`: raw image body, capped at 5 MB; optional custom ResNet18 Top-3 inference, or 503.

## Ranking v1

Normalize aliases → exclude recipes containing forbidden ingredients → exclude unknown or excessive times → require at least one available ingredient match → rank → stable recipe ID tie-break → Top-K.

Score = 0.60 × ingredient coverage + 0.20 × time fit + 0.20 × cuisine fit.
Coverage = matched / all listed ingredients (including oil/salt). Time fit = 1 − recipe time / time budget. Cuisine is a soft preference; `any` scores 1 for all. Weights are hypotheses. Optional semantic scoring uses hybrid weights documented in the AI architecture; failures revert to this baseline.

## Remaining work

Real dataset import, confirmed CNN category mapping and upload UI, model provisioning, measured evaluation, durable generation jobs and production deployment remain pending. No credentials or weights are bundled.
