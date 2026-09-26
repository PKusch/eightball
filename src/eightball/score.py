"""Grade the ball on your own questions: a file with one JSON object per line, {"question": "...", "label": "yes|no|maybe"}."""
from __future__ import annotations

import json
from pathlib import Path

from .engine import Ball

LABELS = ("yes", "no", "maybe")


def load_items(path: str | Path) -> list[dict]:
    items = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            it = json.loads(line)
            q, lab = it["question"], it["label"]
        except (ValueError, KeyError, TypeError):
            raise ValueError(f'{path}:{n}: each line must look like {{"question": "...", "label": "yes"}}') from None
        if lab not in LABELS or not isinstance(q, str) or not q.strip():
            raise ValueError(f"{path}:{n}: label must be yes, no or maybe, and the question must not be empty")
        items.append(it)
    if not items:
        raise ValueError(f"{path}: no questions found")
    return items


def score(ball: Ball, items: list[dict]) -> dict:
    rows = [(it, ball.ask(it["question"])) for it in items]
    n = len(rows)
    right = sum(1 for it, r in rows if r["category"] == it["label"])
    said = [(it, r) for it, r in rows if r["category"] != "maybe"]
    wrong_said = [(it, r) for it, r in said if r["category"] != it["label"]]
    out = {
        "n": n,
        "right": right / n,
        "said_yes_or_no": len(said) / n,
        "wrong_when_sure": len(wrong_said) / len(said) if said else 0.0,
        "by_label": {},
        "misses": [{"question": it["question"], "should_say": it["label"], "said": r["answer"]} for it, r in wrong_said],
    }
    for lab in LABELS:
        sub = [(it, r) for it, r in rows if it["label"] == lab]
        if sub:
            out["by_label"][lab] = {"n": len(sub), "right": sum(1 for it, r in sub if r["category"] == lab) / len(sub)}
    return out


def render(res: dict) -> str:
    pct = lambda x: f"{100 * x:.0f}%"
    lines = [
        f"{res['n']} questions",
        f"  right group (yes / hazy / no):  {pct(res['right'])}",
        f"  said a plain yes or no:         {pct(res['said_yes_or_no'])}",
        f"  of those, wrong:                {pct(res['wrong_when_sure'])}   <- the number to watch",
    ]
    lines += [f"  right on {lab} questions ({v['n']}):  {pct(v['right'])}" for lab, v in res["by_label"].items()]
    if res["misses"]:
        lines += ["", "wrongly sure (first 10):"]
        lines += [f"  {m['question']}  should be {m['should_say']}, ball said: {m['said']}" for m in res["misses"][:10]]
    return "\n".join(lines)
