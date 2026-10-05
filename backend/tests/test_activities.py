import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.activities.balance_hold import BalanceHold
from app.activities.symmetry import Symmetry
from app.activities.weight_shift import TARGETS, WeightShift
from app.balance_board.board import BoardSample
from app.balance_board.calibrated_board import CalibratedBoard
from app.configuration import Settings
from app.main import create_app
from app.models.activity_session import ActivityCreate, ActivitySession
from app.models.board_calibration import BoardCalibration
from app.models.board_status import BoardStatus
from app.models.measurement import Measurement
from app.services.activity_service import ActivityService
from app.services.board_calibration_service import BoardCalibrationService
from app.services.profile_service import ProfileService
from app.services.session_service import SessionService
from app.websocket.live_measurements import LiveMeasurements


def sample(t, x=0, y=0, weight=80):
    return BoardSample(
        t,
        weight * (1 - x) * (1 + y) / 4,
        weight * (1 + x) * (1 + y) / 4,
        weight * (1 - x) * (1 - y) / 4,
        weight * (1 + x) * (1 - y) / 4,
    )


class Board:
    def __init__(self, samples=None, connected=True):
        self.values = samples
        self.connected = connected
        self.closed = False

    def get_status(self):
        return BoardStatus(mode="real", connected=self.connected, mac_address="00:24:44:6C:0D:A2")

    async def samples(self):
        try:
            if self.values is None:
                await asyncio.sleep(60)
            else:
                for value in self.values:
                    yield value
                    await asyncio.sleep(0)
        finally:
            self.closed = True


class Events(LiveMeasurements):
    def __init__(self):
        super().__init__()
        self.events = []

    async def publish(self, event):
        self.events.append(event)
        await super().publish(event)


def setup(database, board=None, **settings):
    engine, profile, _ = database
    board = board or Board()
    events = Events()
    sessions = SessionService(engine, board, Settings(**settings), events)
    calibration = BoardCalibrationService(engine, board, sessions)
    sessions.calibration = calibration
    service = ActivityService(engine, board, sessions.settings, events, sessions, calibration)
    return service, profile, events


@pytest.mark.parametrize("kind", ["BALANCE_HOLD", "SYMMETRY", "WEIGHT_SHIFT"])
async def test_full_activity_presence_countdown_completion_and_no_measurement(database, kind):
    # Virtual sample time makes the real 30/40-second engines fast, without shortening policy.
    board = Board([sample(i / 10, weight=0 if i < 10 else 80) for i in range(501)])
    service, profile, events = setup(database, board)
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type=kind))
    assert row.status == "WAITING_FOR_USER"
    await service.task
    result = service.get(row.id)
    assert result.status == "COMPLETED"
    assert result.duration_seconds == pytest.approx(40 if kind == "WEIGHT_SHIFT" else 30)
    assert result.score == (0 if kind == "WEIGHT_SHIFT" else 1000)
    assert result.completed_at and result.result_json
    assert "samples" not in result.result_json
    assert board.closed
    statuses = [e for e in events.events if e["type"] == "activity_status"]
    assert [e["status"] for e in statuses] == [
        "WAITING_FOR_USER",
        "COUNTDOWN",
        "COUNTDOWN",
        "COUNTDOWN",
        "ACTIVE",
        "COMPLETED",
    ]
    assert [e["countdown"] for e in statuses[1:5]] == [3, 2, 1, 0]
    with Session(service.engine) as db:
        assert db.exec(select(Measurement)).all() == []
        assert len(db.exec(select(ActivitySession)).all()) == 1
    assert service.list(profile.id, kind)[0].id == row.id
    assert events.latest_activity_completion["activity"]["id"] == row.id


async def test_presence_dropout_resets_countdown(database):
    samples = [sample(i / 10, weight=0 if 15 <= i <= 20 else 80) for i in range(80)]
    service, profile, events = setup(database, Board(samples))
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type="BALANCE_HOLD"))
    await service.task
    status = [e["status"] for e in events.events if e["type"] == "activity_status"]
    assert status[:4] == ["WAITING_FOR_USER", "COUNTDOWN", "WAITING_FOR_USER", "COUNTDOWN"]
    assert service.get(row.id).status == "ERROR"  # Recording ends early, no false completion.


@pytest.mark.parametrize("kind", ["BALANCE_HOLD", "SYMMETRY", "WEIGHT_SHIFT"])
async def test_step_off_never_saves_score_and_releases_board(database, kind):
    service, profile, _ = setup(
        database, Board([sample(i / 10, weight=0 if i >= 70 else 80) for i in range(100)])
    )
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type=kind))
    await service.task
    result = service.get(row.id)
    assert result.status == "ERROR" and "sceso" in result.error_message
    assert result.score is None and result.result_json is None
    assert not service.is_active
    next_row = await service.start(ActivityCreate(profile_id=profile.id, activity_type=kind))
    await service.cancel(next_row.id)


async def test_brief_step_off_is_tolerated(database):
    service, profile, _ = setup(
        database, Board([sample(i / 10, weight=0 if 70 <= i < 73 else 80) for i in range(350)])
    )
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type="SYMMETRY"))
    await service.task
    assert service.get(row.id).score == 1000


@pytest.mark.parametrize("failure", ["cancel", "disconnect", "restart", "timeout"])
async def test_interruptions_leave_audit_without_result(database, failure):
    board = Board()
    service, profile, _ = setup(
        database, board, board_sample_timeout=0.01 if failure == "timeout" else 2
    )
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type="BALANCE_HOLD"))
    await asyncio.sleep(0)
    if failure == "cancel":
        await service.cancel(row.id)
    elif failure == "disconnect":
        board.connected = False
        await service.on_board_status(board.get_status())
    elif failure == "restart":
        await service.shutdown()
        service.recover_interrupted_sessions()
    else:
        await service.task
    result = service.get(row.id)
    assert result.status == ("CANCELLED" if failure == "cancel" else "ERROR")
    assert result.completed_at and result.score is None and result.result_json is None
    assert not service.is_active and board.closed


async def test_all_board_operations_are_mutually_exclusive(database):
    service, profile, _ = setup(database)
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type="BALANCE_HOLD"))
    for call in (
        service.start(ActivityCreate(profile_id=profile.id, activity_type="SYMMETRY")),
        service.sessions.start_measurement_session(profile.id),
        service.calibration.start(),
        service.calibration.reset(),
    ):
        with pytest.raises(HTTPException) as error:
            await call
        assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        ProfileService(service.engine).delete_profile(profile.id)
    assert error.value.status_code == 409
    await service.cancel(row.id)
    measurement = await service.sessions.start_measurement_session(profile.id)
    with pytest.raises(HTTPException) as error:
        await service.start(ActivityCreate(profile_id=profile.id, activity_type="SYMMETRY"))
    assert error.value.status_code == 409
    await service.sessions.cancel_measurement_session(measurement.id)
    calibration = await service.calibration.start()
    with pytest.raises(HTTPException) as error:
        await service.start(ActivityCreate(profile_id=profile.id, activity_type="SYMMETRY"))
    assert error.value.status_code == 409
    await service.calibration.cancel(calibration.id)
    ProfileService(service.engine).delete_profile(profile.id)
    assert service.list() == []


async def test_missing_profile_offline_and_concurrent_start(database):
    service, profile, _ = setup(database, Board(connected=False))
    for identifier, code in (("missing", 404), (profile.id, 503)):
        with pytest.raises(HTTPException) as error:
            await service.start(ActivityCreate(profile_id=identifier, activity_type="BALANCE_HOLD"))
        assert error.value.status_code == code
    assert service.list() == []
    service.board.connected = True
    values = ActivityCreate(profile_id=profile.id, activity_type="BALANCE_HOLD")
    outcomes = await asyncio.gather(
        service.start(values), service.start(values), return_exceptions=True
    )
    assert (
        sum(isinstance(value, HTTPException) and value.status_code == 409 for value in outcomes)
        == 1
    )
    await service.cancel(service.get_active_session().id)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1])
async def test_invalid_sample_time_fails_without_result(database, bad):
    service, profile, _ = setup(database, Board([sample(bad)]))
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type="SYMMETRY"))
    await service.task
    assert service.get(row.id).status == "ERROR"


def test_engines_have_weighted_scores_and_boundary_ranges():
    hold = BalanceHold()
    hold.process_sample(sample(0), 1, 1)
    hold.process_sample(sample(1, 0.75), 3, 2)
    assert hold.score == 333
    assert hold.get_result()["centeredPercent"] == pytest.approx(100 / 3)
    assert hold.get_result()["averageCenterDistance"] == pytest.approx(0.5)
    assert hold.get_result()["maxCenterDistance"] == 0.75
    symmetry = Symmetry()
    symmetry.process_sample(sample(0), 1, 1)
    symmetry.process_sample(sample(1, 0.4), 2, 1)
    assert symmetry.score == 500
    assert symmetry.get_result()["averageLeftPercent"] == pytest.approx(40)
    assert symmetry.get_result()["averageRightPercent"] == pytest.approx(60)
    assert symmetry.get_result()["balancedPercent"] == 50


async def test_training_applies_stored_calibration_once_before_scoring(database):
    hardware = Board([BoardSample(i / 10, 24, 20, 24, 20) for i in range(350)])
    service, profile, events = setup(database, hardware)
    with Session(service.engine) as db:
        db.add(
            BoardCalibration(
                board_mac=hardware.get_status().mac_address,
                front_left_offset=4,
                front_right_offset=0,
                rear_left_offset=4,
                rear_right_offset=0,
                weight_scale=1.1,
                reference_weight=88,
                measured_weight_before=88,
                measured_weight_after=88,
            )
        )
        db.commit()
    service.board = CalibratedBoard(hardware, service.calibration)
    row = await service.start(ActivityCreate(profile_id=profile.id, activity_type="BALANCE_HOLD"))
    await service.task
    assert service.get(row.id).score == 1000
    assert events.latest_activity_reading["weight"] == 88
    assert events.latest_activity_reading["centerOfPressure"] == {"x": 0, "y": 0}
    assert hardware.closed


def test_target_sequence_hold_reset_reaction_bonus_and_timeouts():
    exercise = WeightShift("repeatable")
    assert len(exercise.directions) == 10
    assert all(a != b for a, b in zip(exercise.directions, exercise.directions[1:], strict=False))
    x, y = TARGETS[exercise.directions[0]]
    exercise.process_sample(sample(0, x, y), 0, 0)
    exercise.process_sample(sample(0.3, x, y), 0.3, 0.3)
    assert exercise.index == 0
    exercise.process_sample(sample(0.35), 0.35, 0.05)  # leaving target resets continuous hold
    exercise.process_sample(sample(0.5, x, y), 0.5, 0.15)
    exercise.process_sample(sample(0.9, x, y), 0.9, 0.4)
    assert exercise.index == 1 and exercise.score == 139
    assert exercise.get_result()["bestReactionTime"] == 0.9
    for index in range(1, 10):
        exercise.process_sample(sample(0.9 + index * 4), 0.9 + index * 4, 4)
    assert exercise.completed
    assert exercise.get_result()["targetsReached"] == 1
    assert exercise.get_result()["targetsMissed"] == 9


def test_all_targets_reached_and_hold_interrupted():
    exercise = WeightShift("targets")
    elapsed = 0
    for direction in exercise.directions:
        x, y = TARGETS[direction]
        exercise.process_sample(sample(elapsed, x, y), elapsed, 0)
        exercise.interrupt_hold()
        exercise.process_sample(sample(elapsed + 0.2, x, y), elapsed + 0.2, 0.2)
        exercise.process_sample(sample(elapsed + 0.6, x, y), elapsed + 0.6, 0.4)
        elapsed += 0.6
    assert exercise.completed and 0 < exercise.score <= 1500
    assert exercise.get_result()["targetsReached"] == 10
    assert exercise.get_result()["averageReactionTime"] == pytest.approx(0.6)


def test_api_validation_filters_and_cancel(database):
    _, profile, url = database
    with TestClient(create_app(Settings(database_url=url, demo_seed=False))) as client:
        endpoint = "/api/v1/activities"
        for payload in (
            {"profileId": profile.id, "activityType": "unknown"},
            {"profileId": profile.id, "activityType": "BALANCE_HOLD", "durationSeconds": 60},
        ):
            assert client.post(endpoint, json=payload).status_code == 422
        assert (
            client.post(
                endpoint, json={"profileId": "missing", "activityType": "SYMMETRY"}
            ).status_code
            == 404
        )
        response = client.post(endpoint, json={"profileId": profile.id, "activityType": "SYMMETRY"})
        assert response.status_code == 201
        row = response.json()
        assert client.get(f"{endpoint}/active").json()["id"] == row["id"]
        assert client.get(f"{endpoint}/{row['id']}").json()["profileId"] == profile.id
        assert (
            len(
                client.get(
                    endpoint, params={"profileId": profile.id, "activityType": "SYMMETRY"}
                ).json()
            )
            == 1
        )
        assert client.get(endpoint, params={"activityType": "BALANCE_HOLD"}).json() == []
        assert client.post(f"{endpoint}/{row['id']}/cancel").json()["status"] == "CANCELLED"
        assert client.post(f"{endpoint}/{row['id']}/cancel").status_code == 409
        assert client.get(f"{endpoint}/missing").status_code == 404
