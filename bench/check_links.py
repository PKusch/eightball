#!/usr/bin/env python3
"""Every relative markdown link in the repo must resolve, heading anchors included.

The docs here point at each other a lot (the README at the question sets, the audit,
the scoring notes, the contract), and moving or renaming one breaks every link to it
without anything failing. Renaming a heading breaks a #anchor the same way while the
file path stays right, so the heading is checked too, the way GitHub builds it.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"```.*?```", re.S)
bad = 0
_anchors: dict[Path, set[str]] = {}


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: markup dropped, lower case, punctuation removed,
    spaces turned into hyphens."""
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)      # [text](url) -> text
    h = re.sub(r"<[^>]+>|[`*]", "", h)
    h = re.sub(r"(?<!\w)_|_(?!\w)", "", h).strip().lower()
    return re.sub(r"[^\w\- ]", "", h).replace(" ", "-")


def anchors(md: Path) -> set[str]:
    if md not in _anchors:
        found: set[str] = set()
        seen: dict[str, int] = {}
        text = FENCE.sub("", md.read_text(encoding="utf-8"))
        for line in text.splitlines():
            m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
            if m:
                s_ = slug(m.group(1))
                n = seen.get(s_, 0)
                seen[s_] = n + 1
                found.add(s_ if n == 0 else f"{s_}-{n}")      # a repeated heading gets -1, -2
            found.update(re.findall(r'<a\s+(?:name|id)="([^"]+)"', line))
        _anchors[md] = found
    return _anchors[md]


for md in sorted(ROOT.rglob("*.md")):
    if ".git" in md.parts:
        continue
    for target in LINK.findall(FENCE.sub("", md.read_text(encoding="utf-8"))):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, fragment = target.partition("#")
        path = (md.parent / file_part).resolve() if file_part else md
        if not path.exists():
            print(f"  ✗ {md.relative_to(ROOT)} → {target}")
            bad += 1
        elif fragment and path.suffix == ".md" and fragment.lower() not in anchors(path):
            print(f"  ✗ {md.relative_to(ROOT)} → {target}   (no heading '{fragment}' in {path.relative_to(ROOT)})")
            bad += 1

print(f"\n{'✗' if bad else '✓'} {bad} broken link(s)")
sys.exit(1 if bad else 0)
