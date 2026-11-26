# Model assets

`food101_5class/resnet18.pt` is the local trained checkpoint, ignored by Git. `food101_5class/labels.json` is the ordered five-class label list (committed). Reproduce with `scripts/prepare_food101.py` and `scripts/train_cnn.py` after installing inference dependencies and obtaining data.

The backbone starts from torchvision `ResNet18_Weights.DEFAULT` / ImageNet weights. Only the new linear classification head is trained; backbone weights stay frozen. Input preprocessing follows the same torchvision default evaluation transform used by the API. Seed 42, 60 head-training epochs, model selected by validation macro-F1. No test labels participate in training or checkpoint selection. Measured confusion matrix and checkpoint SHA256 are in `evaluation/results/cnn_metrics.json`.

The local Ollama models and Stable Diffusion cache are external pretrained models, not trained by this project. Their paths belong in ignored `.env`; see AI architecture for configuration. Raw datasets and binary weights are excluded from Git to avoid large files and uncontrolled redistribution.
