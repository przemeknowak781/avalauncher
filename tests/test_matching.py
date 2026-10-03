import json
import tempfile
import unittest
from pathlib import Path

from avalauncher.io import load_observation, load_scenarios
from avalauncher.matching import rank_scenarios


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class MatchingTests(unittest.TestCase):
    def test_synthetic_observation_ranks_nearest_grid_first(self):
        observation = load_observation(EXAMPLES / "synthetic_observation.json")
        scenarios = load_scenarios(EXAMPLES / "synthetic_scenarios.json")
        ranked = rank_scenarios(observation, scenarios)
        self.assertEqual([item.scenario_id for item in ranked], ["close-synthetic", "far-synthetic"])
        self.assertEqual(ranked[0].valid_cells, 5)
        self.assertLess(ranked[0].rmse_m, ranked[1].rmse_m)

    def test_rejects_grid_mismatch_instead_of_false_similarity(self):
        observation = load_observation(EXAMPLES / "synthetic_observation.json")
        scenarios = load_scenarios(EXAMPLES / "synthetic_scenarios.json")
        from avalauncher.models import Grid, SnowScenario

        wrong = SnowScenario(
            Grid("SYNTHETIC", "another-grid", "EPSG:32632", 1.0, 3, 2),
            "wrong-grid", scenarios[0].simulated_at, scenarios[0].model, scenarios[0].depth_m
        )
        with self.assertRaisesRegex(ValueError, "grid mismatch"):
            rank_scenarios(observation, [wrong])

    def test_rejects_nonpositive_uncertainty(self):
        data = json.loads((EXAMPLES / "synthetic_observation.json").read_text())
        data["uncertainty_m"][0] = 0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "uncertainty"):
                load_observation(path)


if __name__ == "__main__":
    unittest.main()
