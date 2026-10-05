from collections import deque
from dataclasses import dataclass
from statistics import mean, pstdev


@dataclass(frozen=True)
class StabilityResult:
    score: float
    stable: bool
    average_weight: float


class StabilityService:
    """One second of samples, at least 5 readings, and a continuous stable hold."""

    def __init__(
        self,
        minimum_weight: float,
        required_stability: float,
        stable_duration: float,
        range_kg: float = 0.8,
        stddev_kg: float = 0.3,
    ):
        self.minimum_weight = minimum_weight
        self.required_stability = required_stability
        self.stable_duration = stable_duration
        self.range_kg = range_kg
        self.stddev_kg = stddev_kg
        self.samples: deque[tuple[float, float]] = deque()
        self.stable_since: float | None = None

    def calculate_weight_stability(self, elapsed: float, weight: float) -> StabilityResult:
        if weight < self.minimum_weight:
            self.samples.clear()
            self.stable_since = None
            return StabilityResult(0, False, weight)

        self.samples.append((elapsed, weight))
        # Retain the boundary sample so the window truly covers at least 1 second.
        while len(self.samples) > 1 and self.samples[1][0] <= elapsed - 1.0:
            self.samples.popleft()
        weights = [sample[1] for sample in self.samples]
        sufficient = len(weights) >= 5 and elapsed - self.samples[0][0] >= 1.0 - 1e-9
        deviation = pstdev(weights)
        spread = max(weights) - min(weights)
        # At score 95, tolerate the configured range and standard deviation in kg.
        # The old scaling required <= 50 g range and <= 20 g deviation, preventing
        # ordinary board noise/body sway from ever completing a real measurement.
        raw_score = (
            max(0.0, 100 - 5 * max(spread / self.range_kg, deviation / self.stddev_kg))
            if sufficient
            else 0
        )
        score = round(raw_score, 1)
        if sufficient and raw_score >= self.required_stability:
            if self.stable_since is None:
                self.stable_since = elapsed
        else:
            self.stable_since = None
        stable = (
            self.stable_since is not None and elapsed - self.stable_since >= self.stable_duration
        )
        return StabilityResult(score, stable, mean(weights))
