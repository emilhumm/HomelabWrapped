"""Homelab Wrapped core: plain Python with no Home Assistant imports.

Everything here works on plain data (see ``model.py``) that the Home Assistant
layer fills in, so a standalone version can reuse it as it is. Two rules keep it
that way, and ``tests/core/test_purity.py`` checks both:

- nothing in this package imports ``homeassistant``;
- modules here import each other relatively (``from .model import ...``).
"""
