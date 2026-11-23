"""Parser adapters and reproducible, policy-driven parser benchmarking."""
from __future__ import annotations
import hashlib
import importlib.util
import platform
import random
import time
import tracemalloc
from collections import defaultdict
from typing import Optional

from shared.parsing import template_for


class BaselineParser:
    name = "baseline-token-mask-v1"
    version = "1"

    def parse(self, message: str):
        return template_for(message)


class Drain3Parser:
    name = "drain3"
    version = "installed-package"

    def __init__(self):
        if importlib.util.find_spec("drain3") is None:
            raise RuntimeError("Drain3 is not installed")
        from drain3 import TemplateMiner
        from drain3.template_miner_config import TemplateMinerConfig
        config = TemplateMinerConfig()
        config.drain_sim_th = 0.4
        config.drain_depth = 4
        self.miner = TemplateMiner(config=config)

    def parse(self, message: str):
        result = self.miner.add_log_message(message)
        template = result.get("template_mined", message)
        params = {str(i): value for i, value in enumerate(result.get("parameter_list", []))}
        return hashlib.sha1(template.encode()).hexdigest()[:12], template, params


def parser_factories():
    """Return only adapters that can be imported; every run gets a fresh instance."""
    factories = [BaselineParser]
    if importlib.util.find_spec("drain3") is not None:
        factories.append(Drain3Parser)
    return factories


def available_parsers():
    return [factory() for factory in parser_factories()]


def parser_by_name(name: str):
    """Create a fresh parser instance by its registered, versioned name."""
    for factory in parser_factories():
        parser = factory()
        if parser.name == name:
            return parser
    raise ValueError(f"Parser '{name}' is not installed or registered")


def _sample_indices(lines, size, strategy, seed):
    n = len(lines)
    size = min(size, n)
    if strategy == "first_n":
        return list(range(size))
    rng = random.Random(seed)
    if strategy == "random":
        return sorted(rng.sample(range(n), size))
    if strategy == "stratified":
        # Stratify by parsed severity so rare severity classes are represented.
        from shared.parsing import parse_line
        buckets = defaultdict(list)
        for i, line in enumerate(lines):
            _, severity, _ = parse_line(line)
            buckets[severity].append(i)
        allocation = {key: int(size * len(values) / n) for key, values in buckets.items()}
        remainder = size - sum(allocation.values())
        for key in sorted(buckets, key=lambda k: len(buckets[k]) % (size / n if n else 1), reverse=True)[:remainder]:
            allocation[key] += 1
        chosen = []
        for key, values in buckets.items():
            chosen.extend(rng.sample(values, min(allocation[key], len(values))))
        if len(chosen) < size:
            remaining = sorted(set(range(n)) - set(chosen))
            chosen.extend(rng.sample(remaining, size - len(chosen)))
        return sorted(chosen[:size])
    raise ValueError("sampling_strategy must be first_n, random, or stratified")


def _quality_accuracy(predicted, expected):
    if expected is None:
        return None
    if len(expected) != len(predicted):
        raise ValueError("ground_truth_templates must align with the sampled lines")
    if not expected:
        return 0.0
    return sum(a == b for a, b in zip(predicted, expected)) / len(expected)


def benchmark(lines, seed=42, sample_size=10000, sampling_strategy="random",
              selection_policy="runtime_first", min_quality=0.90,
              ground_truth_templates: Optional[list[str]] = None):
    if not lines:
        raise ValueError("at least one log line is required")
    if selection_policy not in {"runtime_first", "quality_constrained", "multi_objective"}:
        raise ValueError("unsupported selection_policy")
    if ground_truth_templates is not None and len(ground_truth_templates) != len(lines):
        raise ValueError("ground_truth_templates must align with all input lines")
    indices = _sample_indices(lines, sample_size, sampling_strategy, seed)
    sample = [lines[i] for i in indices]
    expected = [ground_truth_templates[i] for i in indices] if ground_truth_templates is not None else None
    results = []

    for factory in parser_factories():
        parser = factory()  # fresh state for each candidate
        tracemalloc.start()
        started = time.perf_counter()
        predicted, template_ids, failures = [], set(), 0
        for line in sample:
            try:
                tid, template, _ = parser.parse(line)
                predicted.append(template)
                template_ids.add(tid)
            except Exception:
                failures += 1
                predicted.append(None)
        elapsed = max(time.perf_counter() - started, 1e-9)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        accuracy = _quality_accuracy(predicted, expected) if expected is not None else None
        results.append({
            "parser": parser.name, "parser_version": getattr(parser, "version", "unknown"),
            "sample_size": len(sample), "execution_seconds": round(elapsed, 6),
            "throughput_lps": round(len(sample) / elapsed, 2),
            "peak_memory_bytes": peak, "template_count": len(template_ids),
            "failures": failures, "exact_template_accuracy": round(accuracy, 6) if accuracy is not None else None,
        })

    eligible = [r for r in results if r["failures"] == 0]
    if selection_policy == "quality_constrained":
        if expected is None:
            raise ValueError("quality_constrained requires ground_truth_templates aligned with lines")
        eligible = [r for r in eligible if r["exact_template_accuracy"] is not None and r["exact_template_accuracy"] >= min_quality]
        selected = min(eligible, key=lambda r: r["execution_seconds"]) if eligible else None
    elif selection_policy == "multi_objective":
        # Transparent equal-weight ranking of normalized runtime and quality.
        if expected is None:
            raise ValueError("multi_objective requires ground_truth_templates aligned with lines")
        if eligible:
            max_time = max(r["execution_seconds"] for r in eligible) or 1
            selected = min(eligible, key=lambda r: 0.5 * (r["execution_seconds"] / max_time) + 0.5 * (1 - r["exact_template_accuracy"]))
        else:
            selected = None
    else:
        selected = min(eligible, key=lambda r: r["execution_seconds"]) if eligible else None

    return {
        "seed": seed, "sample_size": len(sample), "sampling_strategy": sampling_strategy,
        "sample_indices": indices, "selection_policy": selection_policy,
        "minimum_quality": min_quality if selection_policy == "quality_constrained" else None,
        "results": results, "selected_parser": selected["parser"] if selected else None,
        "selection_reason": ("fastest eligible parser under policy" if selected else "no parser met eligibility constraints"),
        "hardware": {"platform": platform.platform(), "python": platform.python_version()},
        "quality_note": "No ground-truth labels are assumed. Exact template accuracy is reported only when caller supplies aligned ground-truth templates. Template count is descriptive, not a quality score.",
    }
