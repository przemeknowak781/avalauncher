"""Interfaces to be implemented with audited model and sensor adapters."""

from typing import Protocol

from .models import Grid, SnowObservation, SnowScenario


class SnowDepthSensor(Protocol):
    def observe(self, site_id: str, grid: Grid, timestamp: str) -> SnowObservation: ...


class SnowpackModel(Protocol):
    def scenarios(self, site_id: str, grid: Grid, timestamp: str) -> list[SnowScenario]: ...


class FlowModel(Protocol):
    def run(self, release_scenario_id: str, parameters: dict[str, float]) -> str:
        """Return a reference to stored runout outputs after a real model run."""
        ...
