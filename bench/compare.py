"""Compare two saved runs (usually two models) on the same test questions.

    python bench/compare.py bench/receipts/gemma3-4b.json bench/receipts/gemma3-12b.json
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eightball.calibrate import KEYS, fit  # noqa: E402
from eightball.receipts import dev_items, item_odds, load, scoring_of  # noqa: E402

TARGET = 0.9


def read(path):
    r = load(path)
    dev = dev_items(r, path)   # validates the receipts shape before anything reads it
    scoring = scoring_of(r)
    by_id = {i["id"]: i for i in r["items"]}
    cal = fit(dev, r["model"], TARGET)
    label = r["model"] + (" (word)" if scoring == "word" else "")
    return label, by_id, cal, scoring


def pct(x):
    return f"{100 * x:.1f}%"


def boot(diffs, n=2000, seed=1):
    rnd = random.Random(seed)
    m = len(diffs)
    if m == 0:
        return 0.0, 0.0
    means = sorted(sum(diffs[rnd.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def main(path_a, path_b):
    from eightball.engine import choose, Odds

    name_a, items_a, cal_a, sc_a = read(path_a)
    name_b, items_b, cal_b, sc_b = read(path_b)
    shared = sorted(set(items_a) & set(items_b))
    test_ids = [i for i in shared if items_a[i]["split"] == "test" and items_b[i]["split"] == "test"]
    if not test_ids:
        sys.exit("no shared test items between these two runs")

    def answer(items, cal, scoring, i):
        it = items[i]
        return choose(it["question"], Odds(item_odds(it, scoring), None, []), cal, text_mode="text" in it)

    right_a, right_b, said_a, said_b, wrong_a, wrong_b = [], [], [], [], [], []
    for i in test_ids:
        label = items_a[i]["label"]
        a, b = answer(items_a, cal_a, sc_a, i), answer(items_b, cal_b, sc_b, i)
        right_a.append(a["category"] == label)
        right_b.append(b["category"] == label)
        if a["category"] != "maybe":
            said_a.append(1); wrong_a.append(a["category"] != label)
        if b["category"] != "maybe":
            said_b.append(1); wrong_b.append(b["category"] != label)

    print(f"# {name_a} vs {name_b}\n")
    print(f"{len(test_ids)} shared test questions.\n")
    print("| | " + name_a + " | " + name_b + " |")
    print("|---|---|---|")
    print(f"| Right group | {pct(sum(right_a) / len(right_a))} | {pct(sum(right_b) / len(right_b))} |")
    print(f"| Said a plain yes or no | {pct(len(said_a) / len(test_ids))} | {pct(len(said_b) / len(test_ids))} |")
    print(f"| Wrong when it said one | {pct(sum(wrong_a) / len(wrong_a) if wrong_a else 0)} | {pct(sum(wrong_b) / len(wrong_b) if wrong_b else 0)} |")

    diffs = [int(rb) - int(ra) for ra, rb in zip(right_a, right_b)]
    lo, hi = boot(diffs)
    tag = "outside noise" if lo > 0 or hi < 0 else "inside noise"
    print(f"\nRight group, {name_b} minus {name_a}: {100 * sum(diffs) / len(diffs):+.1f} points [{100 * lo:+.1f}, {100 * hi:+.1f}] ({tag})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <receipts-a.json> <receipts-b.json>")
    try:
        main(sys.argv[1], sys.argv[2])
    except (OSError, ValueError) as e:
        sys.exit(f"compare: {e}")
