"""Minimal, already-coregistered raster inputs for scenario comparison.

Physical model outputs and observations must be preprocessed onto exactly the
same projected grid. This module intentionally does not resample geospatial data.
"""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True)
class Grid:
    site_id: str
    grid_id: str
    crs: str
    cell_size_m: float
    width: int
    height: int

    def __post_init__(self) -> None:
        if not self.site_id or not self.grid_id or not self.crs:
            raise ValueError("site_id, grid_id and crs are required")
        if not self.crs.startswith("EPSG:"):
            raise ValueError("crs must be an explicit EPSG code")
        if not isfinite(self.cell_size_m) or self.cell_size_m <= 0:
            raise ValueError("cell_size_m must be positive and finite")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")

    @property
    def size(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class SnowObservation:
    grid: Grid
    captured_at: str
    source: str
    depth_m: tuple[float | None, ...]
    uncertainty_m: tuple[float | None, ...]

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("observation source is required")
        timestamp = datetime.fromisoformat(self.captured_at.replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        if len(self.depth_m) != self.grid.size or len(self.uncertainty_m) != self.grid.size:
            raise ValueError("observation arrays must match grid dimensions")
        for depth, uncertainty in zip(self.depth_m, self.uncertainty_m):
            if depth is None and uncertainty is None:
                continue
            if depth is None or uncertainty is None:
                raise ValueError("depth and uncertainty must share a missing-data mask")
            if not isfinite(depth) or depth < 0:
                raise ValueError("snow depth must be finite and nonnegative")
            if not isfinite(uncertainty) or uncertainty <= 0:
                raise ValueError("uncertainty must be positive and finite")
        if all(value is None for value in self.depth_m):
            raise ValueError("at least one observed cell is required")


@dataclass(frozen=True)
class SnowScenario:
    grid: Grid
    scenario_id: str
    simulated_at: str
    model: str
    depth_m: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.model:
            raise ValueError("scenario_id and model are required")
        timestamp = datetime.fromisoformat(self.simulated_at.replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError("simulated_at must include a timezone")
        if len(self.depth_m) != self.grid.size:
            raise ValueError("scenario array must match grid dimensions")
        if any(not isfinite(value) or value < 0 for value in self.depth_m):
            raise ValueError("scenario snow depths must be finite and nonnegative")
