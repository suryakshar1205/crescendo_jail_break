"""
Vercel Serverless Function file route for /api/status.
"""
from api.index import app, handler

__all__ = ["app", "handler"]
