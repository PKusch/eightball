"""Checks bench/questions.jsonl. Run:  python bench/check_questions.py

It re-reads the question text and works out the right answer again from scratch for every item
that is arithmetic or a rule (numbers, calendar, words, comparisons, latitudes, atomic numbers),
and against the fact tables for the table-driven kinds. It also checks the file is exactly what
the generator produces, so nobody can hand-edit a label by accident.
"""
from __future__ import annotations

import calendar
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_questions as mq  # noqa: E402

FILE = Path(__file__).resolve().parent / "questions.jsonl"
FIELDS = ["id", "question", "label", "kind", "split"]
LABELS = {"yes", "no", "maybe"}
MONTH_NAMES = mq.MONTHS
DAY_NAMES = mq.WEEKDAYS


def fail(msg: str) -> None:
    raise AssertionError(msg)


def yn(flag: bool) -> str:
    return "yes" if flag else "no"


def match_any(shapes: list[str], q: str, pat: dict | None = None) -> dict | None:
    """Turn '{a}' placeholders into regex groups and see which shape the question follows."""
    for s in shapes:
        rx = re.escape(s)
        for name in re.findall(r"\\\{(\w+)\\\}", rx):
            rx = rx.replace("\\{" + name + "\\}", f"(?P<{name}>{(pat or {}).get(name, '.+?')})", 1)
        m = re.fullmatch(rx, q)
        if m:
            return m.groupdict()
    return None


# ------------------------------------------------------------------------------- rule-based kinds
def truth_arithmetic(q: str) -> str:
    nums = [int(x) for x in re.findall(r"\d+", q)]
    if "answer to" in q:
        claimed, (a, b) = nums[0], nums[1:3]
    else:
        (a, b), claimed = nums[:2], nums[2]
    if " x " in q or "product" in q:
        t = a * b
    elif "divided by" in q:
        t = a / b
    elif "+" in q or " plus " in q or "sum of" in q:
        t = a + b
    elif " - " in q or "minus" in q or "difference" in q:
        t = a - b
    else:
        fail("unknown arithmetic shape: " + q)
    return yn(t == claimed)


def truth_bigger(q: str) -> str:
    m = re.fullmatch(r"Is (\S+) (greater than|larger than|more than|less than|smaller than) (\S+)\?", q)
    a, w, b = Decimal(m.group(1)), m.group(2), Decimal(m.group(3))
    return yn(a > b if w in ("greater than", "larger than", "more than") else a < b)


def truth_number(q: str) -> str:
    n_list = [int(x) for x in re.findall(r"\d+", q)]
    n = n_list[0]
    if "prime" in q or "divisors other than" in q:
        return yn(n > 1 and all(n % d for d in range(2, math.isqrt(n) + 1)))
    if "square" in q:
        return yn(math.isqrt(n) ** 2 == n)
    if "multiple of" in q or "divisible by" in q or "divide evenly" in q:
        a, b = n_list[:2]
        n, k = (b, a) if "divide evenly" in q else (a, b)   # "Does {k} divide evenly into {n}?"
        return yn(n % k == 0)
    if "odd number" in q:
        return yn(n % 2 == 1)
    if "even number" in q:
        return yn(n % 2 == 0)
    fail("unknown number shape: " + q)


def truth_calendar(q: str) -> str:
    dm = re.search(r"(\d{1,2}) (%s) (\d{4})" % "|".join(MONTH_NAMES), q)
    if dm:
        d = date(int(dm.group(3)), MONTH_NAMES.index(dm.group(2)) + 1, int(dm.group(1)))
        wd = re.search("|".join(DAY_NAMES), q).group(0)
        return yn(DAY_NAMES[d.weekday()] == wd)
    ms = [(m.start(), m.group(0)) for m in re.finditer("|".join(MONTH_NAMES), q)]
    if "days" in q and "366" not in q:
        n = int(re.search(r"(\d+) days", q).group(1))
        y = re.search(r"\b(19|20)\d\d\b", q)
        year = int(y.group(0)) if y else 2023
        if ms[0][1] == "February" and not y:
            fail("February without a year: " + q)
        return yn(calendar.monthrange(year, MONTH_NAMES.index(ms[0][1]) + 1)[1] == n)
    y = re.search(r"\b(\d{4})\b", q)
    if y and ("leap" in q or "366" in q):
        return yn(calendar.isleap(int(y.group(1))))
    if len(ms) == 2:
        a, b = (MONTH_NAMES.index(m[1]) for m in ms)
        return yn(a < b if ("before" in q or "earlier" in q) else a > b)
    fail("unknown calendar shape: " + q)


def truth_word(q: str) -> str:
    w = re.search(r"'(\w+)'", q)
    w = w.group(1) if w else None
    letters = re.findall(r"\b([A-Z])\b", q)
    if "contain the letter" in q or "a letter" in q or "find the letter" in q:
        return yn(letters[0].lower() in w)
    if "start with" in q or "begin with" in q or "first letter" in q:
        return yn(w[0] == letters[0].lower())
    if "end with" in q or "last letter" in q:
        return yn(w[-1] == letters[0].lower())
    if "longer than" in q or "more than" in q:
        return yn(len(w) > int(re.search(r"\d+", q).group(0)))
    if "shorter than" in q:
        return yn(len(w) < int(re.search(r"\d+", q).group(0)))
    if "backwards" in q:
        return yn(w == w[::-1])
    if "alphabet" in q:
        a, b = letters
        return yn(a < b if ("before" in q or "earlier" in q) else a > b)
    fail("unknown word shape: " + q)


def find_names(q: str, names) -> list[str]:
    hits = []
    for n in names:
        for m in re.finditer(r"(?<![\w])" + re.escape(n) + r"(?![\w])", q):
            hits.append((m.start(), n))
    return [n for _, n in sorted(hits)]


def truth_compare(q: str) -> str:
    for g in mq.COMPARE:
        for w, hi in ((g["hi"], True), (g["lo"], False)):
            if re.search(r"\b" + w + r"\b", q):
                names = find_names(q, g["items"])
                if len(names) == 2:
                    a, b = (g["items"][n] for n in names)
                    if max(a, b) / min(a, b) < g["ratio"]:
                        fail("gap too small: " + q)
                    return yn(a > b if hi else a < b)
    fail("unknown compare shape: " + q)


# -------------------------------------------------------------------------------- table-driven kinds
def truth_capital(q: str) -> str:
    m = match_any(mq.CAPITAL_SHAPES, q, {"c": "|".join(map(re.escape, mq.CAPITALS)), "cap": "|".join(re.escape(v[0]) for v in mq.CAPITALS.values())})
    if not m:
        fail("unknown capital shape: " + q)
    return yn(mq.CAPITALS[m["c"]][0] == m["cap"])


def truth_physical(q: str) -> str:
    for tmpl, trues, wrongs in mq.PHYSICAL:
        m = match_any([tmpl], q)
        if m:
            v = int(m["v"].replace(",", ""))
            if v in trues:
                return "yes"
            if v in wrongs:
                return "no"
            fail("value in neither list: " + q)
    fail("unknown physical fact: " + q)


def truth_animal(q: str) -> str:
    m = re.fullmatch(r"Can (?:an? )(\w+) fly\?|Is (?:an? )(\w+) able to fly\?|Would (?:an? )(\w+) be able to fly\?", q)
    if m:
        a = next(x for x in m.groups() if x)
        return yn(a in mq.CAN_FLY) if a in mq.CAN_FLY + mq.CANNOT_FLY else fail("fly: " + q)
    m = re.fullmatch(r"Does (?:an? )(\w+) lay eggs\?|Can (?:an? )(\w+) lay eggs\?", q)
    if m:
        a = next(x for x in m.groups() if x)
        return yn(a in mq.LAYS_EGGS) if a in mq.LAYS_EGGS + mq.NO_EGGS else fail("eggs: " + q)
    m = match_any(mq.CLASS_SHAPES, q, {"a": r"an? \w+", "c": r"an? \w+"})
    if m:
        a, c = m["a"].split(" ", 1)[1], m["c"].split(" ", 1)[1]
        return yn(mq.ANIMAL_CLASS[a] == c)
    fail("unknown animal shape: " + q)


def truth_geo(q: str) -> str:
    if "Hemisphere" in q:
        m = match_any(mq.HEMI_SHAPES, q)
        return yn((mq.LATITUDE[m["a"]] > 0) == (m["h"] == "Northern"))
    m = match_any(mq.CONTINENT_SHAPES, q, {"x": "|".join(map(re.escape, mq.PLACE_CONTINENT)), "k": "|".join(mq.CONTINENTS)})
    if m:
        return yn(mq.PLACE_CONTINENT[m["x"]] == m["k"])
    for shapes, north in ((mq.NORTH_SHAPES, True), (mq.SOUTH_SHAPES, False)):
        m = match_any(shapes, q)
        if m:
            a, b = mq.LATITUDE[m["a"]], mq.LATITUDE[m["b"]]
            if abs(a - b) < 8:
                fail("latitude gap too small: " + q)
            return yn(a > b if north else a < b)
    m = match_any(mq.HEMI_SHAPES, q)
    if m:
        lat = mq.LATITUDE[m["a"]]
        return yn((lat > 0) == (m["h"] == "Northern"))
    m = match_any([mq.LAND_SHAPE_A], q)
    if m:
        c = m["c"]
        return yn(c in mq.LANDLOCKED) if c in mq.LANDLOCKED + mq.COASTAL else fail("country: " + q)
    m = match_any([mq.LAND_SHAPE_B], q)
    if m:
        c = m["c"]
        return yn(c in mq.COASTAL) if c in mq.LANDLOCKED + mq.COASTAL else fail("country: " + q)
    fail("unknown geo shape: " + q)


def truth_chemistry(q: str) -> str:
    m = match_any(mq.SYMBOL_SHAPES, q)
    if m:
        return yn(mq.ELEMENTS[m["n"]][0] == m["s"])
    m = match_any(mq.ORDER_SHAPES, q)
    if m:
        za, zb = mq.ELEMENTS[m["a"]][1], mq.ELEMENTS[m["b"]][1]
        if abs(za - zb) < 5:
            fail("atomic numbers too close: " + q)
        return yn(za < zb if m["w"] == "lower" else za > zb)
    m = match_any(mq.FORMULA_SHAPES, q)
    if m:
        return yn(mq.COMPOUNDS[m["n"]] == m["f"])
    m = match_any(mq.STATE_SHAPES, q)
    if m:
        return yn(mq.ELEMENTS[m["n"]][2] == m["st"])
    fail("unknown chemistry shape: " + q)


def truth_history(q: str) -> str:
    for noun, year, tmpl in mq.HISTORY:
        m = match_any([tmpl], q)
        if m:
            return yn(int(m["y"]) == year)
    m = match_any(mq.HISTORY_ORDER_SHAPES, q)
    if m:
        ya = next(y for n, y, _ in mq.HISTORY if n == m["a"])
        yb = next(y for n, y, _ in mq.HISTORY if n == m["b"])
        if abs(ya - yb) < 20:
            fail("years too close: " + q)
        return yn(ya < yb if q.startswith("Did") and " before " in q else ya > yb)
    fail("unknown history shape: " + q)


TRUTH = {
    "arithmetic": truth_arithmetic, "bigger": truth_bigger, "number": truth_number, "calendar": truth_calendar,
    "word": truth_word, "compare": truth_compare, "capital": truth_capital, "physical": truth_physical,
    "animal": truth_animal, "geo": truth_geo, "chemistry": truth_chemistry, "history": truth_history,
}


def table_sanity() -> None:
    caps = [v[0] for v in mq.CAPITALS.values()]
    assert len(caps) == len(set(caps)), "two countries share a capital"
    assert len({v[0] for v in mq.ELEMENTS.values()}) == len(mq.ELEMENTS), "duplicate element symbol"
    assert len({v[1] for v in mq.ELEMENTS.values()}) == len(mq.ELEMENTS), "duplicate atomic number"
    assert len(set(mq.COMPOUNDS.values())) == len(mq.COMPOUNDS)
    assert not set(mq.LANDLOCKED) & set(mq.COASTAL)
    assert len(mq.ANIMAL_CLASS) == sum(len(v) for v in mq.ANIMALS.values()), "animal listed in two classes"
    assert not set(mq.CAN_FLY) & set(mq.CANNOT_FLY) and not set(mq.LAYS_EGGS) & set(mq.NO_EGGS)
    for _, trues, wrongs in mq.PHYSICAL:
        assert not set(trues) & set(wrongs)
    assert len({y for _, y, _ in mq.HISTORY}) == len(mq.HISTORY), "two events share a year"
    for pal in mq.PALINDROMES:
        assert pal == pal[::-1]
    for w in mq.NOT_PALINDROMES:
        assert w != w[::-1], w


def main() -> None:
    table_sanity()
    raw = FILE.read_text(encoding="utf-8").splitlines()
    items = []
    for i, line in enumerate(raw, 1):
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as e:
            fail(f"line {i} is not valid JSON: {e}")
    for it in items:
        assert list(it) == FIELDS, ("fields", it)
        assert it["label"] in LABELS, it
        assert it["split"] in ("dev", "test"), it
        assert it["kind"] in mq.PREFIX, it
        assert it["id"].startswith(mq.PREFIX[it["kind"]] + "-"), it
        assert it["question"].strip() == it["question"] and it["question"], it
    assert len({it["id"] for it in items}) == len(items), "ids not unique"
    assert len({it["question"].lower() for it in items}) == len(items), "questions not unique"

    by = Counter((it["kind"], it["label"]) for it in items)
    lab = Counter(it["label"] for it in items)
    assert lab["yes"] == lab["no"] == lab["maybe"] == 300, lab
    for kind in mq.YESNO_KINDS:
        assert by[(kind, "yes")] == by[(kind, "no")] > 0, (kind, by[(kind, "yes")], by[(kind, "no")])
        assert by[(kind, "maybe")] == 0
    for kind in mq.MAYBE_KINDS:
        assert by[(kind, "maybe")] == 75 and by[(kind, "yes")] == by[(kind, "no")] == 0, kind
    for kind in mq.PREFIX:
        for label in LABELS:
            if by[(kind, label)]:
                sp = Counter(it["split"] for it in items if it["kind"] == kind and it["label"] == label)
                assert sp["dev"] and sp["test"], ("a split is missing", kind, label, sp)
                assert abs(sp["dev"] / (sp["dev"] + sp["test"]) - 1 / 3) < 0.1, (kind, label, sp)

    # yes and no must not be guessable from the opening word of the question
    first = defaultdict(Counter)
    for it in items:
        if it["label"] != "maybe":
            first[it["question"].split()[0]][it["label"]] += 1
    for w, c in first.items():
        if c["yes"] + c["no"] >= 20:
            assert 0.35 <= c["yes"] / (c["yes"] + c["no"]) <= 0.65, ("opening word gives the answer away", w, c)

    # every yes/no label recomputed from the question text
    bad = []
    for it in items:
        if it["label"] == "maybe":
            continue
        got = TRUTH[it["kind"]](it["question"])
        if got != it["label"]:
            bad.append((it["id"], it["question"], it["label"], got))
    assert not bad, "labels disagree with the recomputed answer:\n" + "\n".join(map(str, bad[:20]))

    # maybe-items: shape checks and the filler cap
    for it in items:
        if it["label"] == "maybe" and it["kind"] in ("future", "private", "taste"):
            assert it["question"].endswith("?"), it
    mq.build()
    over = {k: v for k, v in mq.FILL.use.items() if v > mq.FILLER_CAP}
    assert not over, ("filler used too often", over)

    # the file is exactly what the generator makes
    fresh = [json.dumps(it, ensure_ascii=False) for it in mq.build()]
    assert fresh == raw, "questions.jsonl differs from what make_questions.py produces; regenerate it"

    n_dev = sum(it["split"] == "dev" for it in items)
    print(f"OK: {len(items)} items, labels {dict(lab)}, dev {n_dev} / test {len(items) - n_dev}")
    print(f"recomputed {sum(it['label'] != 'maybe' for it in items)} yes/no labels from the question text")


if __name__ == "__main__":
    main()
