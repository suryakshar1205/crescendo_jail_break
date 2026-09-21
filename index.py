"""
Root Python entrypoint for Vercel deployment.
Re-exports the WSGI app and handler from api/index.py.
"""
from api.index import app, handler

__all__ = ["app", "handler"]
