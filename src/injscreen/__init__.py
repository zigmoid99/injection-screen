"""injscreen: heuristic screening for indirect prompt injection, with a taint gate."""

from .gate import TaintGate
from .screen import ALLOW, BLOCK, FLAG, Result, screen, wrap

__version__ = "0.2.0"

__all__ = ["ALLOW", "BLOCK", "FLAG", "Result", "TaintGate", "screen", "wrap", "__version__"]
