"""Turns raw model odds into odds you can check, and decides how sure the ball must be before it commits.

Two numbers are learned from labelled examples: a temperature (how much to cool down an over-confident
model) and a threshold (the lowest confidence at which the ball still says a plain yes or no).
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

KEYS = ("yes", "no", "maybe")


@dataclass
class Calibration:
    temperature: float = 1.0   # above 1 cools an over-confident model
    threshold: float = 0.0     # below this confidence a yes or no becomes a hazy answer
    model: str = ""
    n_dev: int = 0
    target: float = 0.0        # the accuracy the threshold was chosen to reach on the dev items

    def apply(self, probs: dict[str, float]) -> dict[str, float]:
        w = {k: max(probs[k], 1e-12) ** (1.0 / self.temperature) for k in KEYS}
        z = sum(w.values())
        return {k: w[k] / z for k in KEYS}

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "Calibration":
        d = json.loads(Path(path).read_text())
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


def _nll(samples: list[tuple[dict[str, float], str]], t: float) -> float:
    c = Calibration(temperature=t)
    return -sum(math.log(max(c.apply(p)[y], 1e-12)) for p, y in samples) / len(samples)


def fit_temperature(samples: list[tuple[dict[str, float], str]]) -> float:
    """Best single temperature by grid search on the average log-loss (dependency-free)."""
    grid = [round(0.3 + 0.05 * i, 2) for i in range(0, 95)]
    return min(grid, key=lambda t: _nll(samples, t))


def fit_threshold(samples: list[tuple[dict[str, float], str]], temperature: float, target: float,
                  min_commit: float = 0.10) -> float:
    """The lowest confidence at which, among yes/no picks at or above it, the share that were right
    reaches `target`. The ball must still commit on at least `min_commit` of items (a ball that never
    says yes or no is useless), so a target that cannot be met falls back to the most accurate cut that still commits that often."""
    cal = Calibration(temperature=temperature)
    scored = []
    for p, y in samples:
        q = cal.apply(p)
        top = max(KEYS, key=q.get)
        if top != "maybe":
            scored.append((q[top], top == y))
    scored.sort(reverse=True)
    n = len(samples)
    best, right, best_acc, fallback = None, 0, -1.0, 1.0
    for i, (conf, ok) in enumerate(scored, 1):
        right += ok
        if i < len(scored) and scored[i][0] == conf:
            continue  # only judge between groups of equal confidence
        if i / n >= min_commit:
            if right / i >= target:
                best = conf
            if right / i > best_acc:
                best_acc, fallback = right / i, conf
    return best if best is not None else fallback


def fit(samples: list[tuple[dict[str, float], str]], model: str = "", target: float = 0.9) -> Calibration:
    if not samples:
        raise ValueError("need labelled examples to calibrate")
    t = fit_temperature(samples)
    return Calibration(t, fit_threshold(samples, t, target), model, len(samples), target)
