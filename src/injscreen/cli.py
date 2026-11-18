"""Command-line entry point: `injscreen check` and `injscreen eval`."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from .eval import evaluate, format_table
from .screen import screen, wrap

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "testdata"


def _cmd_check(args: argparse.Namespace) -> int:
    text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(
        encoding="utf-8"
    )
    result = screen(text, source=args.file)
    payload = dataclasses.asdict(result)
    if args.wrap:
        payload["prompt_text"] = wrap(text, result)
    print(json.dumps(payload, indent=2))
    return 0 if result.verdict == "allow" else 1


def _cmd_eval(args: argparse.Namespace) -> int:
    stats, outcomes = evaluate(Path(args.data))
    print(format_table(stats))
    if args.details:
        print()
        for o in outcomes:
            mark = "ok " if o["correct"] else "MISS"
            print(
                f"{mark} {o['id']:<22} {o['label']:<9} {o['verdict']:<6} "
                f"score={o['score']:<2} {','.join(o['signals'])}"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="injscreen",
        description="Screen untrusted text for indirect prompt injection.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="screen one file (or '-' for stdin)")
    p_check.add_argument("file")
    p_check.add_argument("--wrap", action="store_true", help="include prompt-ready text")
    p_check.set_defaults(func=_cmd_check)

    p_eval = sub.add_parser("eval", help="run the labelled test set")
    p_eval.add_argument("--data", default=str(DEFAULT_DATA))
    p_eval.add_argument("--details", action="store_true", help="per-record outcomes")
    p_eval.set_defaults(func=_cmd_eval)

    args = parser.parse_args(argv)
    return args.func(args)
