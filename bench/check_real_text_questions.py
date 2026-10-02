"""Checks bench/real_text_questions.jsonl. Run:  python bench/check_real_text_questions.py

These items are hand-written from real documents (USAJOBS postings, SEC-filed commercial
leases), not generated from a fact table, so a label cannot be mechanically re-derived the
way bench/check_text_questions.py does for the synthetic set. Instead every item carries a
`facts` field that names the exact substring(s) grounding its label, and this script checks
the one thing that IS mechanical:

  - for every "yes" or "no" item, each string in facts["present"] must actually occur in
    `text` (case-insensitive) -- i.e. the excerpt really does say the thing the question
    and label depend on;
  - for every "maybe" item, none of the strings in facts["absent"] may occur in `text`
    (case-insensitive) -- i.e. the excerpt genuinely never touches that topic.

It also checks the basic format: valid JSON, required fields, labels in {yes, no, maybe},
unique ids, unique questions, both splits present, and a `source` on every item.

This does NOT verify that the label itself is the correct reading of the text -- that is a
human judgment call, made once by reading each item (see bench/REAL_QUESTIONS.md).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

FILE = Path(__file__).resolve().parent / "real_text_questions.jsonl"
LABELS = {"yes", "no", "maybe"}
KINDS = {"job_real", "lease_real"}
FIELDS = ["id", "text", "question", "label", "kind", "split", "facts", "source"]


def fail(msg: str) -> None:
    raise AssertionError(msg)


def main() -> None:
    raw = FILE.read_text(encoding="utf-8").splitlines()
    items = []
    for i, line in enumerate(raw, 1):
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as e:
            fail(f"line {i} is not valid JSON: {e}")

    for it in items:
        assert set(FIELDS) <= set(it), ("missing field", it.get("id"), set(FIELDS) - set(it))
        assert it["label"] in LABELS, it
        assert it["split"] in ("dev", "test"), it
        assert it["kind"] in KINDS, it
        for f in ("text", "question", "id", "source"):
            assert isinstance(it[f], str) and it[f].strip() == it[f] and it[f], (f, it["id"])
        assert it["question"].endswith("?"), it["id"]
        assert isinstance(it["facts"], dict), it["id"]

    ids = [it["id"] for it in items]
    assert len(set(ids)) == len(ids), "ids not unique"
    questions = [(it["kind"], it["question"]) for it in items]
    dupes = [q for q, n in Counter(questions).items() if n > 1]
    assert not dupes, ("duplicate question within a kind", dupes)

    assert {it["split"] for it in items} == {"dev", "test"}
    for kind in KINDS:
        sub = [it for it in items if it["kind"] == kind]
        assert sub, kind
        for label in LABELS:
            sp = Counter(it["split"] for it in sub if it["label"] == label)
            assert sp["dev"] and sp["test"], ("a split is missing", kind, label, sp)

    n_present_checks = 0
    n_absent_checks = 0
    for it in items:
        text_lc = it["text"].lower()
        facts = it["facts"]
        if it["label"] in ("yes", "no"):
            present = facts.get("present")
            assert isinstance(present, list) and present and all(isinstance(x, str) for x in present), \
                ("yes/no item needs facts.present as a non-empty list of strings", it["id"])
            for phrase in present:
                n_present_checks += 1
                assert phrase.lower() in text_lc, (
                    "grounding phrase not found in text", it["id"], phrase)
        elif it["label"] == "maybe":
            absent = facts.get("absent")
            assert isinstance(absent, list) and absent and all(isinstance(x, str) for x in absent), \
                ("maybe item needs facts.absent as a non-empty list of strings", it["id"])
            for phrase in absent:
                n_absent_checks += 1
                assert phrase.lower() not in text_lc, (
                    "'maybe' item's text actually mentions this", it["id"], phrase)

    # a text should not be reused verbatim across items of the same kind (each excerpt is
    # its own "document"), though different questions about the same excerpt are expected
    text_reuse = Counter((it["kind"], it["text"]) for it in items)
    n_excerpts = len(text_reuse)

    lab = Counter(it["label"] for it in items)
    by_kind = Counter(it["kind"] for it in items)
    by_kind_label = Counter((it["kind"], it["label"]) for it in items)
    n_dev = sum(it["split"] == "dev" for it in items)

    print(f"OK: {len(items)} items across {n_excerpts} distinct excerpts")
    print(f"by kind: {dict(by_kind)}")
    print(f"by label: {dict(lab)}")
    print(f"by kind+label: {dict(by_kind_label)}")
    print(f"dev {n_dev} / test {len(items) - n_dev}")
    print(f"checked {n_present_checks} grounding phrases for yes/no items "
          f"and {n_absent_checks} absence checks for maybe items")


if __name__ == "__main__":
    main()
