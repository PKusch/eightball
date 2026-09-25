"""The ball: read the model's odds in three shuffled orders, cool them down, and pick one of the 20 phrases."""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field

from .answers import ANSWERS
from .calibrate import KEYS, Calibration

# Every option takes every position once, so a model's habit of favouring "A" cancels out.
ORDERS = [["yes", "no", "maybe"], ["no", "maybe", "yes"], ["maybe", "yes", "no"]]

# A phrase is said only when the chance of being wrong is below its cut-off. Strongest phrase first.
# "It is certain" therefore needs a calibrated chance of being wrong under 1 in 100.
LADDER = {
    "yes": [0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.17, 0.23, 0.30],
    "no": [0.02, 0.06, 0.12, 0.22],
}

FUTURE = re.compile(r"\b(will|won't|going to|tomorrow|tonight|next|soon|someday|eventually)\b|\b20[3-9]\d\b", re.I)
YES_NO_START = re.compile(
    r"^(is|are|was|were|am|do|does|did|can|could|will|would|should|shall|may|might|must|has|have|had|isn't|aren't|"
    r"wasn't|weren't|don't|doesn't|didn't|can't|won't|wouldn't|shouldn't)\b", re.I)


def softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    es = [math.exp(x - m) for x in xs]
    z = sum(es)
    return [e / z for e in es]


def is_yes_no_question(q: str) -> bool:
    s = q.strip()
    return len(s.split()) >= 3 and bool(YES_NO_START.match(s))


@dataclass
class Odds:
    probs: dict[str, float]      # the three shuffled readings averaged
    stability: float             # share of the orderings whose own top pick matched the averaged top pick
    per_order: list[dict[str, float]] = field(default_factory=list)


def read_odds(backend, question: str) -> Odds:
    per_order = []
    for order in ORDERS:
        raw = backend.scores(question, order)
        per_order.append(dict(zip(order, softmax(raw))))
    probs = {k: sum(p[k] for p in per_order) / len(per_order) for k in KEYS}
    top = max(KEYS, key=probs.get)
    stab = sum(1 for p in per_order if max(KEYS, key=p.get) == top) / len(per_order)
    return Odds(probs, stab, per_order)


def strength_of(category: str, confidence: float) -> int:
    """1 = the strongest phrase in the group. Wrong-chance above each cut-off steps one phrase down."""
    err = 1.0 - confidence
    return 1 + sum(err > cut for cut in LADDER[category])


def hazy_phrase(question: str, top: str, probs: dict[str, float]) -> str:
    if not is_yes_no_question(question):
        return "Concentrate and ask again"          # not something with a yes or no answer
    if top == "maybe":
        return "Cannot predict now" if FUTURE.search(question) else "Better not tell you now"
    other = "no" if top == "yes" else "yes"
    if probs[top] - probs[other] < 0.15:
        return "Reply hazy, try again"              # torn between yes and no
    return "Ask again later"                        # leaning one way but not sure enough


def choose(question: str, odds: Odds, cal: Calibration) -> dict:
    probs = cal.apply(odds.probs)
    top = max(KEYS, key=probs.get)
    committed = top != "maybe" and probs[top] >= cal.threshold and is_yes_no_question(question)
    if committed:
        category, strength = top, strength_of(top, probs[top])
        answer = ANSWERS[category][strength - 1]
    else:
        category, answer = "maybe", hazy_phrase(question, top, probs)
        strength = ANSWERS["maybe"].index(answer) + 1
    return {
        "category": category, "answer": answer, "strength": strength,
        "confidence": round(probs[category] if committed else probs[top], 4),
        "committed": committed, "leaning": top,
        "probs": {k: round(probs[k], 4) for k in KEYS},
        "stability": round(odds.stability, 3),
    }


class Ball:
    def __init__(self, backend, calibration: Calibration | None = None):
        self.backend = backend
        self.calibration = calibration or Calibration()

    def ask(self, question: str) -> dict:
        question = question.strip()
        if not question:
            raise ValueError("ask a question")
        t0 = time.perf_counter()
        reading = choose(question, read_odds(self.backend, question), self.calibration)
        return {"question": question, **reading, "backend": getattr(self.backend, "name", "unknown"),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000)}
