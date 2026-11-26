"""LoRA fine-tuning for conversational image-and-text ingredient datasets."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

os.environ.setdefault("HF_HOME", str(Path(sys.prefix) / "cache/huggingface"))
os.environ.setdefault("HF_DATASETS_CACHE", str(Path(sys.prefix) / "cache/datasets"))
os.environ.setdefault("TORCH_HOME", str(Path(sys.prefix) / "cache/torch"))

import torch
from datasets import Image, Sequence, load_dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, default=ROOT / "data/training/vlm/train.jsonl")
    parser.add_argument("--model", required=True, help="A Transformers-compatible vision-language model")
    parser.add_argument("--output", type=Path, default=ROOT / "training_outputs/vlm-lora")
    parser.add_argument("--epochs", type=float, default=1)
    parser.add_argument("--max-length", type=int, default=1024)
    args = parser.parse_args()

    if not args.train.is_file():
        raise FileNotFoundError(f"Training JSONL not found: {args.train}")
    dataset = load_dataset("json", data_files=str(args.train), split="train")
    required = {"images", "messages"}
    if not required.issubset(dataset.column_names):
        raise ValueError('Each row needs "images" and conversational "messages" fields')
    dataset = dataset.cast_column("images", Sequence(Image()))

    config = SFTConfig(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=1e-4,
        max_length=args.max_length,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        remove_unused_columns=False,
        logging_steps=5,
        save_strategy="epoch",
        report_to="tensorboard",
    )
    trainer = SFTTrainer(
        model=args.model,
        args=config,
        train_dataset=dataset,
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules="all-linear",
        ),
    )
    trainer.train()
    trainer.save_model(str(args.output / "final-adapter"))


if __name__ == "__main__":
    main()
