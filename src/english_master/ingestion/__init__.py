"""M3 adapter-based ingestion infrastructure."""

from english_master.ingestion.adapters.tatoeba_text import TatoebaTextAdapter
from english_master.ingestion.registry import AdapterRegistry


def default_adapter_registry() -> AdapterRegistry:
    """Return the explicitly registered adapters available in this release."""

    registry = AdapterRegistry()
    registry.register(TatoebaTextAdapter.source_id, TatoebaTextAdapter())
    return registry


__all__ = ["default_adapter_registry"]
