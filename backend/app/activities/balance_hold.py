from math import hypot

from app.balance_board.board import BoardSample

CENTER_RADIUS = 0.15
MAX_USEFUL_DISTANCE = 0.75


class BalanceHold:
    def __init__(self):
        self.seconds = self.distance_sum = self.quality_sum = self.centered_seconds = 0.0
        self.max_distance = 0.0

    def process_sample(self, sample: BoardSample, elapsed: float, dt: float):
        distance = hypot(sample.center_x, sample.center_y)
        quality = max(0, min(1, 1 - distance / MAX_USEFUL_DISTANCE))
        self.seconds += dt
        self.distance_sum += distance * dt
        self.quality_sum += quality * dt
        self.centered_seconds += dt if distance <= CENTER_RADIUS else 0
        self.max_distance = max(self.max_distance, distance)
        return {"centerDistance": distance, "centerRadius": CENTER_RADIUS, "quality": quality}

    @property
    def score(self):
        return round(1000 * self.quality_sum / self.seconds) if self.seconds else 0

    def get_result(self):
        return {
            "averageCenterDistance": self.distance_sum / self.seconds if self.seconds else 0,
            "maxCenterDistance": self.max_distance,
            "centeredPercent": 100 * self.centered_seconds / self.seconds if self.seconds else 0,
        }
