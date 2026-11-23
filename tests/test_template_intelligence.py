from services.intelligence.detectors import error_burst_triggered


def test_error_burst_requires_minimum_volume():
    assert not error_burst_triggered(4, 0)
    assert error_burst_triggered(5, 0)


def test_error_burst_compares_to_previous_55_minute_baseline():
    # 55 prior events imply a five-per-five-minute baseline; a 3x rise is 15.
    assert not error_burst_triggered(14, 55)
    assert error_burst_triggered(15, 55)


def test_error_burst_does_not_flag_normal_baseline():
    assert not error_burst_triggered(10, 110)


def test_error_burst_handles_zero_or_negative_baseline_safely():
    assert error_burst_triggered(5, 0)
    assert error_burst_triggered(5, -10)
