from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from app.models.board_status import BoardStatus

BoardStatusPublisher = Callable[[BoardStatus], Awaitable[None]]


class BoardUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class BoardSample:
    elapsed_seconds: float
    front_left: float
    front_right: float
    rear_left: float
    rear_right: float

    @property
    def weight(self) -> float:
        return self.front_left + self.front_right + self.rear_left + self.rear_right

    @property
    def center_x(self) -> float:
        if self.weight <= 0:
            return 0
        return (self.front_right + self.rear_right - self.front_left - self.rear_left) / self.weight

    @property
    def center_y(self) -> float:
        if self.weight <= 0:
            return 0
        return (self.front_left + self.front_right - self.rear_left - self.rear_right) / self.weight


class BalanceBoard(Protocol):
    async def start(self, publish_status: BoardStatusPublisher) -> None: ...

    def get_status(self) -> BoardStatus: ...

    async def shutdown(self) -> None: ...

    def samples(self) -> AsyncIterator[BoardSample]:
        """Yield calibrated kg readings; elapsed time is monotonic within a session."""
        ...
