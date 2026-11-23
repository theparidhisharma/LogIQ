from pydantic import BaseModel, Field
from fastapi import Depends
from typing import Literal
from shared.common import *
from shared.security import current_user
from .engine import benchmark, available_parsers

app = make_app('parser')

class BenchmarkRequest(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=100000)
    seed: int = 42
    sample_size: int = Field(default=10000, ge=1, le=10000)
    sampling_strategy: Literal['first_n', 'random', 'stratified'] = 'random'
    selection_policy: Literal['runtime_first', 'quality_constrained', 'multi_objective'] = 'runtime_first'
    min_quality: float = Field(default=0.90, ge=0, le=1)
    ground_truth_templates: list[str] | None = None

@app.get('/v1/parsers')
def parsers():
    return {'eligible': [p.name for p in available_parsers()], 'note': 'Only installed and initialized adapters are listed. PIPLUP is not registered unless its real API and license are verified.'}

@app.post('/v1/benchmarks')
def run_benchmark(request: BenchmarkRequest, user: dict = Depends(current_user)):
    try:
        return benchmark(request.lines, request.seed, request.sample_size,
                         request.sampling_strategy, request.selection_policy,
                         request.min_quality, request.ground_truth_templates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

