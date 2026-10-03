"""Similarity metrics for snow-depth snapshots; no release probability is inferred."""

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Sequence

from .models import SnowObservation, SnowScenario


@dataclass(frozen=True)
class Match:
    scenario_id: str
    model: str
    rmse_m: float
    normalized_rmse: float
    valid_cells: int

    def to_dict(self) -> dict:
        return asdict(self)


def rank_scenarios(
    observation: SnowObservation, scenarios: Sequence[SnowScenario]
) -> list[Match]:
    """Compare a snapshot with simulated snapshots on the same projected grid.

    normalized_rmse uses observation uncertainties as weights. It is a residual
    metric, not a calibrated likelihood or a probability of an avalanche.
    """
    if not scenarios:
        raise ValueError("at least one scenario is required")
    results: list[Match] = []
    for scenario in scenarios:
        if scenario.grid != observation.grid:
            raise ValueError(f"grid mismatch for scenario {scenario.scenario_id}")
        if scenario.simulated_at != observation.captured_at:
            raise ValueError(f"time mismatch for scenario {scenario.scenario_id}")
        residuals = [
            (observed - predicted, uncertainty)
            for observed, uncertainty, predicted in zip(
                observation.depth_m, observation.uncertainty_m, scenario.depth_m
            )
            if observed is not None and uncertainty is not None
        ]
        count = len(residuals)
        results.append(
            Match(
                scenario_id=scenario.scenario_id,
                model=scenario.model,
                rmse_m=sqrt(sum(error * error for error, _ in residuals) / count),
                normalized_rmse=sqrt(
                    sum((error / uncertainty) ** 2 for error, uncertainty in residuals)
                    / count
                ),
                valid_cells=count,
            )
        )
    return sorted(results, key=lambda item: (item.normalized_rmse, item.rmse_m))
