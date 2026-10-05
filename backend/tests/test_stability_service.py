import pytest

from app.services.stability_service import StabilityService


def detector():
    return StabilityService(20, 95, 2.5)


def test_unstable_weight_does_not_complete():
    service = detector()
    for index in range(100):
        result = service.calculate_weight_stability(index / 10, 72 + (index % 2))
        assert not result.stable
    assert result.score == 0


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
    # Standard deviation is stricter than range for this alternating signal.
    assert result.score == pytest.approx(97.5)


def test_instability_breaks_continuous_duration():
    service = detector()
    for index in range(30):
        service.calculate_weight_stability(index / 10, 72.4)
    service.calculate_weight_stability(3, 73)
    for index in range(31, 65):
        assert not service.calculate_weight_stability(index / 10, 72.4).stable
