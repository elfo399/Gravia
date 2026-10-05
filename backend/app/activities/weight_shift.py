import random
from math import hypot

from app.balance_board.board import BoardSample

TARGET_COUNT = 10
TARGET_RADIUS = 0.18
TARGET_HOLD_SECONDS = 0.4
TARGET_TIMEOUT = 4.0
TARGET_BASE_SCORE = 100
MAX_SPEED_BONUS = 50
TARGETS = {"LEFT": (-0.45, 0), "RIGHT": (0.45, 0), "FRONT": (0, 0.45), "REAR": (0, -0.45)}


class WeightShift:
    def __init__(self, seed: str):
        rng = random.Random(seed)
        self.directions = []
        for _ in range(TARGET_COUNT):
            choices = [key for key in TARGETS if not self.directions or key != self.directions[-1]]
            self.directions.append(rng.choice(choices))
        self.index = 0
        self.target_started = 0.0
        self.in_target_since = None
        self.reactions = []
        self.score = 0
        self.last_outcome = None
        self.outcome_at = 0.0

    @property
    def completed(self):
        return self.index == TARGET_COUNT

    def interrupt_hold(self):
        self.in_target_since = None

    def process_sample(self, sample: BoardSample, elapsed: float, dt: float):
        if not self.completed:
            x, y = TARGETS[self.directions[self.index]]
            if hypot(sample.center_x - x, sample.center_y - y) <= TARGET_RADIUS:
                if self.in_target_since is None:
                    self.in_target_since = elapsed
            else:
                self.in_target_since = None
            reaction = elapsed - self.target_started
            reached = (
                self.in_target_since is not None
                and elapsed - self.in_target_since >= TARGET_HOLD_SECONDS - 1e-9
                and reaction <= TARGET_TIMEOUT + 1e-9
            )
            if reached or reaction >= TARGET_TIMEOUT - 1e-9:
                if reached:
                    self.reactions.append(reaction)
                    self.score += round(
                        TARGET_BASE_SCORE
                        + max(0, MAX_SPEED_BONUS * (1 - reaction / TARGET_TIMEOUT))
                    )
                self.last_outcome = "REACHED" if reached else "MISSED"
                self.outcome_at = elapsed
                self.index += 1
                self.target_started = elapsed
                self.in_target_since = None
        direction = self.directions[self.index] if not self.completed else None
        return {
            "direction": direction,
            "target": dict(zip(("x", "y"), TARGETS[direction], strict=True)) if direction else None,
            "targetIndex": min(self.index + 1, TARGET_COUNT),
            "totalTargets": TARGET_COUNT,
            "targetsReached": len(self.reactions),
            "targetRadius": TARGET_RADIUS,
            "lastOutcome": self.last_outcome if elapsed - self.outcome_at <= 0.8 else None,
        }

    def get_result(self):
        return {
            "targets": TARGET_COUNT,
            "targetsReached": len(self.reactions),
            "targetsMissed": self.index - len(self.reactions),
            "averageReactionTime": sum(self.reactions) / len(self.reactions)
            if self.reactions
            else None,
            "bestReactionTime": min(self.reactions) if self.reactions else None,
        }
