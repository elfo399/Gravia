import asyncio
import math
import random
import time
from collections.abc import AsyncIterator

from app.balance_board.board import BoardSample, BoardStatusPublisher
from app.models.api_model import utc_now
from app.models.board_status import BoardStatus


class DemoBoard:
    def __init__(self):
        self.status = BoardStatus(mode="demo", connected=True)

    async def start(self, publish_status: BoardStatusPublisher):
        await publish_status(self.get_status())

    def get_status(self) -> BoardStatus:
        return self.status.model_copy()

    async def shutdown(self):
        pass

    async def samples(self) -> AsyncIterator[BoardSample]:
        started = time.monotonic()
        target_weight = random.uniform(72.1, 72.7)
        while True:
            elapsed = time.monotonic() - started
            if elapsed < 1.5:
                weight = 0.0
            elif elapsed < 3:
                weight = target_weight * min(1, (elapsed - 1.5) / 1.2)
            else:
                oscillation = 1.8 * math.exp(-(elapsed - 3) * 1.2)
                weight = target_weight + math.sin(elapsed * 9) * oscillation
                weight += random.uniform(-0.003, 0.003)
            sway = 0.02 * math.sin(elapsed * 1.4)
            self.status.last_sample_at = utc_now()
            yield BoardSample(
                elapsed,
                weight * (0.26 + sway),
                weight * 0.24,
                weight * 0.25,
                weight * (0.25 - sway),
            )
            await asyncio.sleep(0.1)
