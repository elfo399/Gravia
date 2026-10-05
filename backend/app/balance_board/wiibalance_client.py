"""The verified wiibalance 1.4.1 API and exclusive local ownership of its sockets."""

import os
from pathlib import Path

from wiibalance import create_balance_board, read_config
from wiibalance._direct import DirectBalanceBoard

from app.balance_board.board import BoardUnavailableError


class WiibalanceClient:
    def __init__(self, address: str):
        # Linux-only library. Lazy import keeps demo usable on other platforms.
        import fcntl

        self._lock = None
        self.board = None
        lock_path = Path(os.environ.get("GRAVIA_BOARD_LOCK_PATH", "/data/real-board.lock"))
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = lock_path.open("a")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self._lock.close()
            self._lock = None
            raise BoardUnavailableError(
                "Balance Board già in uso da Gravia o dalla diagnostica."
            ) from error
        try:
            # 1.4.1 can convert the returned weights to pounds using its config file.
            if read_config().get("units", "metric") != "metric":
                raise BoardUnavailableError(
                    "wiibalance richiede units=metric nel file ~/.config/wiibalance/config.json."
                )
            self.board = create_balance_board(address=address, use_daemon=False)
        except BaseException as error:
            # In 1.4.1 initialize()/led_on() may raise before the factory returns,
            # leaving sockets or the worker alive. Recover that exact constructor's
            # instance from its traceback so the same disconnect/join cleanup applies.
            traceback = error.__traceback__
            while traceback is not None:
                if traceback.tb_frame.f_code is DirectBalanceBoard.__init__.__code__:
                    self.board = traceback.tb_frame.f_locals["self"]
                    break
                traceback = traceback.tb_next
            self.close()
            raise

    def read_state(self):
        return self.board.read_state()

    def close(self):
        try:
            if self.board is not None:
                self.board.disconnect()
                # Public disconnect closes the sockets but 1.4.1 does not join its worker.
                worker = getattr(self.board, "worker_thread", None)
                if worker is not None and worker.ident is not None:
                    worker.join(timeout=6)
                    if worker.is_alive():
                        raise RuntimeError(
                            "Il thread wiibalance non si è arrestato dopo disconnect."
                        )
                self.board = None
        finally:
            if self._lock is not None:
                self._lock.close()
                self._lock = None
