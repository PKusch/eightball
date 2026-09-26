"""Checks bench/text_questions.jsonl. Run:  python bench/check_text_questions.py

Three independent checks on every item:
  1. The label is worked out again from the fact table and the question spec alone.
  2. The text is read back: every sentence must match exactly one known sentence pattern, and the
     facts recovered from the words must equal the fact table. The question is read back the same way.
     The label worked out from those recovered facts must agree too.
  3. For "maybe" items, the asked attribute must not be mentioned, by any word from its probe list.
It also checks format, ids, balance, splits, and that the file is exactly what the generator makes.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_text_questions as mt  # noqa: E402

FILE = Path(__file__).resolve().parent / "text_questions.jsonl"
LABELS = {"yes", "no", "maybe"}


def fail(msg: str) -> None:
    raise AssertionError(msg)


def label_from(facts: dict, attr: str, asserted) -> str:
    """The whole rule: not in the table -> maybe; same value -> yes; different value -> no."""
    if attr not in facts:
        return "maybe"
    return "yes" if facts[attr] == asserted else "no"


def pattern(tpl: str, ctx: dict) -> re.Pattern:
    parts = re.split(r"(\{\w+\})", tpl)
    rx = ""
    for p in parts:
        if p == "{v}":
            rx += r"(?P<v>.+?)"
        elif re.fullmatch(r"\{\w+\}", p):
            rx += re.escape(ctx[p[1:-1]])
        else:
            rx += re.escape(p)
    return re.compile(rx)


def read_back(sentence: str, kind: str, ctx: dict, which: str) -> tuple[str, object]:
    """Which attribute and value does this sentence or question state? Exactly one pattern may fit."""
    hits = []
    for a in mt.ATTRS[kind]:
        tpls = a.t if which == "t" else a.q
        pols = [(True, tpls[True]), (False, tpls[False])] if a.is_bool else [(None, tpls)]
        for pol, tpls in pols:
            for tpl in tpls:
                m = pattern(tpl, ctx).fullmatch(sentence)
                if m:
                    hits.append((a, pol if a.is_bool else m.group("v")))
    if len(hits) != 1:
        fail(f"{len(hits)} patterns fit: {sentence!r}")
    a, v = hits[0]
    spec = a.spec
    if spec[0] == "num":
        v = int(v)
    return a.key, v


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=\.) ", text)
    assert all(p.endswith(".") for p in parts), text
    return parts


def recover_facts(text: str, kind: str, ctx: dict) -> dict:
    known_fill = set(mt.FILLERS[kind][0]) | set(mt.FILLERS[kind][1])
    got = {}
    for s in split_sentences(text):
        if s in known_fill:
            continue
        key, v = read_back(s, kind, ctx, "t")
        assert key not in got, ("attribute stated twice", key, text)
        got[key] = v
    return got


def table_sanity() -> None:
    for kind in mt.KINDS:
        keys = [a.key for a in mt.ATTRS[kind]]
        assert len(keys) == len(set(keys)) >= 8, kind
        fill = mt.FILLERS[kind][0] + mt.FILLERS[kind][1]
        assert all(s.endswith(".") and "?" not in s for s in fill), kind
        for a in mt.ATTRS[kind]:
            assert re.compile(a.probe), (kind, a.key)
            for f in fill:      # no filler may state or hint at any attribute
                assert not re.search(a.probe, f.lower()), ("filler hints at", kind, a.key, f)
            if a.is_bool:
                assert set(a.t) == {True, False} == set(a.q), (kind, a.key)
            for tpl in (sum(a.t.values(), []) if a.is_bool else a.t):
                assert tpl.count("{v}") == (0 if a.is_bool else 1), (kind, a.key, tpl)
                assert tpl.endswith("."), tpl
            for tpl in (sum(a.q.values(), []) if a.is_bool else a.q):
                assert tpl.endswith("?"), tpl
                assert tpl.count("{v}") == (0 if a.is_bool else 1), (kind, a.key, tpl)


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
        assert list(it) == mt.FIELDS, ("fields", it)
        assert it["label"] in LABELS, it
        assert it["split"] in ("dev", "test"), it
        assert it["kind"] in mt.PREFIX, it
        assert it["id"].startswith(mt.PREFIX[it["kind"]] + "-"), it
        for f in ("text", "question"):
            assert it[f] and it[f].strip() == it[f], it
        assert it["question"].endswith("?"), it
        n_sent = len(split_sentences(it["text"]))
        assert 3 <= n_sent <= 7, ("sentence count", n_sent, it["id"])
    assert len({it["id"] for it in items}) == len(items), "ids not unique"
    assert len({(it["kind"], it["text"]) for it in items}) == len(items), "a text is used twice"

    by = Counter((it["kind"], it["label"]) for it in items)
    lab = Counter(it["label"] for it in items)
    assert lab["yes"] == lab["no"] == lab["maybe"] == 200, lab
    assert len(items) == 600, len(items)
    for kind in mt.KINDS:
        assert by[(kind, "yes")] == by[(kind, "no")] == by[(kind, "maybe")] == mt.PER_LABEL, kind
        for label in LABELS:
            sp = Counter(it["split"] for it in items if it["kind"] == kind and it["label"] == label)
            assert sp["dev"] and sp["test"], ("a split is missing", kind, label, sp)
            assert abs(sp["dev"] / (sp["dev"] + sp["test"]) - 1 / 3) < 0.05, (kind, label, sp)
    assert {it["split"] for it in items} == {"dev", "test"}

    # every attribute is asked about, under every label
    for kind in mt.KINDS:
        for label in LABELS:
            asked = Counter(it["ask"]["attr"] for it in items if it["kind"] == kind and it["label"] == label)
            assert set(asked) == {a.key for a in mt.ATTRS[kind]}, (kind, label, asked)

    # the wording of the question and the length of the text must not give the label away
    first = defaultdict(Counter)
    for it in items:
        first[it["question"].split()[0]][it["label"]] += 1
    for w, c in first.items():
        if sum(c.values()) >= 40:
            assert all(0.2 <= v / sum(c.values()) <= 0.5 for v in (c["yes"], c["no"], c["maybe"])), (w, c)
    avg = {l: sum(len(split_sentences(it["text"])) for it in items if it["label"] == l) / 200 for l in LABELS}
    assert max(avg.values()) - min(avg.values()) < 0.4, avg
    for l in ("yes", "no"):   # a yes/no policy question is asked in both directions equally often
        pol = [it["ask"]["value"] for it in items if it["label"] == l and isinstance(it["ask"]["value"], bool)]
        assert 0.25 <= sum(pol) / len(pol) <= 0.75, (l, sum(pol), len(pol))

    n_trap = 0
    for it in items:
        facts, ask, kind = it["facts"], it["ask"], it["kind"]
        attr = ask["attr"]
        by_key = {a.key: a for a in mt.ATTRS[kind]}
        assert attr in by_key, it

        # check 1: label from the fact table and the question spec alone
        got = label_from(facts, attr, ask["value"])
        assert got == it["label"], ("label disagrees with facts", it["id"], it["label"], got)
        if it["label"] == "maybe":
            assert attr not in facts, it["id"]
        else:
            assert attr in facts, it["id"]
            if it["label"] == "no":
                assert facts[attr] != ask["value"], it["id"]

        # check 2: read the text and the question back, and recompute
        ctx = {k: facts[k] for k in mt.CTX_KEYS.get(kind, [])}
        recovered = recover_facts(it["text"], kind, ctx)
        stated = {k: v for k, v in facts.items() if k not in ctx}
        assert recovered == stated, ("text does not say what the facts say", it["id"], recovered, stated)
        q_attr, q_val = read_back(it["question"], kind, ctx, "q")
        assert (q_attr, q_val) == (attr, ask["value"]), ("question does not match its spec", it["id"], q_attr, q_val)
        assert label_from(recovered, q_attr, q_val) == it["label"], ("label disagrees with the text", it["id"])

        # check 3: an attribute left out is not mentioned at all
        if it["label"] == "maybe":
            assert not re.search(by_key[attr].probe, it["text"].lower()), ("maybe item mentions it", it["id"], it["text"])
        # a value must be a natural one for its attribute
        spec = by_key[attr].spec
        if spec[0] == "choice":
            assert ask["value"] in spec[1], it["id"]
        if spec[0] in ("num", "money"):
            assert mt.in_range(spec, ask["value"]) or it["label"] == "no", it["id"]
        for k, v in stated.items():
            s = by_key[k].spec
            if s[0] == "choice":
                assert v in s[1], (it["id"], k)
            if s[0] in ("num", "money"):
                assert mt.in_range(s, v), (it["id"], k, v)
        if it["label"] != "yes" and by_key[attr].spec[0] in ("num", "money") and \
                any(k != attr and v == ask["value"] for k, v in stated.items()):
            n_trap += 1

    # the file is exactly what the generator makes
    fresh = [json.dumps(it, ensure_ascii=False) for it in mt.build()]
    assert fresh == raw, "text_questions.jsonl differs from what make_text_questions.py produces; regenerate it"

    n_dev = sum(it["split"] == "dev" for it in items)
    print(f"OK: {len(items)} items, labels {dict(lab)}, dev {n_dev} / test {len(items) - n_dev}")
    print(f"recomputed all {len(items)} labels from the fact table, and again from the words of the text and question")
    print(f"{n_trap} no and maybe items ask about a number that the text states for a different attribute")


if __name__ == "__main__":
    main()
