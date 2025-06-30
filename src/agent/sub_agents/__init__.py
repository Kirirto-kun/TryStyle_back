# Sub-agents package for specialized AI agents

from .base import (
    Product,
    ProductList,
    Outfit,
    GeneralResponse,
    AgentResponse
)
from .coordinator_agent import coordinate_request
from .catalog_search_agent import get_catalog_search_agent, search_catalog_products  # НОВЫЙ - поиск в локальном каталоге

__all__ = [
    "Product",
    "ProductList",
    "Outfit",
    "GeneralResponse",
    "AgentResponse",
    "coordinate_request",
    "get_catalog_search_agent",
    "search_catalog_products",
]