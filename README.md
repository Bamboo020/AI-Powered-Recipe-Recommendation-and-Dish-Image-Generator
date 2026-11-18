# Pantry Studio — AI Recipe Recommendation & Dish Image Generator

A runnable CSYE 7380 research prototype: enter ingredients or upload a supported food photo, confirm its category, retrieve source-backed recipes, ask for a grounded explanation, and generate a labeled concept image.

## Implemented

- React/Vite English UI, FastAPI validation/orchestration, SQLite repository.
- 5,106 imported real Food.com recipes plus six separately labeled illustrative fixtures. Default UI mode searches real data.
- Time/exclusion filters, ingredient normalization, optional real Ollama/SentenceTransformer embedding reranking, and explainable scores. Encoder work is limited to a 128-candidate rule shortlist.
- Qwen2.5 7B via Ollama, structured short English explanations with source ID checks and template fallback.
- Local Stable Diffusion 1.5 on Apple MPS, original recipe preserved and generated PNG clearly labeled.
- Five-class ResNet18 CNN: ImageNet backbone frozen, classification head trained on real Food-101. Upload → Top-3 → user confirmation/correction → recipe lookup is connected in the UI.
- Reproducible data scripts, model training, held-out evaluation, baseline comparison, provider smoke tests, and CI.

**Scope:** CNN supports only dumplings, fried rice, omelette, pizza, ramen. Other foods are still forced into one of these classes; confidence is not calibrated and this is not an open-set detector. Category-to-recipe mapping uses title/category heuristics, not paired dataset IDs. Source ingredient units and cuisine labels can be incomplete. Exclusions are not an allergy safety guarantee. Quantities keep original servings.

## Measured results

Five-class official held-out test (1,250 images): **Top-1 91.60%, Macro-F1 0.9165**. This is transfer learning of a head, not CNN training from scratch or 101-class accuracy. See [evaluation report](evaluation/REPORT.zh.md) for splits, limitations, baseline results and provider checks. The synthetic retrieval benchmark did **not** demonstrate improvement from the current semantic blend.

## Local start

The current machine has a configured, ignored root `.env`, local weights, data and a backend environment. Run Ollama if it is not already serving:

```sh
ollama serve
```

Then in the repository root:

```sh
sh scripts/start-backend.sh
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. API docs: http://127.0.0.1:8000/docs.

## Fresh setup / reproduce

Use Python 3.11+ (actual local training: Python 3.13, Apple M4/16GB) and Node 20.19+ or 22.12+.

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
# Optional local inference/training dependencies; use requirements-local-ai.lock.txt
# for the tested Apple silicon environment, or requirements-ai.txt for a new environment.
cd ..
sh scripts/download_data.sh
backend/.venv/bin/python scripts/prepare_foodcom.py
backend/.venv/bin/python scripts/import_foodcom.py
backend/.venv/bin/python scripts/extend_photo_recipes.py
backend/.venv/bin/python scripts/import_foodcom.py --input data/processed/foodcom_photo_extension.jsonl
backend/.venv/bin/python scripts/prepare_food101.py
backend/.venv/bin/python scripts/train_cnn.py
```

Copy `.env.example` to `.env`; configure your own Ollama models, Diffusion model directory/device and absolute CNN checkpoint/labels paths. No credentials, raw datasets, images, or binary model weights are committed. `model_assets/food101_5class/labels.json` records the required label order; training regenerates the local checkpoint. The archives total about 5.75GB; the local prepared class subset and recipe CSVs use additional space.

## Tests and evaluation

```sh
cd backend
.venv/bin/python -m pytest tests -q
```

```sh
cd frontend
npm run build
```

Run evaluation scripts from repository root after provisioning data/models:

```sh
backend/.venv/bin/python scripts/evaluate_retrieval.py
backend/.venv/bin/python scripts/smoke_photo_flow.py
backend/.venv/bin/python scripts/evaluate_providers.py
MPLCONFIGDIR=/tmp/recipe-mpl backend/.venv/bin/python scripts/plot_evaluation.py
```

Provider evaluation includes prior development images from local `output/local-ai-smoke.json`; these are not packaged as a public benchmark. See script docstrings and the evaluation report for the exact scope.

## Documentation

- [整体架构](docs/system-architecture.zh.md)
- [AI 模型配置](docs/ai-architecture.md)
- [本机配置](docs/local-setup.zh.md)
- [真实数据、文件与来源](data_metadata/README.md)
- [评估结果](evaluation/REPORT.zh.md)
- [课程要求核对](docs/course-requirements.zh.md)

## Known dependency issue

The current npm audit reports four high-severity findings in the Vite development-tool chain (picomatch/fdir/tinyglobby). The attempted automatic fix did not resolve them. Review and update these dependencies before deployment. Development services bind to loopback only; production hosting, access control, durable image jobs and cancellation are not implemented.

### Lifestyle meal planner

The English interface now supports nine combinable goals: balanced eating, weight maintenance, weight management, strength, endurance, plant variety, saving time, spending less, and reducing pantry waste. `GET /api/goals` provides the catalog; `POST /api/plan` accepts offset-aware free-window and meal timestamps, hemisphere, pantry/exclusions, cooking preference and cooking preference.

Plans use source total cooking time and transparent ingredient heuristics (60% selected-goal fit, 40% ingredient coverage). Obvious desserts/drinks are excluded by title/category rules. Budget uses missing ingredient count, not real prices. Calendar seasons provide general prompts, not local harvest/weather claims. This is a single-meal plan; it does not import a calendar, prescribe a calorie deficit or validate an entire day's nutritional adequacy.

Run `backend/.venv/bin/python scripts/backfill_nutrition.py` after the existing data preparation/import to refresh original Calories, ProteinContent, CarbohydrateContent, FatContent and FiberContent for the 5,106 local records. Preparation scripts also preserve these fields for future imports. **Nutrition serving basis remains unverified**, so the interface labels source-reported calories and does not rescale them or use them as personal targets.

The nearby-business prototype has been replaced by the Boston events map described below; restaurant search and delivery recommendations are not provided. General adult activity context links to [CDC guidance](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html); no exercise calorie burn or medical plan is calculated.


### Boston activities map — no API key

`GET /api/events/boston` connects to the [official City of Boston RSS](https://www.boston.gov/rss/events), linked from the [city events calendar](https://www.boston.gov/events). The English interface displays actual listings on an interactive Leaflet/OpenStreetMap map, with date/category/search filters, online/cancelled toggles, linked cards and organizer links. No map or events API key is needed.

- The visible page checks for updates every 5 minutes. The server shares a 5-minute memory snapshot; manual refresh can fetch again after a 60-second cooldown. `fetched_at`, `updated/cached/stale`, source coverage and failure messages are visible. This is periodically refreshed data, not push notifications or guaranteed immediate cancellation/capacity information.
- RSS occurrences are deduplicated by official URL plus event start. Visible event time is parsed in `America/New_York` because the current RSS's `datetime` values can incorrectly label a local clock with `Z`. Ambiguous/nonexistent daylight-saving times are skipped; missing end times stay unknown.
- Only numbered public venue street addresses are sent to the [U.S. Census Geocoder](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html). Unambiguous matches inside greater Boston become **approximate street-range** pins. Online, ambiguous and missing addresses remain unplaced. Up to 8 unique addresses per refresh are checked with at most 3 concurrent calls; successful coordinates cache for a day, failures for 5 minutes.
- No personal location, health goal or pantry contents are sent to the feed, geocoder or map provider. The browser requests map tiles directly from OpenStreetMap, which receives ordinary network/referrer metadata. Attribution remains visible. There is no background map prefetch or offline tile download; larger deployments should provision an appropriate tile service.
- The RSS is a limited city-published subset, mostly civic/community listings; the filter does not search all Boston events. Categories are transparent title/department keyword suggestions. Prices, tickets, attendance and travel times are not inferred.
- Feed failure retains a clearly marked last successful memory snapshot for up to 24 hours; without one the API returns 503. New deployment dependencies are in `backend/requirements.txt` and `frontend/package-lock.json`.

General adult movement context remains linked to CDC guidance; event attendance is not converted into a calorie burn estimate or a prescribed workout.

Live integration check (with the API running): `backend/.venv/bin/python scripts/smoke_boston_events.py`. The recorded real result is in `evaluation/results/boston_events_smoke.json`; it is an evaluation snapshot, not the application data source.
