"""Verify the Windows training interpreter without downloading models or data."""
from __future__ import annotations

import importlib
import json
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "torch",
    "torchvision",
    "transformers",
    "sentence_transformers",
    "datasets",
    "accelerate",
    "peft",
    "trl",
    "diffusers",
    "sklearn",
    "tensorboard",
)


def main() -> int:
    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "project": str(ROOT),
        "packages": {},
    }
    missing = []
    for name in PACKAGES:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "installed")
            report["packages"][name] = str(version)
        except Exception as exc:  # Import-time binary errors must be visible.
            report["packages"][name] = f"ERROR: {type(exc).__name__}: {exc}"
            missing.append(name)

    try:
        import torch

        report["cuda_available"] = torch.cuda.is_available()
        report["torch_cuda"] = torch.version.cuda
        report["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        if torch.cuda.is_available():
            report["gpu_memory_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
            )
    except Exception:
        report["cuda_available"] = False

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing:
        print("Missing or broken packages: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
