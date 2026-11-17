# Delivery plan

## Completed foundation
- Project directories and startup instructions.
- React/FastAPI connection and recipe detail flow.
- SQLite fixture repository, normalization, hard filters, and rule baseline.
- Validation and provider-unavailable behavior.

## Next: real data and retrieval
- Obtain the Food.com dataset through its source and record license/access terms.
- Implement validated import with source IDs/URLs, parsing, duplicate handling, missing-time flags, and ingredient normalization.
- Keep project fixtures separate from real records; human-review Chinese examples.
- Encode recipe text with all-MiniLM-L6-v2; compare retrieval with the rule baseline.

## Then: AI integrations
- Choose an LLM provider and configure a server-side key; ground explanations in a selected source record.
- Verify available GPU or hosted Diffusion provider, license, latency, and budget before choosing a model.
- Integrate image generation with separate request/job status and AI labeling.
- Establish Food-101 supported classes, dataset splits, ResNet18 baseline, and category-to-recipe mapping.

## Freeze and evaluation
- Report measured retrieval/classification metrics and model/provider failures.
- Test no matches, excluded ingredients, provider timeouts, original steps surviving failures, and mobile use.
- Prepare reproducible environments, data/model setup, and independently verified demo inputs.

The 14-day guide is a planning reference. Its architecture suggestions are not evidence that models, training, data provenance, or evaluations are complete.
