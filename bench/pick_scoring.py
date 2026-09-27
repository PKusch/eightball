"""Decide letter or word scoring for a model, using only the fitting (dev) questions, never the test ones.

    python bench/pick_scoring.py bench/receipts/gemma3-4b.json bench/receipts/gemma3-4b-word.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eightball.calibrate import KEYS, fit  # noqa: E402
from eightball.receipts import item_odds, scoring_of  # noqa: E402


def dev_accuracy(path):
    r = json.loads(Path(path).read_text())
    scoring = scoring_of(r)
    dev = [(item_odds(i, scoring), i["label"]) for i in r["items"] if i["split"] == "dev"]
    cal = fit(dev, r["model"], 0.9)
    right = sum(1 for p, y in dev if max(KEYS, key=cal.apply(p).get) == y) / len(dev)
    return scoring, right


def main(paths):
    scored = [dev_accuracy(p) for p in paths]
    for (scoring, acc), p in zip(scored, paths):
        print(f"{scoring:>6}: {acc:.1%} right on the fitting questions ({p})")
    best = max(scored, key=lambda x: x[1])
    print(f"\npick: {best[0]}")


if __name__ == "__main__":
    main(sys.argv[1:])
