# Delivery plan — current state

Status date: 2026-11-22.

## Implemented in source

- React/FastAPI/SQLite application with validation and provider fallbacks.
- Deterministic recipe recommendation with exclusions, time limits, dataset selection, meal filtering and confirmed five-category search.
- Optional semantic reranking through Sentence Transformers or Ollama embeddings.
- Ollama explanation adapter with structured output checks and template fallback.
- Diffusers generation adapter plus SQLite-backed single-worker image jobs and queued-job cancellation.
- ResNet18 upload/classification contract and user category confirmation.
- Up to three ingredient photos with conservative VLM text parsing and user correction.
- Lifestyle-goal meal planning with explicit non-clinical limitations.
- Boston.gov events, Census geocoding and reviewed free-food resource aggregation.
- Reproducible Food.com and five-class Food-101 preparation scripts.
- Windows download/setup scripts and CNN, retriever, LLM LoRA, VLM LoRA and Diffusion LoRA training entry points.

## Verified now

- `D:\CondaEnvs\myenv` uses Python 3.14.7 and CUDA-enabled PyTorch on an RTX 4080 Laptop GPU.
- Required training libraries import successfully.
- The backend suite passes 46 tests.
- Training Python files compile and their CLI parsers load.
- PowerShell training scripts parse successfully.
- The official Diffusers LoRA example loads from the environment.

## Present only as historical evidence

Committed evaluation reports describe a previous provisioned environment with 5,106 imported Food.com recipes, a trained five-class CNN and local Ollama/Diffusion smoke tests. The current checkout does not contain those raw datasets, the runtime recipe database, generated images or CNN checkpoint. Historical results must not be described as a current Windows reproduction.

## Remaining work

1. Download and checksum Food.com and Food-101 into the documented paths.
2. Run preparation/import and verify the real recipe count in `/api/health`.
3. Re-run the five-class CNN on the Windows CUDA environment and save the checkpoint and fresh metrics.
4. Construct, review and split task-specific retriever, LLM and VLM training datasets.
5. Select licensed base models, train adapters, evaluate held-out quality and document conversion into the runtime format.
6. Add independent human relevance, factuality and image-quality evaluation.
7. Configure a complete demo `.env` without committing local paths or credentials.
8. Validate frontend production build and perform a full browser/API demo on the final machine.
9. Decide retention, timeout and multi-process behavior for image jobs before production use.
10. Complete team ownership, final report, presentation and course-permission review.
