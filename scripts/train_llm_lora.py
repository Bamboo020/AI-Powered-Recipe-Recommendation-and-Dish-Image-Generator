"""Supervised LoRA fine-tuning for chat-style recipe explanation data."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

os.environ.setdefault("HF_HOME", str(Path(sys.prefix) / "cache/huggingface"))
os.environ.setdefault("HF_DATASETS_CACHE", str(Path(sys.prefix) / "cache/datasets"))
os.environ.setdefault("TORCH_HOME", str(Path(sys.prefix) / "cache/torch"))

import torch
from datasets import load_dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, default=ROOT / "data/training/llm/train.jsonl")
    parser.add_argument("--model", required=True, help="Hugging Face model ID or local model directory")
    parser.add_argument("--output", type=Path, default=ROOT / "training_outputs/llm-lora")
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=2048)
    args = parser.parse_args()

    if not args.train.is_file():
        raise FileNotFoundError(f"Training JSONL not found: {args.train}")
    dataset = load_dataset("json", data_files=str(args.train), split="train")
    if "messages" not in dataset.column_names:
        raise ValueError('Each JSONL row must contain a chat-formatted "messages" array')

    config = SFTConfig(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=2e-4,
        warmup_ratio=0.05,
        max_length=args.max_length,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        logging_steps=5,
        save_strategy="epoch",
        report_to="tensorboard",
    )
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    trainer = SFTTrainer(
        model=args.model,
        args=config,
        train_dataset=dataset,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(str(args.output / "final-adapter"))


if __name__ == "__main__":
    main()
