"""Reads benchmark receipts back in, so calibration and the report can be recomputed without a model."""
from __future__ import annotations

import json
from pathlib import Path

from .engine import ORDERS
from .calibrate import KEYS


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def scoring_of(receipts: dict) -> str:
    return receipts.get("scoring", "letter")  # receipts written before word scoring existed are letter readings


def used_orders(scoring: str) -> int:
    """How many of the saved orders the ball itself uses (all three for letters, the first for words)."""
    return 3 if scoring == "letter" else 1


def item_odds(item: dict, scoring: str = "letter") -> dict[str, float]:
    """The odds the ball would use for one receipt item, recomputed from its raw per-order odds."""
    from .engine import softmax
    n = used_orders(scoring)
    per = [dict(zip(o, softmax(item["raw"][i]))) for i, o in enumerate(ORDERS[:n])]
    return {k: sum(p[k] for p in per) / len(per) for k in KEYS}


def dev_samples(path: str | Path) -> tuple[list[tuple[dict[str, float], str]], str]:
    r = load(path)
    # A file that is valid JSON but is not a receipts file is a plausible slip;
    # name what is missing instead of raising KeyError/TypeError from deep inside.
    if not isinstance(r, dict) or not isinstance(r.get("items"), list) or "model" not in r:
        raise ValueError(f'{path}: not a receipts file (needs a "model" and an "items" list)')
    samples = []
    for i in r["items"]:
        if not isinstance(i, dict) or i.get("split") != "dev":
            continue
        if not isinstance(i.get("raw"), list) or "label" not in i:
            raise ValueError(f'{path}: a dev item is missing its "raw" odds or "label"')
        samples.append((item_odds(i, scoring_of(r)), i["label"]))
    return samples, r["model"]
