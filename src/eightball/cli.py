"""Command line: ask a question, run the web page, or fit calibration from saved benchmark receipts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .backend import BackendError, OllamaBackend
from .calibrate import Calibration, fit
from .engine import Ball
from .mock import MockBackend

CAL_DIR = Path(__file__).resolve().parents[2] / "calibration"


def _slug(model: str) -> str:
    return model.replace(":", "-").replace("/", "-")


def _backend(a):
    return MockBackend() if a.backend == "mock" else OllamaBackend(a.model, a.host, scoring=a.scoring)


def _calibration(a, text: bool = False) -> Calibration | None:
    """The calibration file for this model and reading: calibration/<model>[-word][-text].json."""
    if a.calibration == "none":
        return None if text else Calibration()
    if a.calibration and not text:
        path = Path(a.calibration)
        if not path.exists():
            sys.exit(f"eightball: calibration file not found: {path}")
        return Calibration.load(path)
    if a.calibration:
        return None  # an explicit file covers plain questions only; text mode falls back to it
    path = CAL_DIR / (_slug(a.model) + ("-word" if a.scoring == "word" else "") + ("-text" if text else "") + ".json")
    if path.exists():
        return Calibration.load(path)
    if not text:
        print(f"eightball: no calibration for {a.model} ({a.scoring} reading; looked for {path}); running uncalibrated", file=sys.stderr)
        return Calibration()
    return None


def _common(p):
    p.add_argument("--backend", choices=["ollama", "mock"], default="ollama")
    p.add_argument("--model", default="gemma3")
    p.add_argument("--host", default="http://127.0.0.1:11434", help="where Ollama is listening")
    p.add_argument("--scoring", choices=["letter", "word"], default="letter", help="how the model's odds are read")
    p.add_argument("--calibration", help='a calibration file, or "none"; default: calibration/<model>.json if present')


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="eightball", description="A Magic 8 Ball that reads a local model's odds.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ask", help="ask one question")
    a.add_argument("question", nargs="+")
    a.add_argument("--json", action="store_true", help="print the full answer as JSON")
    a.add_argument("--text", help="answer about this text instead of from general knowledge")
    a.add_argument("--text-file", help="answer about the text in this file")
    _common(a)

    s = sub.add_parser("serve", help="run the web page and the API")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--cors", action="store_true", help="let other web pages call this server (off by default)")
    _common(s)

    sc = sub.add_parser("score", help="grade the ball on your own questions (a .jsonl file of {question, label})")
    sc.add_argument("file")
    sc.add_argument("--json", action="store_true")
    _common(sc)

    c = sub.add_parser("calibrate", help="fit calibration from benchmark receipts (dev items only)")
    c.add_argument("--receipts", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--target", type=float, default=0.9, help="accuracy wanted when the ball commits to yes or no")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "calibrate":
            from .receipts import dev_samples
            samples, model = dev_samples(args.receipts)
            cal = fit(samples, model, args.target)
            cal.save(args.out)
            print(f"fitted on {cal.n_dev} dev items: temperature {cal.temperature}, threshold {cal.threshold} -> {args.out}")
            return
        ball = Ball(_backend(args), _calibration(args), _calibration(args, text=True))
        if args.cmd == "score":
            from .score import load_items, render, score
            res = score(ball, load_items(args.file))
            print(json.dumps(res, indent=2) if args.json else render(res))
        elif args.cmd == "ask":
            text = Path(args.text_file).read_text() if args.text_file else args.text
            r = ball.ask(" ".join(args.question), text)
            print(json.dumps(r, indent=2) if args.json else f"{r['answer']}   ({r['category']}, {round(r['confidence'] * 100)}% sure)")
        else:
            from .server import serve
            serve(ball, args.bind, args.port, args.cors)
    except (BackendError, ValueError) as e:
        sys.exit(f"eightball: {e}")
