# Delivery plan — current state

## Implemented and locally verified

- React/FastAPI/SQLite user flows, validation and provider fallbacks.
- 5,106 source-backed Food.com records with reproducible preparation/import; six distinct fixtures.
- Frozen pretrained ResNet18 feature extraction + trained five-class head; official test evaluation and confusion matrix.
- Photo upload, Top-3 predictions, explicit category confirmation/correction and real recipe lookup.
- Actual Ollama embedding reranking, Qwen structured explanation and MPS Stable Diffusion generation.
- Baseline retrieval comparison, provider smoke study and five-category HTTP integration check.

## Remaining limitations / follow-up research

- Human relevance labels and tuning/evaluation on independently held-out user queries. Current semantic blend did not beat keyword baseline on synthetic reconstruction queries.
- Human validation of category-to-recipe mapping; broader data coverage and cuisine/ingredient normalization.
- Unknown-food rejection and calibrated probabilities; expansion beyond five supported classes requires separate training/evaluation.
- Independent LLM factuality and Diffusion image-quality evaluation; outputs can still add unsupported content.
- Durable image job queue/cancellation, production hosting and dependency vulnerability remediation.
- Team ownership, original course rubric and explicit TA confirmation of topic counting and AI-use permission; final team report/demo/submission archive.

See course-requirements.zh.md for the distinction between working technical modules and confirmed classroom compliance.
