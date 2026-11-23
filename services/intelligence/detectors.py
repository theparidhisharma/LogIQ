"""Deterministic statistical detectors; these are not ML/AI predictions."""
from __future__ import annotations

import math
from statistics import mean


def rolling_mean(values: list[float], window: int = 5) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be positive")
    return [None if i + 1 < window else mean(values[i + 1 - window:i + 1]) for i in range(len(values))]


def z_score_outliers(values: list[float], threshold: float = 3.0) -> list[int]:
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    if len(values) < 2:
        return []
    mu = mean(values)
    variance = sum((x - mu) ** 2 for x in values) / len(values)
    sigma = math.sqrt(variance)
    if sigma == 0:
        return []
    return [i for i, value in enumerate(values) if abs((value - mu) / sigma) >= threshold]


def iqr_outliers(values: list[float], multiplier: float = 1.5) -> list[int]:
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    if len(values) < 4:
        return []
    ordered = sorted(values)

    def percentile(xs, p):
        position = (len(xs) - 1) * p
        lo = int(position)
        hi = min(lo + 1, len(xs) - 1)
        fraction = position - lo
        return xs[lo] * (1 - fraction) + xs[hi] * fraction

    q1, q3 = percentile(ordered, 0.25), percentile(ordered, 0.75)
    spread = q3 - q1
    lo, hi = q1 - multiplier * spread, q3 + multiplier * spread
    return [i for i, value in enumerate(values) if value < lo or value > hi]


def rare_template_ids(counts: dict[str, int], minimum_count: int = 2) -> list[str]:
    if minimum_count < 1:
        raise ValueError("minimum_count must be positive")
    return sorted(template_id for template_id, count in counts.items() if count < minimum_count)


def error_frequency_spikes(values: list[int], window: int = 5, multiplier: float = 2.0) -> list[int]:
    """Flag points exceeding multiplier * prior-window mean; never compares to itself."""
    if window < 1 or multiplier <= 0:
        raise ValueError("window and multiplier must be positive")
    spikes = []
    for i in range(window, len(values)):
        baseline = mean(values[i-window:i])
        if values[i] > 0 and (baseline == 0 or values[i] > multiplier * baseline):
            spikes.append(i)
    return spikes


def error_burst_triggered(recent: int, prior: int) -> bool:
    """Require at least five recent errors and a 3x per-window baseline increase."""
    expected_per_five = max(0, prior) / 11.0
    return recent >= 5 and recent >= max(5, expected_per_five * 3)


def severity_distribution_shift(recent: dict[str, int], baseline: dict[str, int],
                                min_recent: int = 10, threshold: float = 0.35) -> float | None:
    """Return total-variation distance between recent and baseline severity mixes."""
    if threshold <= 0 or threshold > 1 or min_recent < 1:
        raise ValueError("invalid severity-shift configuration")
    recent_total, baseline_total = sum(recent.values()), sum(baseline.values())
    if recent_total < min_recent or baseline_total < min_recent:
        return None
    keys = set(recent) | set(baseline)
    distance = 0.5 * sum(
        abs(recent.get(k, 0) / recent_total - baseline.get(k, 0) / baseline_total)
        for k in keys
    )
    return distance if distance >= threshold else None


def latest_count_outliers(values: list[int], *, z_threshold: float = 2.0,
                          iqr_multiplier: float = 1.5, spike_multiplier: float = 3.0) -> list[str]:
    """Evaluate only the newest bucket against preceding buckets."""
    if len(values) < 6:
        return []
    prior, current = values[:-1], values[-1]
    newest = len(values) - 1
    baseline = sum(prior) / len(prior)
    # Minimum effect size: zero- or low-spread baselines otherwise flag every +-1 change.
    if abs(current - baseline) < max(5, 0.5 * baseline):
        return []
    reasons = []
    if current > 0 and newest in error_frequency_spikes(values, window=min(5, len(prior)),
                                                        multiplier=spike_multiplier):
        reasons.append("rolling_mean")
    if len(prior) >= 3:
        if newest in z_score_outliers(values, threshold=z_threshold):
            reasons.append("z_score")
        if newest in iqr_outliers(values, multiplier=iqr_multiplier):
            reasons.append("iqr")
    return reasons
