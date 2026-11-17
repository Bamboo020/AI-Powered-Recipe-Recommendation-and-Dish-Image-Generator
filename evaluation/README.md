# Evaluation protocol

No model metrics have been measured yet. API tests verify software behavior only.

- Retrieval: fixed queries with human relevance judgments; Recall@K and MRR; compare rule/keyword baseline to encoder retrieval.
- Ranking: Top-K relevance and hard constraint violation rate.
- CNN: held-out split, Top-1 accuracy, macro F1, per-class confusion matrix.
- LLM: source consistency, unsupported ingredient claims, and failure rate.
- Diffusion: dish consistency, human image quality ratings, latency, and failures.
- System: end-to-end success and error-state behavior.

Record dataset sizes, splits, model versions, hardware, and actual measurements.
