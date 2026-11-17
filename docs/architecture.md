# Architecture v0.1

Browser → Vite dev proxy → FastAPI → SQLite recipe repository → rule ranking.

The backend owns filtering and scoring. UI renders source metadata and original steps. Recommendation returns immediately without model calls. Explanation and image requests are separate actions.

## API contracts

- `GET /api/health`: dataset count and provider readiness.
- `POST /api/recommend`: ingredients (1–50), max_cooking_time (1–1440), cuisine, servings (1–20), excluded_ingredients, top_k (1–10). Returns recommendations, total_candidates, ranking_method, dataset_notice.
- `POST /api/explain`: recipe_id. Returns a labeled template fallback, not an LLM result.
- `POST /api/generate-image`: recipe_id. Validates recipe existence, then returns 503 until a Diffusion provider is implemented.
- `POST /api/classify-food`: reserved P1 endpoint; currently returns 503, accepts no image upload.

## Ranking v1

Normalize aliases → exclude recipes containing forbidden ingredients → exclude unknown or excessive times → require at least one available ingredient match → rank → stable recipe ID tie-break → Top-K.

Score = 0.60 × ingredient coverage + 0.20 × time fit + 0.20 × cuisine fit.
Coverage = matched / all listed ingredients (including oil/salt). Time fit = 1 − recipe time / time budget. Cuisine is a soft preference; `any` scores 1 for all. Weights are hypotheses. There is no semantic similarity score until a real encoder is integrated and evaluated.

## Next boundaries

Add a separate retriever using sentence-transformers and precomputed embeddings; retain hard filters before ranking. Keep original recipe data distinct from LLM text. Add provider timeouts and explicit error states. Diffusion should expose job status and an explicitly AI-generated image. CNN should return supported classes and Top-3 confidences, followed by user confirmation before recipe lookup.

No API key belongs in the browser. Production deployment, durable image jobs, authentication, rate limits, and hosted inference are not implemented.
