"""Run a local Ollama model over bench/questions.jsonl and save receipts (raw odds for every item).

Resumable: finished items are kept in a .partial file, so an interrupted run carries on where it stopped.
    python bench/run.py --model gemma3            # writes bench/receipts/<model>.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eightball.backend import OllamaBackend  # noqa: E402
from eightball.engine import ORDERS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma3")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--questions", default=str(ROOT / "bench" / "questions.jsonl"), help="bench/text_questions.jsonl for text mode")
    ap.add_argument("--scoring", choices=["letter", "word"], default="letter")
    ap.add_argument("--split", choices=["dev", "test", "all"], default="all", help="dev only is a quick way to compare readings")
    ap.add_argument("--limit", type=int, help="only the first N items (for a quick check)")
    ap.add_argument("--out", help="default: bench/receipts/<model>.json")
    a = ap.parse_args()

    items = [json.loads(l) for l in Path(a.questions).read_text().splitlines() if l.strip()]
    if a.split != "all":
        items = [i for i in items if i["split"] == a.split]
    if a.limit:
        items = items[: a.limit]
    slug = a.model.replace(":", "-").replace("/", "-")
    out = Path(a.out) if a.out else ROOT / "bench" / "receipts" / f"{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_suffix(".partial.jsonl")
    done = {}
    if partial.exists():
        for l in partial.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                done[r["id"]] = r

    backend = OllamaBackend(a.model, a.host, scoring=a.scoring)
    t0 = time.time()
    with partial.open("a") as f:
        for n, it in enumerate(items, 1):
            if it["id"] in done:
                continue
            t = time.perf_counter()
            text = it.get("text")  # text-mode items carry the text the question is about
            raw = [backend.scores(it["question"], o, text) if text else backend.scores(it["question"], o) for o in ORDERS]
            t_scores = (time.perf_counter() - t) * 1000
            t = time.perf_counter()
            plain = backend.plain(it["question"], text) if text else backend.plain(it["question"])
            t_plain = (time.perf_counter() - t) * 1000
            rec = {**it, "raw": raw, "plain": plain, "ms_scores": round(t_scores), "ms_plain": round(t_plain)}
            done[it["id"]] = rec
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if n % 25 == 0:
                print(f"{n}/{len(items)} items, {round(time.time() - t0)}s", flush=True)

    result = {"model": a.model, "orders": ORDERS, "n": len(items), "items": [done[i["id"]] for i in items]}
    out.write_text(json.dumps(result))
    partial.unlink()
    print(f"wrote {out} ({len(items)} items)")


if __name__ == "__main__":
    main()
