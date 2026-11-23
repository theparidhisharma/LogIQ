from services.intelligence.detectors import (
    rolling_mean, z_score_outliers, iqr_outliers, rare_template_ids, error_frequency_spikes,
)


def test_rolling_mean():
    assert rolling_mean([1, 2, 3, 4], 2) == [None, 1.5, 2.5, 3.5]


def test_z_score_constant_series_has_no_outliers():
    assert z_score_outliers([2, 2, 2, 2]) == []


def test_iqr_detects_extreme_value():
    assert 4 in iqr_outliers([1, 2, 2, 3, 100])


def test_rare_templates():
    assert rare_template_ids({'a': 1, 'b': 8}, 2) == ['a']


def test_error_spike_uses_prior_window():
    assert error_frequency_spikes([1, 1, 1, 10], window=3, multiplier=2) == [3]
