# tools/__init__.py
# Makes `tools` a proper Python package.
# Import shortcuts so agent files can do:
#   from tools import execute_query, get_schema

from tools.postgres_tool import execute_query
from tools.schema_tool import get_schema

__all__ = ["execute_query", "get_schema"]
