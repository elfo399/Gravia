import json

import pytest

from scripts import test_real_board as diagnostic


def test_diagnostic_prints_real_samples_and_disconnects(monkeypatch, capsys):
    from test_real_board import FakeClient

    client = FakeClient()
    monkeypatch.setenv("GRAVIA_BOARD_MAC", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setattr(diagnostic, "WiibalanceClient", lambda _: client)
    monkeypatch.setattr(diagnostic.time, "sleep", lambda _: None)
    monkeypatch.setattr(diagnostic.sys, "argv", ["test_real_board.py", "--samples", "2"])
    assert diagnostic.main() == 0
    output = capsys.readouterr().out.splitlines()
    samples = [json.loads(line) for line in output if line.startswith("{")]
    assert len(samples) == 2 and samples[0]["weight"] == 70
    assert samples[0]["sensors"]["frontRight"] == 20
    assert output[-1] == "Balance Board disconnected"
    assert client.closed


@pytest.mark.parametrize("failure", [False, True])
def test_diagnostic_cleans_up_on_read_error_and_interrupt(monkeypatch, failure):
    from test_real_board import FakeClient

    class FailingClient(FakeClient):
        def read_state(self):
            if failure:
                raise OSError("read failure")
            raise KeyboardInterrupt

    client = FailingClient()
    monkeypatch.setenv("GRAVIA_BOARD_MAC", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setattr(diagnostic, "WiibalanceClient", lambda _: client)
    monkeypatch.setattr(diagnostic.sys, "argv", ["test_real_board.py"])
    assert diagnostic.main() == (1 if failure else 130)
    assert client.closed
