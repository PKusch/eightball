"""Turn receipts into the scoreboard. No model needed: everything is recomputed from bench/receipts/<model>.json.

Calibration is fitted on the dev items only; every number below is from the test items.
    python bench/report.py bench/receipts/gemma3-4b.json
"""
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eightball.calibrate import KEYS, Calibration, fit  # noqa: E402
from eightball.engine import ORDERS, Odds, choose, softmax  # noqa: E402
from eightball.receipts import item_odds, scoring_of, used_orders  # noqa: E402

TARGET = 0.9


STOP = set("a an the is are was were be it its of to in on at for and or do does did can could will would has have had this that these those there their they you your with by from as not no any which what when who how".split())
WORD = __import__("re").compile(r"[a-z0-9]+")


def word_match(item):
    """A no-model yardstick for text mode: if a question word is missing from the text, 'maybe'; else if
    every number in the question appears in the text, 'yes'; otherwise 'no'. It sees only the text and the question."""
    text = set(WORD.findall(item["text"].lower()))
    q = [w for w in WORD.findall(item["question"].lower()) if w not in STOP]
    stem = lambda w: w[:5]
    text_stems = {stem(w) for w in text}
    words = [w for w in q if not w.isdigit()]
    nums = [w for w in q if w.isdigit()]
    if any(stem(w) not in text_stems for w in words):
        return "maybe"
    return "yes" if all(n in text for n in nums) else "no"


def per_order(item):
    return [dict(zip(o, softmax(item["raw"][i]))) for i, o in enumerate(ORDERS)]


def top(p):
    return max(KEYS, key=p.get)


def systems(item, cal, scoring):
    n = used_orders(scoring)
    po = per_order(item)
    avg = item_odds(item, scoring)          # what the ball uses
    avg_all = item_odds(item, "letter")     # all three orders averaged, for the "shuffled" column
    stab = sum(1 for p in po[:n] if top(p) == top(avg)) / n if n > 1 else None
    ball = choose(item["question"], Odds(avg, stab, po[:n]), cal, text_mode="text" in item)
    extra = {"word match": word_match(item)} if "text" in item else {}
    return {
        **extra,
        "plain": item["plain"],
        "one order": top(po[0]),
        "shuffled": top(avg_all),
        "ball": ball["category"],
    }, ball, po, avg


def ece(pairs, bins=10):
    """Average gap between how sure the model said it was and how often it was right, over confidence bins."""
    buckets = defaultdict(list)
    for conf, ok in pairs:
        buckets[min(int(conf * bins), bins - 1)].append((conf, ok))
    n = len(pairs)
    return sum(len(b) / n * abs(sum(c for c, _ in b) / len(b) - sum(o for _, o in b) / len(b)) for b in buckets.values())


def pct(x):
    return f"{100 * x:.1f}%"


def boot(diffs, n=2000, seed=1):
    rnd = random.Random(seed)
    m = len(diffs)
    means = sorted(sum(diffs[rnd.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def main(path):
    r = json.loads(Path(path).read_text())
    items = r["items"]
    scoring = scoring_of(r)
    dev = [(item_odds(i, scoring), i["label"]) for i in items if i["split"] == "dev"]
    test = [i for i in items if i["split"] == "test"]
    cal = fit(dev, r["model"], TARGET)
    rows = []
    for it in test:
        s, ball, po, avg = systems(it, cal, scoring)
        rows.append((it, s, ball, po, avg))

    names = (["word match"] if "text" in test[0] else []) + ["plain", "one order", "shuffled", "ball"]
    out = [f"# Scoreboard: {r['model']}", "",
           f"{len(items)} questions; calibration fitted on {len(dev)} dev items "
           f"(temperature {cal.temperature}, commit threshold {cal.threshold:.3f}); every number below is from the other {len(test)} test items.", ""]

    # headline
    ball_head = "The ball (shuffled + calibrated)" if scoring == "letter" else "The ball (natural order + calibrated)"
    heads = {"word match": "Word match (no model)", "plain": "Plain answer", "one order": "One ordering",
             "shuffled": "Three orders averaged", "ball": ball_head}
    out += ["| | " + " | ".join(heads[n] for n in names) + " |", "|---" * (len(names) + 1) + "|"]

    def acc(name):
        return sum(1 for it, s, *_ in rows if s[name] == it["label"]) / len(rows)

    def commits(name):
        c = [(it, s) for it, s, *_ in rows if s[name] != "maybe"]
        return c

    def wrong_commit(name):
        c = commits(name)
        return sum(1 for it, s in c if s[name] != it["label"]) / len(c) if c else 0.0

    out.append("| Right group (yes / maybe / no) | " + " | ".join(pct(acc(n)) for n in names) + " |")
    out.append("| Said a plain yes or no | " + " | ".join(pct(len(commits(n)) / len(rows)) for n in names) + " |")
    out.append("| Of those, wrong | " + " | ".join(pct(wrong_commit(n)) for n in names) + " |")
    for lab in KEYS:
        sub = [x for x in rows if x[0]["label"] == lab]
        out.append(f"| Right on {lab} items ({len(sub)}) | " + " | ".join(pct(sum(1 for it, s, *_ in sub if s[n] == lab) / len(sub)) for n in names) + " |")
    ms = statistics.median(i["ms_scores"] for i in test)
    mp = statistics.median(i["ms_plain"] for i in test)
    times = {"word match": "0 ms", "plain": f"{mp:.0f} ms", "one order": f"{ms/3:.0f} ms", "shuffled": f"{ms:.0f} ms",
             "ball": f"{ms:.0f} ms" if scoring == "letter" else f"{ms/3:.0f} ms"}
    out.append("| Typical time | " + " | ".join(times[n] for n in names) + " |")
    out += ["", '"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.', ""]

    # significance
    out += ["## Gaps and whether they are outside noise", "", "Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.", ""]
    for other in [n for n in names if n != "ball"]:
        d = [(s["ball"] == it["label"]) - (s[other] == it["label"]) for it, s, *_ in rows]
        lo, hi = boot(d)
        out.append(f"- Right group, ball vs {other}: {100*sum(d)/len(d):+.1f} points [{100*lo:+.1f}, {100*hi:+.1f}] "
                   + ("outside noise" if lo > 0 or hi < 0 else "inside noise"))
    out.append("")

    # position bias
    disagree = sum(1 for it, s, ball, po, avg in rows if len({top(p) for p in po}) > 1) / len(rows)
    out += ["## Does reordering the options change the answer?", "",
            f"Reading the model in a single fixed order, its pick changed when the options were reordered on {pct(disagree)} of items. "
            + ("The ball reads three orders and averages them, so its own answer does not depend on the order." if scoring == "letter" else
               "In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.") + "", ""]
    # calibration
    raw_pairs = [(avg[top(avg)], top(avg) == it["label"]) for it, s, ball, po, avg in rows]
    cal_pairs = []
    for it, s, ball, po, avg in rows:
        q = cal.apply(avg)
        cal_pairs.append((q[top(q)], top(q) == it["label"]))
    out += ["## Can you trust the confidence?", "",
            "Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).", "",
            f"- Before calibration: {ece(raw_pairs):.3f}", f"- After calibration: {ece(cal_pairs):.3f}", ""]

    # the strictness dial: how much the ball says versus how often it is wrong when it says it
    out += ["## The strictness dial", "",
            "The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. "
            "A stricter ball says less and is wrong less often when it does speak.", "",
            "| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |", "|---|---|---|---|"]
    from eightball.calibrate import fit_threshold
    for tgt in (0.75, 0.8, 0.85, 0.9, 0.95):
        c2 = Calibration(temperature=cal.temperature, threshold=fit_threshold(dev, cal.temperature, tgt), model=cal.model)
        res = [(it, choose(it["question"], Odds(item_odds(it, scoring), None, per_order(it)[:used_orders(scoring)]), c2, text_mode="text" in it)) for it in test]
        said = [(it, b) for it, b in res if b["category"] != "maybe"]
        wr = sum(1 for it, b in said if b["category"] != it["label"]) / len(said) if said else 0.0
        mark = " (default)" if tgt == TARGET else ""
        out.append(f"| {int(tgt * 100)}%{mark} | {pct(len(said) / len(res))} | {pct(wr)} | {pct(sum(1 for it, b in res if b['category'] == it['label']) / len(res))} |")
    out.append("")

    # per kind
    kinds = sorted({it["kind"] for it, *_ in rows})
    out += ["## By kind of question", "", "| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |", "|---|---|---|---|---|---|"]
    for k in kinds:
        sub = [x for x in rows if x[0]["kind"] == k]
        lab = " or ".join(sorted({x[0]["label"] for x in sub}))
        out.append(f"| {k} | {lab} | {len(sub)} | {pct(sum(1 for it, s, *_ in sub if s['plain'] == it['label']) / len(sub))} | "
                   f"{pct(sum(1 for it, s, *_ in sub if s['ball'] == it['label']) / len(sub))} | "
                   f"{pct(sum(1 for it, s, *_ in sub if s['ball'] == 'maybe') / len(sub))} |")
    out.append("")

    # ladder
    by_phrase = defaultdict(list)
    for it, s, ball, *_ in rows:
        by_phrase[ball["answer"]].append(ball["category"] == it["label"])
    out += ["## Does a stronger phrase mean a more reliable answer?", "",
            "Each phrase the ball used on the test items, and how often the group it named was right.", "", "| Phrase | Times said | Right |", "|---|---|---|"]
    from eightball.answers import ANSWERS
    for cat in ("yes", "no"):
        for ph in ANSWERS[cat]:
            if ph in by_phrase:
                v = by_phrase[ph]
                out.append(f"| {ph} | {len(v)} | {pct(sum(v) / len(v))} |")
    hazy = [v for ph in ANSWERS["maybe"] for v in [by_phrase.get(ph, [])] if v]
    total_hazy = sum(len(v) for v in hazy)
    if total_hazy:
        out.append(f"| (all hazy phrases together) | {total_hazy} | {pct(sum(sum(v) for v in hazy) / total_hazy)} |")
    out.append("")

    Path(path).with_suffix(".md").write_text("\n".join(out) + "\n")
    summary = {"model": r["model"], "scoring": scoring, "n_test": len(rows), "temperature": cal.temperature, "threshold": cal.threshold,
               **{f"acc_{n.replace(' ', '_')}": acc(n) for n in names}, **{f"wrong_commit_{n.replace(' ', '_')}": wrong_commit(n) for n in names}}
    Path(path).with_name(Path(path).stem + "-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
