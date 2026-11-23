import pytest

from services.intelligence.detectors import (
    error_frequency_spikes,
    iqr_outliers,
    latest_count_outliers,
    rare_template_ids,
    rolling_mean,
    severity_distribution_shift,
    z_score_outliers,
)


def test_rolling_mean_returns_none_until_window_is_full():
    assert rolling_mean([1, 2, 3, 4], 3) == [None, None, 2, 3]


def test_z_score_detects_extreme_value():
    assert 5 in z_score_outliers([1, 1, 1, 1, 1, 20], threshold=2)


def test_iqr_detects_extreme_value():
    assert 7 in iqr_outliers([1, 2, 2, 3, 3, 4, 4, 50])


def test_error_frequency_spike_uses_prior_window():
    assert error_frequency_spikes([2, 2, 2, 2, 2, 10], window=5, multiplier=3) == [5]


def test_zero_baseline_can_detect_first_spike():
    assert error_frequency_spikes([0, 0, 0, 0, 0, 5], window=5, multiplier=3) == [5]


def test_latest_count_outlier_returns_detector_evidence():
    reasons = latest_count_outliers([1, 1, 2, 1, 1, 18])
    assert "rolling_mean" in reasons
    assert "z_score" in reasons
    assert "iqr" in reasons


def test_severity_distribution_shift_uses_total_variation():
    distance = severity_distribution_shift(
        {"INFO": 1, "ERROR": 19}, {"INFO": 19, "ERROR": 1},
        min_recent=10, threshold=0.35)
    assert distance == pytest.approx(0.9)


def test_severity_shift_ignores_small_samples():
    assert severity_distribution_shift({"ERROR": 2}, {"INFO": 20}) is None


def test_rare_templates_are_selected_below_frequency_threshold():
    assert rare_template_ids({"a": 1, "b": 2, "c": 3}, 3) == ["a", "b"]


@pytest.mark.parametrize("window", [0, -1])
def test_rolling_mean_rejects_invalid_window(window):
    with pytest.raises(ValueError):
        rolling_mean([1, 2], window)
