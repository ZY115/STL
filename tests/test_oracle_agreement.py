"""Online/direct-oracle/RTAMT agreement tests on synthetic and environment traces."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml

from safety_stl.monitor import BoundedRecoveryMonitor, MonitorOutput
from safety_stl.oracle import OracleResult, evaluate_trace, rtamt_window_robustness


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "stage1_rule.yaml"
FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixtures"


def load_config() -> Dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def run_online(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    config: Dict[str, Any],
) -> List[MonitorOutput]:
    monitor = BoundedRecoveryMonitor(
        config["d_warn"],
        config["d_safe"],
        config["deadline_steps"],
    )
    outputs = [monitor.reset(distances[0])]
    for index in range(1, len(distances)):
        outputs.append(
            monitor.step(
                distances[index],
                terminated=terminated[index],
                truncated=truncated[index],
            ),
        )
    return outputs


def event_steps(outputs: Sequence[MonitorOutput], attribute: str) -> List[int]:
    return [output.sample_index for output in outputs if getattr(output, attribute)]


class OracleAgreementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()

    def assert_online_oracle_agree(
        self,
        distances: Sequence[float],
        terminated: Sequence[bool],
        truncated: Sequence[bool],
    ) -> OracleResult:
        outputs = run_online(distances, terminated, truncated, self.config)
        oracle = evaluate_trace(
            distances,
            self.config["d_warn"],
            self.config["d_safe"],
            self.config["deadline_steps"],
            terminated=terminated,
            truncated=truncated,
        )
        self.assertEqual(event_steps(outputs, "stl_warning_trigger"), oracle.trigger_steps)
        self.assertEqual(event_steps(outputs, "stl_recovery"), oracle.recovery_steps)
        self.assertEqual(event_steps(outputs, "stl_late_recovery"), oracle.late_recovery_steps)
        self.assertEqual(event_steps(outputs, "stl_deadline_violation"), oracle.violation_steps)
        self.assertEqual(event_steps(outputs, "stl_terminal_unresolved"), oracle.unresolved_steps)
        self.assertEqual([output.stl_cost for output in outputs], oracle.costs)
        for window in oracle.completed_windows:
            values = distances[window.trigger_step : window.deadline_step + 1]
            rtamt_robustness = rtamt_window_robustness(
                values,
                self.config["d_safe"],
                self.config["deadline_steps"],
            )
            self.assertEqual(rtamt_robustness >= 0.0, window.satisfied)
            self.assertLessEqual(
                abs(rtamt_robustness - window.robustness),
                self.config["agreement_tolerance"],
            )
        return oracle

    def test_synthetic_cases(self) -> None:
        warn = self.config["d_warn"]
        safe = self.config["d_safe"]
        deadline = self.config["deadline_steps"]
        cases = {
            "vacuous": [warn] * (deadline + 2),
            "deadline_recovery": [warn - 0.01] + [safe - 0.01] * (deadline - 1) + [safe],
            "deadline_violation": [warn - 0.01] + [safe - 0.01] * deadline,
            "two_episodes": [warn - 0.01, safe] + [safe] * deadline + [warn - 0.01] + [safe] * (deadline + 1),
        }
        for name, distances in cases.items():
            with self.subTest(name=name):
                flags = [False] * len(distances)
                self.assert_online_oracle_agree(distances, flags, flags)

    def test_truncated_synthetic_case(self) -> None:
        distances = [self.config["d_warn"] - 0.01, self.config["d_safe"] - 0.01]
        terminated = [False, False]
        truncated = [False, True]
        oracle = self.assert_online_oracle_agree(distances, terminated, truncated)
        self.assertEqual(oracle.unresolved_steps, [1])
        self.assertEqual(oracle.completed_windows, [])

    def test_stable_environment_fixtures(self) -> None:
        with (FIXTURE_DIRECTORY / "manifest.json").open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        for fixture in manifest["fixtures"]:
            with self.subTest(fixture=fixture["label"]):
                path = FIXTURE_DIRECTORY / fixture["file"]
                with path.open("r", newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                distances = [float(row["nearest_hazard_distance_public"]) for row in rows]
                terminated = [row["terminated"].lower() == "true" for row in rows]
                truncated = [row["truncated"].lower() == "true" for row in rows]
                oracle = self.assert_online_oracle_agree(distances, terminated, truncated)
                if fixture["label"] == "on_time":
                    self.assertEqual(len(oracle.recovery_steps), 1)
                    self.assertEqual(oracle.violation_steps, [])
                elif fixture["label"] == "violation":
                    self.assertEqual(len(oracle.violation_steps), 1)
                    if "late_recovery" in fixture["expected_outcome"]:
                        self.assertEqual(len(oracle.late_recovery_steps), 1)
                elif fixture["label"] == "unresolved":
                    self.assertEqual(len(oracle.unresolved_steps), 1)
                    self.assertEqual(oracle.completed_windows, [])


if __name__ == "__main__":
    unittest.main()
