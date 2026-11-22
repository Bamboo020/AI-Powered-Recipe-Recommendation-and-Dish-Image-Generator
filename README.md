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

The original development machine has a configured, ignored root `.env`, local weights, data and a backend environment. On any machine, run Ollama first if you configured an Ollama-backed feature:

```sh
ollama serve
```

### Windows PowerShell

From the repository root, start the backend:

```powershell
.\scripts\start-backend.ps1
```

Use `-Reload` during backend development. The script deliberately uses `backend\.venv\Scripts\python.exe` and fails with setup instructions when the Windows virtual environment is missing.

In a second PowerShell window, start the frontend:

```powershell
Set-Location frontend
npm ci  # First run, or after package-lock.json changes
npm run dev
```

If PowerShell blocks local scripts, either use a process-only policy for that terminal or invoke the script without changing the machine policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

### macOS or Linux

From the repository root:

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

### Windows PowerShell setup

The following creates a Windows-native backend environment and installs the web/API dependencies. It is sufficient to start the application with the labeled demo records; real Food.com data and optional AI providers still require the data/model provisioning described below.

```powershell
py -3 --version
py -3 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.lock.txt
Copy-Item .env.example .env

Set-Location frontend
npm ci
Set-Location ..
```

Edit the ignored root `.env` if you want Ollama, semantic embeddings, Diffusion, CNN classification or ingredient-photo recognition. Leave optional provider values empty to run the deterministic recipe flow without those providers.

### macOS or Linux setup

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

Windows PowerShell equivalent:

```powershell
& .\backend\.venv\Scripts\python.exe -m pytest .\backend\tests -q
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

The current npm audit reports four high-severity findings in the Vite development-tool chain (picomatch/fdir/tinyglobby). The attempted automatic fix did not resolve them. Review and update these dependencies before deployment. Development services bind to loopback only. Image generation now uses a persistent SQLite status record and a bounded single-worker queue; queued work can be cancelled, while an already-running local inference cannot be interrupted safely. Production hosting, access control, job deadlines, retention cleanup and multi-process coordination are not implemented.

### Lifestyle meal planner

The English interface now supports nine combinable goals: balanced eating, weight maintenance, weight management, strength, endurance, plant variety, saving time, spending less, and reducing pantry waste. `GET /api/goals` provides the catalog; `POST /api/plan` accepts offset-aware free-window and meal timestamps, hemisphere, pantry/exclusions and cooking preference.

Plans use source total cooking time and transparent ingredient heuristics (60% selected-goal fit, 40% ingredient coverage). Obvious desserts/drinks are excluded by title/category rules. Budget uses missing ingredient count, not real prices. Calendar seasons provide general prompts, not local harvest/weather claims. This is a single-meal plan; it does not import a calendar, prescribe a calorie deficit or validate an entire day's nutritional adequacy.

Choosing **Prefer a ready-to-eat meal** now switches the API to `ready_to_eat` mode: cooking recipes are intentionally omitted and the interface directs the user to the source-backed prepared-meal and food-resource list below. It does not invent restaurants or treat grocery pickup as a guaranteed prepared meal.

Run `backend/.venv/bin/python scripts/backfill_nutrition.py` after the existing data preparation/import to refresh original Calories, ProteinContent, CarbohydrateContent, FatContent and FiberContent for the 5,106 local records. Preparation scripts also preserve these fields for future imports. **Nutrition serving basis remains unverified**, so the interface labels source-reported calories and does not rescale them or use them as personal targets.

The nearby-business prototype has been replaced by the Boston events map described below; restaurant search and delivery recommendations are not provided. General adult activity context links to [CDC guidance](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html); no exercise calorie burn or medical plan is calculated.


### Boston activities map — no API key

`GET /api/events/boston` connects to the [official City of Boston RSS](https://www.boston.gov/rss/events), linked from the [city events calendar](https://www.boston.gov/events). The backend retains the general city-event feed; the current English map interface uses the free-food resource endpoint described below, with date/category/search filters and linked provider cards. No map or events API key is needed.

- The visible page checks for updates every 5 minutes. The server shares a 5-minute memory snapshot; manual refresh can fetch again after a 60-second cooldown. `fetched_at`, `updated/cached/stale`, source coverage and failure messages are visible. This is periodically refreshed data, not push notifications or guaranteed immediate cancellation/capacity information.
- RSS occurrences are deduplicated by official URL plus event start. Visible event time is parsed in `America/New_York` because the current RSS's `datetime` values can incorrectly label a local clock with `Z`. Ambiguous/nonexistent daylight-saving times are skipped; missing end times stay unknown.
- Only numbered public venue street addresses are sent to the [U.S. Census Geocoder](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html). Unambiguous matches inside greater Boston become **approximate street-range** pins. Online, ambiguous and missing addresses remain unplaced. Up to 8 unique addresses per refresh are checked with at most 3 concurrent calls; successful coordinates cache for a day, failures for 5 minutes.
- No personal location, health goal or pantry contents are sent to the feed, geocoder or map provider. The browser requests map tiles directly from OpenStreetMap, which receives ordinary network/referrer metadata. Attribution remains visible. There is no background map prefetch or offline tile download; larger deployments should provision an appropriate tile service.
- The RSS is a limited city-published subset, mostly civic/community listings; the filter does not search all Boston events. Categories are transparent title/department keyword suggestions. Prices, tickets, attendance and travel times are not inferred.
- Feed failure retains a clearly marked last successful memory snapshot for up to 24 hours; without one the API returns 503. New deployment dependencies are in `backend/requirements.txt` and `frontend/package-lock.json`.

General adult movement context remains linked to CDC guidance; event attendance is not converted into a calorie burn estimate or a prescribed workout.

Live integration check (with the API running): `backend/.venv/bin/python scripts/smoke_boston_events.py`. The recorded real result is in `evaluation/results/boston_events_smoke.json`; it is an evaluation snapshot, not the application data source.

### Free food options, not merely free admission

The activity interface now focuses on **free food** through `GET /api/food-resources/boston`. It separates prepared meals, groceries to cook, community fridges and one-off events explicitly mentioning free food. The validated data registry in `data_metadata/boston_food_resources.json` currently covers four services at two addresses: Allston Brighton Food Pantry's Wednesday hot meal/groceries and community fridge, and Friday Night Supper's dinner service. New reviewed records can be added without editing Python code. Each record keeps its provider link, eligibility, published schedule, review date, source-check status and approximate Census map location.

Regular programs are manually reviewed summaries, with five-minute checks that the source still contains the reviewed details. They are **not** a complete Boston resource directory or a real-time inventory/opening-hours API. Changed or unreachable sources display `needs_recheck`. Prices are not inferred from free admission, donation drives or generic food mentions. The city RSS contributes only explicit free-food evidence; no matching event is an honest empty result. Fridge stock, exact menus, calories, dietary suitability, holiday changes and immediate meal availability remain unknown. Source pages: [Allston Brighton services](https://abfoodpantry.com/services/) and [Friday Night Supper guest information](https://www.fridaynightsupper.org/be-our-guest); its address is documented on the [provider contact page](https://www.fridaynightsupper.org/contact).

### Multiple ingredient photos → confirmation → recipe suggestions

The new custom drop/paste/choose interface accepts **1–3 JPG/PNG/WebP photos**, each under 5 MB and 16 megapixels. `POST /api/identify-ingredients` accepts base64 image strings in `images` (bounded 21 MB JSON request). It strips metadata, creates bounded 1024-pixel inference copies and sends each photo separately to local Ollama. It does not persist ordinary user uploads or send them to the event, geocoding or map providers.

```sh
ollama pull llava:7b
```

Set `OLLAMA_VISION_MODEL=llava:7b` in the ignored root `.env` and restart the backend. LLaVA is an additional **pretrained vision-language model**, not the trained five-class CNN and not a newly trained ingredient detector. Its short visual description is conservatively mapped to a limited English ingredient vocabulary. Every suggestion is marked uncertain, starts unchecked and keeps its photo index. Unknown rice state must be corrected before use. Users select/correct ingredients and explicitly confirm before replacing their pantry and requesting source-backed recipes. Recognized prepared dishes display a warning that visible components are not a complete pantry list. Failures leave manual entry available.

The existing ResNet18 dish-photo interface remains separate, with its five supported classes and original evaluation. Neither interface guarantees arbitrary photo accuracy, portions, freshness, food safety or hidden allergen detection. No calories are estimated from photos. Photo-confirmed searches set `meal_only=true`, which excludes obvious desserts/drinks/standalone sauce categories and records with fewer than two listed ingredients. This is a discovery heuristic, not proof the source ingredient list is complete.

Real integration check: `backend/.venv/bin/python scripts/smoke_food_and_photos.py` with the app running and the two attributed local development photos prepared as documented in `data_metadata/ingredient_photo_sources.json`. Results in `evaluation/results/food_and_photos_smoke.json` preserve observed omissions and manual corrections. These development samples are **not** a held-out ingredient-recognition accuracy benchmark. The downloaded model and image binaries remain excluded from Git.
