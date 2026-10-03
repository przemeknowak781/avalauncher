"""JSON input boundary; external LiDAR and simulation adapters come later."""

import json
from pathlib import Path

from .models import Grid, SnowObservation, SnowScenario


def _grid(data: dict) -> Grid:
    return Grid(**data)


def load_observation(path: str | Path) -> SnowObservation:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SnowObservation(
        grid=_grid(data["grid"]),
        captured_at=data["captured_at"],
        source=data["source"],
        depth_m=tuple(data["depth_m"]),
        uncertainty_m=tuple(data["uncertainty_m"]),
    )


def load_scenarios(path: str | Path) -> list[SnowScenario]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        SnowScenario(
            grid=_grid(item["grid"]),
            scenario_id=item["scenario_id"],
            simulated_at=item["simulated_at"],
            model=item["model"],
            depth_m=tuple(item["depth_m"]),
        )
        for item in data
    ]
