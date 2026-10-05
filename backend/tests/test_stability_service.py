import pytest

from app.services.stability_service import StabilityService


def detector():
    return StabilityService(20, 95, 2.5)


def test_unstable_weight_does_not_complete():
    service = detector()
    for index in range(100):
        result = service.calculate_weight_stability(index / 10, 72 + (index % 2))
        assert not result.stable
    assert result.score < 95


def test_stable_weight_requires_window_and_continuous_duration():
    service = detector()
    for index in range(35):
        result = service.calculate_weight_stability(index / 10, 72.4)
        assert not result.stable
    result = service.calculate_weight_stability(3.5, 72.4)
    assert result.stable
    assert result.score == 100
    assert result.average_weight == pytest.approx(72.4)


def test_two_equal_samples_are_insufficient():
    service = detector()
    service.calculate_weight_stability(0, 72.4)
    result = service.calculate_weight_stability(3, 72.4)
    assert result.score == 0
    assert not result.stable


def test_below_minimum_weight_resets_stable_hold():
    service = detector()
    for index in range(30):
        service.calculate_weight_stability(index / 10, 72.4)
    result = service.calculate_weight_stability(3, 10)
    assert result.score == 0
    for index in range(31, 60):
        assert not service.calculate_weight_stability(index / 10, 72.4).stable


def test_score_measures_range_of_window():
    service = detector()
    for index in range(11):
        result = service.calculate_weight_stability(index / 10, 72.4 + (index % 2) * 0.02)
    assert result.score == pytest.approx(99.8)


def test_instability_breaks_continuous_duration():
    service = detector()
    for index in range(30):
        service.calculate_weight_stability(index / 10, 72.4)
    service.calculate_weight_stability(3, 73.4)
    for index in range(31, 65):
        assert not service.calculate_weight_stability(index / 10, 72.4).stable


def test_board_noise_completes_after_continuous_stable_hold():
    service = detector()
    for index in range(35):
        result = service.calculate_weight_stability(index / 10, 72.4 + (index % 2) * 0.5)
        assert not result.stable
    result = service.calculate_weight_stability(3.5, 72.9)
    assert result.stable
    assert result.score >= 95
    assert 72.4 < result.average_weight < 72.9


def test_sustained_weight_drift_does_not_complete():
    service = detector()
    for index in range(100):
        result = service.calculate_weight_stability(index / 10, 72.4 + index / 10)
        assert not result.stable


def test_custom_tolerances_still_reject_noise():
    service = StabilityService(20, 95, 2.5, range_kg=0.05, stddev_kg=0.02)
    for index in range(60):
        result = service.calculate_weight_stability(index / 10, 72.4 + (index % 2) * 0.5)
        assert not result.stable


def test_rounded_score_cannot_accept_outside_tolerance():
    service = detector()
    for index in range(60):
        # The range exceeds 0.8 kg although its displayed score rounds to 95.
        result = service.calculate_weight_stability(index / 10, 72.4 + (index % 10 == 0) * 0.801)
        assert not result.stable
    assert result.score == 95
