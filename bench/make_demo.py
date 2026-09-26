"""Fill the page's replay block from saved receipts, so the demo shows real answers and nothing invented.

Draws 3 random test questions per kind (fixed seed, no picking of flattering ones), asks the ball what it
would have said using the calibration fitted on the dev items, and writes them into web/index.html.
    python bench/make_demo.py bench/receipts/gemma3-4b.json
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eightball.calibrate import fit  # noqa: E402
from eightball.engine import ORDERS, Odds, choose, softmax  # noqa: E402
from eightball.receipts import item_odds, scoring_of, used_orders  # noqa: E402
from eightball.calibrate import KEYS  # noqa: E402

# kinds whose questions read naturally come first, because the page builds its example chips from the top
NATURAL = ["capital", "animal", "geo", "future", "private", "taste", "chemistry", "physical", "open"]


# Extra questions the benchmark does not contain (health guard, a non-question, a lottery). They are asked of the
# real model once, when this script runs, and saved like the rest.
EXTRAS = [
    "Should I stop taking my medication?",
    "Tell me a joke",
    "Will I win the lottery next week?",
    "Is it going to rain in London tomorrow?",
]


def live_extras(model, cal, scoring):
    from eightball.backend import BackendError, OllamaBackend
    from eightball.engine import Ball
    try:
        ball = Ball(OllamaBackend(model, scoring=scoring), cal)
        return [ball.ask(q) | {"backend": f"{model} (saved run)"} for q in EXTRAS]
    except BackendError as e:
        print(f"skipping extras (no model reachable: {e})")
        return []


def main(path):
    r = json.loads(Path(path).read_text())
    scoring = scoring_of(r)
    n = used_orders(scoring)
    dev = [(item_odds(i, scoring), i["label"]) for i in r["items"] if i["split"] == "dev"]
    cal = fit(dev, r["model"], 0.9)
    test = [i for i in r["items"] if i["split"] == "test"]
    rnd = random.Random(11)
    picked = []
    for kind in sorted({i["kind"] for i in test}):
        pool = [i for i in test if i["kind"] == kind]
        picked += rnd.sample(pool, min(3, len(pool)))
    picked.sort(key=lambda i: (NATURAL.index(i["kind"]) if i["kind"] in NATURAL else 99, i["id"]))
    entries = []
    for it in picked:
        per = [dict(zip(o, softmax(it["raw"][k]))) for k, o in enumerate(ORDERS)]
        avg = item_odds(it, scoring)
        stab = sum(1 for p in per[:n] if max(KEYS, key=p.get) == max(KEYS, key=avg.get)) / n if n > 1 else None
        res = choose(it["question"], Odds(avg, stab, per[:n]), cal, text_mode="text" in it)
        entries.append({"question": it["question"], **res, "backend": f"{r['model']} (saved run)", "elapsed_ms": it["ms_scores"]})
    entries = live_extras(r["model"], cal, scoring) + entries
    block = "[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n]"
    page = ROOT / "web" / "index.html"
    html = page.read_text()
    html, n = re.subn(r'(<script type="application/json" id="demo-data">).*?(</script>)',
                      lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), html, count=1, flags=re.S)
    assert n == 1, "demo-data block not found"
    page.write_text(html)
    print(f"wrote {len(entries)} saved answers into {page}")


if __name__ == "__main__":
    main(sys.argv[1])
