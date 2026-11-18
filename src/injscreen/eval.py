"""Evaluate the screen against the labelled test set in testdata/.

Each JSONL record has: id, category, label ("benign" or "injected"), text.
A prediction counts as positive when the verdict is flag or block.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .screen import ALLOW, screen


@dataclass
class CategoryStats:
    category: str
    label: str
    total: int = 0
    positive: int = 0  # verdict was flag or block

    @property
    def rate(self) -> float:
        return self.positive / self.total if self.total else 0.0


def load_records(data_dir: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(Path(data_dir).glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def evaluate(data_dir: Path) -> tuple[list[CategoryStats], list[dict]]:
    """Return per-category stats and per-record outcomes."""
    stats: dict[str, CategoryStats] = {}
    outcomes: list[dict] = []
    for rec in load_records(data_dir):
        result = screen(rec["text"], source=rec["id"])
        cat = stats.setdefault(
            rec["category"], CategoryStats(rec["category"], rec["label"])
        )
        cat.total += 1
        flagged = result.verdict != ALLOW
        if flagged:
            cat.positive += 1
        outcomes.append(
            {
                "id": rec["id"],
                "category": rec["category"],
                "label": rec["label"],
                "verdict": result.verdict,
                "score": result.score,
                "signals": list(result.signals),
                "correct": flagged == (rec["label"] == "injected"),
            }
        )
    order = ["benign", "direct", "indirect", "paraphrased"]
    ordered = sorted(
        stats.values(),
        key=lambda s: order.index(s.category) if s.category in order else 99,
    )
    return ordered, outcomes


def format_table(stats: list[CategoryStats]) -> str:
    lines = [
        f"{'category':<14}{'label':<10}{'n':>4}{'flagged/blocked':>18}{'rate':>9}",
        "-" * 55,
    ]
    for s in stats:
        metric = "FPR" if s.label == "benign" else "recall"
        lines.append(
            f"{s.category:<14}{s.label:<10}{s.total:>4}"
            f"{s.positive:>18}{s.rate:>8.0%}  {metric}"
        )
    return "\n".join(lines)
