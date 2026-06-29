# handlers/__init__.py
# Makes `handlers` a proper Python package.

from handlers.query_handler import handle_query
from handlers.kpi_handler import handle_kpi
from handlers.export_handler import handle_export
from handlers import static_replies

__all__ = ["handle_query", "handle_kpi", "handle_export", "static_replies"]
