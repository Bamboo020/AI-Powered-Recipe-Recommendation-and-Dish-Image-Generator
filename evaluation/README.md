# Evaluation

See [measured report](REPORT.zh.md) and `results/` for actual metrics, confusion matrix, retrieval baselines and real provider/integration checks.

The five-class CNN uses a frozen pretrained backbone and a trained classifier head. Independent official test membership is preserved. Retrieval results are synthetic known-positive reconstruction metrics, not a human-labeled relevance study. LLM/Diffusion checks measure technical behavior and document observed errors; independent quality ratings remain pending. Do not generalize these limited results to all foods or all users.
