"""Public-observation signal extraction for Stage I."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from gymnasium.spaces import Dict as DictSpace
from gymnasium.spaces.utils import unflatten


DEFAULT_LIDAR_RANGE = 3.0
HAZARDS_LIDAR_KEY = "hazards_lidar"


def distance_from_hazards_lidar(
    hazards_lidar: Any,
    lidar_range: float = DEFAULT_LIDAR_RANGE,
) -> float:
    """Return capped nearest hazard-center distance from pseudo-lidar closeness.

    The input must be the public ``hazards_lidar`` vector, not privileged
    simulator geometry. Safety-Gymnasium's pseudo-lidar encodes closeness as
    ``1 - distance / lidar_range`` and clips objects outside the range to zero.
    """

    values = np.asarray(hazards_lidar, dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("hazards_lidar must be a non-empty one-dimensional vector")
    if not np.all(np.isfinite(values)):
        raise ValueError("hazards_lidar must contain only finite values")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("hazards_lidar values must lie in [0, 1]")
    if not np.isfinite(lidar_range) or lidar_range <= 0.0:
        raise ValueError("lidar_range must be a finite positive number")
    return float(lidar_range * (1.0 - float(np.max(values))))


def hazards_lidar_from_observation(
    observation: Any,
    observation_space_dict: DictSpace | None = None,
) -> np.ndarray:
    """Extract ``hazards_lidar`` from a public dict or flattened observation."""

    if isinstance(observation, Mapping):
        if HAZARDS_LIDAR_KEY not in observation:
            raise KeyError(f"observation has no {HAZARDS_LIDAR_KEY!r} field")
        return np.asarray(observation[HAZARDS_LIDAR_KEY], dtype=np.float64)

    if observation_space_dict is None:
        raise ValueError("observation_space_dict is required for a flattened observation")
    structured = unflatten(observation_space_dict, np.asarray(observation))
    return np.asarray(structured[HAZARDS_LIDAR_KEY], dtype=np.float64)


def distance_from_observation(
    observation: Any,
    observation_space_dict: DictSpace | None = None,
    lidar_range: float = DEFAULT_LIDAR_RANGE,
) -> float:
    """Extract the normative Stage I distance from a public observation."""

    lidar = hazards_lidar_from_observation(observation, observation_space_dict)
    return distance_from_hazards_lidar(lidar, lidar_range)


def simulator_nearest_hazard_center_distance(task: Any) -> float:
    """Return privileged center distance for collection-time validation only."""

    agent_xy = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    hazard_xy = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
    return float(np.min(np.linalg.norm(hazard_xy - agent_xy, axis=1)))

