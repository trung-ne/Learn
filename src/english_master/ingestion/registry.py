"""Fail-closed adapter registry keyed by stable source IDs."""

from __future__ import annotations

from english_master.ingestion.base import SourceAdapter


class AdapterRegistryError(ValueError):
    """Raised for unknown, duplicate, or mismatched adapter registrations."""


class AdapterRegistry:
    """Register source-isolated adapters without source conditionals in the pipeline."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter[object]] = {}

    def register(
        self,
        source_id: str,
        adapter: SourceAdapter[object],
    ) -> None:
        if source_id != adapter.source_id:
            raise AdapterRegistryError(
                f"Adapter {adapter.adapter_id!r} declares {adapter.source_id!r}, not {source_id!r}"
            )
        if source_id in self._adapters:
            raise AdapterRegistryError(f"An adapter is already registered for {source_id!r}")
        self._adapters[source_id] = adapter

    def get(self, source_id: str) -> SourceAdapter[object]:
        try:
            return self._adapters[source_id]
        except KeyError as error:
            raise AdapterRegistryError(f"No adapter is registered for source {source_id!r}") from error

    def available_source_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
