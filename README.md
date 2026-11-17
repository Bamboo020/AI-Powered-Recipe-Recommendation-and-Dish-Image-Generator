# Pantry Studio — AI Recipe Recommendation & Dish Image Generator

A runnable CSYE 7380 research prototype: enter ingredients or upload a supported food photo, confirm its category, retrieve source-backed recipes, ask for a grounded explanation, and generate a labeled concept image.

## Implemented

- React/Vite Chinese UI, FastAPI validation/orchestration, SQLite repository.
- 5,106 imported real Food.com recipes plus six separately labeled illustrative fixtures. Default UI mode searches real data.
- Time/exclusion filters, ingredient normalization, optional real Ollama/SentenceTransformer embedding reranking, and explainable scores. Encoder work is limited to a 128-candidate rule shortlist.
- Qwen2.5 7B via Ollama, structured short explanations with source ID checks and template fallback.
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
