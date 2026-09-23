import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from api.index import app, handler
except ImportError:
    from index import app, handler  # type: ignore

__all__ = ["app", "handler"]
