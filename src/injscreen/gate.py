"""Taint-tracking capability gate (D).

Detection will miss some injections. The gate limits what a missed injection
can do. It tracks how tainted the session is, and asks for approval before a
high-risk tool call once untrusted content has entered the context.

Taint only rises within a session:

    clean -> untrusted -> suspicious -> hostile

    clean       nothing non-user has been ingested
    untrusted   non-user content was ingested and screened as allow
    suspicious  ingested content was flagged
    hostile     ingested content was blocked

Tool decisions:

    low risk                          -> allow (any taint)
    high risk, clean                  -> allow
    high risk, untrusted/suspicious   -> ask the approver (default: deny)
    high risk, hostile                -> deny

Unknown tools are treated as high risk (fail closed). The audit log records
tool names, decisions and taint, never argument values or content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .screen import BLOCK, FLAG, screen, wrap

CLEAN, UNTRUSTED, SUSPICIOUS, HOSTILE = "clean", "untrusted", "suspicious", "hostile"
_ORDER = {CLEAN: 0, UNTRUSTED: 1, SUSPICIOUS: 2, HOSTILE: 3}

DEFAULT_TOOL_RISK: dict[str, str] = {
    "search_web": "low",
    "read_file": "low",
    "calculator": "low",
    "write_file": "high",
    "delete_file": "high",
    "send_email": "high",
    "http_post": "high",
    "run_shell": "high",
}

Approver = Callable[[str, dict], bool]


@dataclass(frozen=True)
class Decision:
    action: str  # allow | ask | deny
    tool: str
    reason: str
    taint: str


@dataclass
class TaintGate:
    tool_risk: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TOOL_RISK))
    approver: Approver | None = None
    taint: str = CLEAN
    audit: list[dict] = field(default_factory=list)

    def ingest(self, text: str, source: str, trust: str = "web") -> str:
        """Screen content, update taint, and return the prompt-ready text."""
        if trust == "user":
            # The user's own input is not an injection channel for this session.
            self._log("ingest", source, "user input", self.taint)
            return text

        result = screen(text, source=source, trust=trust)
        if result.verdict == BLOCK:
            new = HOSTILE
        elif result.verdict == FLAG:
            new = SUSPICIOUS
        else:
            new = UNTRUSTED
        self._raise_taint(new)
        self._log("ingest", source, result.verdict, self.taint)
        return wrap(text, result)

    def authorize(self, tool: str, args: dict | None = None) -> Decision:
        risk = self.tool_risk.get(tool, "high")
        args = args or {}

        if risk == "low":
            decision = Decision("allow", tool, "low-risk tool", self.taint)
        elif self.taint == CLEAN:
            decision = Decision("allow", tool, "no untrusted content in session", self.taint)
        elif self.taint == HOSTILE:
            decision = Decision("deny", tool, "session contains blocked content", self.taint)
        elif self.approver is not None and self.approver(tool, dict(args)):
            decision = Decision("allow", tool, "approved after untrusted content", self.taint)
        elif self.approver is None:
            decision = Decision("deny", tool, "untrusted content; no approver configured", self.taint)
        else:
            decision = Decision("deny", tool, "untrusted content; approval refused", self.taint)

        self._log("authorize", tool, decision.action, self.taint, arg_keys=sorted(args))
        return decision

    def _raise_taint(self, new: str) -> None:
        if _ORDER[new] > _ORDER[self.taint]:
            self.taint = new

    def _log(self, event: str, subject: str, outcome: str, taint: str, **extra) -> None:
        entry = {"event": event, "subject": subject, "outcome": outcome, "taint": taint}
        entry.update(extra)
        self.audit.append(entry)
