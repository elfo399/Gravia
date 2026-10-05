from app.balance_board.board import BoardSample

MAX_SYMMETRY_ERROR = 0.20
BALANCED_MIN_RATIO = 0.45
BALANCED_MAX_RATIO = 0.55


class Symmetry:
    def __init__(self):
        self.seconds = self.left_sum = self.quality_sum = self.balanced_seconds = 0.0

    def process_sample(self, sample: BoardSample, elapsed: float, dt: float):
        left = (sample.front_left + sample.rear_left) / sample.weight
        quality = max(0, min(1, 1 - abs(left - 0.5) / MAX_SYMMETRY_ERROR))
        self.seconds += dt
        self.left_sum += left * dt
        self.quality_sum += quality * dt
        self.balanced_seconds += dt if BALANCED_MIN_RATIO <= left <= BALANCED_MAX_RATIO else 0
        return {"leftPercent": 100 * left, "rightPercent": 100 * (1 - left), "quality": quality}

    @property
    def score(self):
        return round(1000 * self.quality_sum / self.seconds) if self.seconds else 0

    def get_result(self):
        left = 100 * self.left_sum / self.seconds if self.seconds else 50
        return {
            "averageLeftPercent": left,
            "averageRightPercent": 100 - left,
            "balancedPercent": 100 * self.balanced_seconds / self.seconds if self.seconds else 0,
        }
