# sheets/__init__.py
# Makes `sheets` a proper Python package.

from sheets.google_sheets import append_rows

__all__ = ["append_rows"]
