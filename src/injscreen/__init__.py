"""injscreen: heuristic screening for indirect prompt injection."""

from .screen import ALLOW, BLOCK, FLAG, Result, screen, wrap

__version__ = "0.1.0"

__all__ = ["ALLOW", "BLOCK", "FLAG", "Result", "screen", "wrap", "__version__"]
