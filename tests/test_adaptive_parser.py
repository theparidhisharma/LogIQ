import pytest
from services.parser.engine import benchmark, _sample_indices

LINES = [
    'INFO request 10 completed', 'ERROR request 11 failed',
    'WARN request 12 delayed', 'INFO request 13 completed',
    'ERROR request 14 failed', 'DEBUG cache hit 15',
]


def test_sampling_is_reproducible():
    assert _sample_indices(LINES, 4, 'random', 7) == _sample_indices(LINES, 4, 'random', 7)
    assert _sample_indices(LINES, 3, 'first_n', 1) == [0, 1, 2]
    assert len(_sample_indices(LINES, 4, 'stratified', 7)) == 4


def test_runtime_benchmark_returns_measurements():
    result = benchmark(LINES, seed=7, sample_size=4, sampling_strategy='random')
    assert result['sample_size'] == 4
    assert result['selected_parser']
    assert result['results'][0]['throughput_lps'] > 0


def test_quality_policy_requires_ground_truth():
    with pytest.raises(ValueError, match='ground_truth_templates'):
        benchmark(LINES, selection_policy='quality_constrained')


def test_quality_policy_uses_aligned_ground_truth():
    expected = ['INFO request <*> completed', 'ERROR request <*> failed', 'WARN request <*> delayed',
                'INFO request <*> completed', 'ERROR request <*> failed', 'DEBUG cache hit <*>']
    result = benchmark(LINES, sample_size=6, sampling_strategy='first_n',
                       selection_policy='quality_constrained', min_quality=0,
                       ground_truth_templates=expected)
    assert result['results'][0]['exact_template_accuracy'] is not None


def test_parser_factory_resolves_only_registered_names():
    from services.parser.engine import parser_by_name, BaselineParser
    assert isinstance(parser_by_name(BaselineParser.name), BaselineParser)
    with pytest.raises(ValueError, match="not installed or registered"):
        parser_by_name("not-a-real-parser")


def test_ground_truth_must_align_with_entire_dataset():
    with pytest.raises(ValueError, match="align with all input lines"):
        benchmark(LINES, sample_size=2, ground_truth_templates=["only-one"])
