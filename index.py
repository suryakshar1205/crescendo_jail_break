"""
Root Python entrypoint for Vercel deployment.
Re-exports the WSGI app and handler from api.index.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.index import app, handler

__all__ = ["app", "handler"]
