"""Helpers for the Google Colab notebook (notebooks/aminos_colab_gpu.ipynb): read the GPU, pick a local model that fits.

Free Colab runtimes offer a shared NVIDIA GPU (typically a T4 with about 15 GB) with no guarantee on availability or
session length. The model runs inside the Colab VM through Ollama; nothing is exposed to the outside.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, asdict
from typing import Callable

# (minimum free VRAM in MiB, Ollama tag, comment). Sizes are the 4-bit builds plus room for the context window.
MODELS = [
    (14000, "qwen3:14b", "best quality that fits a 15 GB T4/P100"),
    (8000, "qwen3:8b", "fits 8-12 GB cards"),
    (5000, "qwen3:4b", "small card: expect weaker legal Arabic"),
    (0, "qwen3:1.7b", "very small: drafts only, check everything"),
]

Runner = Callable[[list[str]], "tuple[int, str]"]


def _run(argv: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        return p.returncode, p.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""


@dataclass
class Plan:
    gpu: str
    vram_total_mb: int
    vram_free_mb: int
    model: str
    note: str
    warnings: list[str]


def detect_gpu(run: Runner = _run) -> tuple[str, int, int] | None:
    """(name, total MiB, free MiB) of the first GPU, or None."""
    rc, out = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"])
    if rc != 0 or not out.strip():
        return None
    name, total, free = (v.strip() for v in out.strip().splitlines()[0].split(","))
    return name, int(float(total)), int(float(free))


def choose_model(free_mb: int) -> tuple[str, str]:
    for need, tag, note in MODELS:
        if free_mb >= need:
            return tag, note
    return MODELS[-1][1], MODELS[-1][2]


def plan(run: Runner = _run) -> Plan:
    gpu = detect_gpu(run)
    warnings = ["Colab is Google's cloud: the document leaves your machine. Do not use it for confidential files.",
                "Free GPU availability and session length are not guaranteed; save results as you go."]
    if gpu is None:
        warnings.insert(0, "No GPU: choose Runtime > Change runtime type > T4 GPU. On CPU the model is far too slow.")
        tag, note = MODELS[-1][1], "no GPU detected"
        return Plan("none", 0, 0, tag, note, warnings)
    name, total, free = gpu
    tag, note = choose_model(free)
    return Plan(name, total, free, tag, note, warnings)


def as_dict(p: Plan) -> dict:
    return asdict(p)
