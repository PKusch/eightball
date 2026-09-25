"""Reads benchmark receipts back in, so calibration and the report can be recomputed without a model."""
from __future__ import annotations

import json
from pathlib import Path

from .engine import ORDERS
from .calibrate import KEYS


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def item_odds(item: dict) -> dict[str, float]:
    """The shuffled average for one receipt item, recomputed from its raw per-order odds."""
    from .engine import softmax
    per = [dict(zip(o, softmax(item["raw"][i]))) for i, o in enumerate(ORDERS)]
    return {k: sum(p[k] for p in per) / len(per) for k in KEYS}


def dev_samples(path: str | Path) -> tuple[list[tuple[dict[str, float], str]], str]:
    r = load(path)
    return [(item_odds(i), i["label"]) for i in r["items"] if i["split"] == "dev"], r["model"]
