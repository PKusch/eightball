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

def orders_for(backend) -> list[list[str]]:
    """Which option orders to read. Letter scoring rotates all three. Word scoring reads only the natural
    order (yes, no, maybe): on the fitting questions, listing MAYBE second made the model almost never say it (6%),
    so averaging in the other orders only hurt."""
    return ORDERS if getattr(backend, "scoring", "letter") == "letter" else ORDERS[:1]


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


# Health, safety, money and other people's private feelings: a toy should never sound sure about these.
SENSITIVE = re.compile(
    r"\b(doctor|medicine|medication|pills?|dose|overdose|pregnan\w*|cancer|diagnos\w*|symptoms?|therapy|therapist|"
    r"depress\w*|suicid\w*|self[- ]harm|kill myself|hurt myself|lawyer|sue|lawsuit|invest\w*|mortgage|loan|"
    r"divorce|break up with|propose|does (he|she|they) (love|like) me|love me)\b", re.I)

NOTE_SENSITIVE = "This is about health, safety, money or someone's feelings. Please ask a person."


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
    stability: float | None      # share of the orderings whose own top pick matched the averaged top pick (None: one ordering)
    per_order: list[dict[str, float]] = field(default_factory=list)


def read_odds(backend, question: str, text: str | None = None) -> Odds:
    per_order = []
    orders = orders_for(backend)
    for order in orders:
        raw = backend.scores(question, order) if text is None else backend.scores(question, order, text)
        per_order.append(dict(zip(order, softmax(raw))))
    probs = {k: sum(p[k] for p in per_order) / len(per_order) for k in KEYS}
    top = max(KEYS, key=probs.get)
    stab = sum(1 for p in per_order if max(KEYS, key=p.get) == top) / len(per_order) if len(orders) > 1 else None
    return Odds(probs, stab, per_order)


def strength_of(category: str, confidence: float) -> int:
    """1 = the strongest phrase in the group. Wrong-chance above each cut-off steps one phrase down."""
    err = 1.0 - confidence
    return 1 + sum(err > cut for cut in LADDER[category])


def hazy(question: str, top: str, probs: dict[str, float]) -> tuple[str, str]:
    """The hazy phrase and, in plain words, why the ball went hazy."""
    if SENSITIVE.search(question):
        return "Better not tell you now", "sensitive"
    if not is_yes_no_question(question):
        return "Concentrate and ask again", "not_a_question"
    if top == "maybe":
        return ("Cannot predict now", "future") if FUTURE.search(question) else ("Better not tell you now", "unknowable")
    other = "no" if top == "yes" else "yes"
    if probs[top] - probs[other] < 0.15:
        return "Reply hazy, try again", "torn"
    return "Ask again later", "leaning"


def hazy_in_text(question: str, top: str, probs: dict[str, float]) -> tuple[str, str]:
    """Hazy phrase when the question is about a supplied text: 'not stated' is the main reason."""
    if not is_yes_no_question(question):
        return "Concentrate and ask again", "not_a_question"
    if top == "maybe":
        return "Concentrate and ask again", "not_stated"
    other = "no" if top == "yes" else "yes"
    if probs[top] - probs[other] < 0.15:
        return "Reply hazy, try again", "torn"
    return "Ask again later", "leaning"


def hazy_phrase(question: str, top: str, probs: dict[str, float]) -> str:
    return hazy(question, top, probs)[0]


def explain(reason: str, leaning: str) -> str:
    return {
        "sensitive": NOTE_SENSITIVE,
        "not_a_question": "That is not a yes/no question, so there is nothing to answer.",
        "future": "It depends on the future, and nobody can know that.",
        "unknowable": "The model does not think this can be known, or it is a private matter.",
        "not_stated": "The text does not say.",
        "torn": "The model was torn between yes and no.",
        "leaning": f"The model leaned {leaning} but was not sure enough to say so.",
    }[reason]


def choose(question: str, odds: Odds, cal: Calibration, text_mode: bool = False) -> dict:
    probs = cal.apply(odds.probs)
    top = max(KEYS, key=probs.get)
    # about a supplied text, the question is not advice, so the health/money guard does not apply
    sensitive = (not text_mode) and bool(SENSITIVE.search(question))
    committed = top != "maybe" and probs[top] >= cal.threshold and is_yes_no_question(question) and not sensitive
    reason = None
    if committed:
        category, strength = top, strength_of(top, probs[top])
        answer = ANSWERS[category][strength - 1]
    else:
        category = "maybe"
        answer, reason = hazy_in_text(question, top, probs) if text_mode else hazy(question, top, probs)
        strength = ANSWERS["maybe"].index(answer) + 1
    return {
        "category": category, "answer": answer, "strength": strength,
        "confidence": round(probs[category] if committed else probs[top], 4),
        "committed": committed, "leaning": top,
        "reason": reason, "explanation": explain(reason, top) if reason else None,
        "per_order": [{"order": list(o), "pick": max(KEYS, key=p.get)} for o, p in zip(ORDERS, odds.per_order)],
        "probs": {k: round(probs[k], 4) for k in KEYS},
        "stability": None if odds.stability is None else round(odds.stability, 3),
    }


class Ball:
    def __init__(self, backend, calibration: Calibration | None = None, text_calibration: Calibration | None = None):
        self.backend = backend
        self.calibration = calibration or Calibration()
        self.text_calibration = text_calibration  # questions about a supplied text behave differently, so they get their own

    def ask(self, question: str, text: str | None = None) -> dict:
        question = question.strip()
        if not question:
            raise ValueError("ask a question")
        if text is not None and not text.strip():
            text = None
        t0 = time.perf_counter()
        cal = (self.text_calibration or self.calibration) if text is not None else self.calibration
        reading = choose(question, read_odds(self.backend, question, text), cal, text_mode=text is not None)
        return {"question": question, **({"text_mode": True} if text is not None else {}), **reading, "backend": getattr(self.backend, "name", "unknown"),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000)}
