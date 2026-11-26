"""Fine-tune a Sentence Transformer from query/positive/negative JSONL rows."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("HF_HOME", str(Path(sys.prefix) / "cache/huggingface"))
os.environ.setdefault("HF_DATASETS_CACHE", str(Path(sys.prefix) / "cache/datasets"))
os.environ.setdefault("TORCH_HOME", str(Path(sys.prefix) / "cache/torch"))

import torch
from datasets import Dataset
from sentence_transformers import (
    SentenceTransformer,
    SentenceTransformerTrainer,
    SentenceTransformerTrainingArguments,
    losses,
)


ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> Dataset:
    rows = []
    with path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            required = ("query", "positive")
            if any(not isinstance(row.get(key), str) or not row[key].strip() for key in required):
                raise ValueError(f"{path}:{number} requires non-empty query and positive strings")
            item = {"anchor": row["query"], "positive": row["positive"]}
            if isinstance(row.get("negative"), str) and row["negative"].strip():
                item["negative"] = row["negative"]
            rows.append(item)
    if len(rows) < 2:
        raise ValueError("Retriever training needs at least two JSONL rows")
    return Dataset.from_list(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, default=ROOT / "data/training/retriever/train.jsonl")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--output", type=Path, default=ROOT / "training_outputs/retriever")
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    args = parser.parse_args()

    dataset = read_rows(args.train)
    model = SentenceTransformer(args.model, trust_remote_code=False)
    loss = losses.MultipleNegativesRankingLoss(model)
    training_args = SentenceTransformerTrainingArguments(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        save_strategy="epoch",
        logging_steps=10,
        report_to="tensorboard",
        run_name="pantry-studio-retriever",
    )
    trainer = SentenceTransformerTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        loss=loss,
    )
    trainer.train()
    model.save_pretrained(str(args.output / "final"))


if __name__ == "__main__":
    main()
