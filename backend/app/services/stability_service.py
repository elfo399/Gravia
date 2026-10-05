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

    def __init__(self, minimum_weight: float, required_stability: float, stable_duration: float):
        self.minimum_weight = minimum_weight
        self.required_stability = required_stability
        self.stable_duration = stable_duration
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
        score = round(max(0.0, 100 - max(spread * 100, deviation * 250)), 1) if sufficient else 0
        if sufficient and score >= self.required_stability:
            if self.stable_since is None:
                self.stable_since = elapsed
        else:
            self.stable_since = None
        stable = (
            self.stable_since is not None and elapsed - self.stable_since >= self.stable_duration
        )
        return StabilityResult(score, stable, mean(weights))
