"""Pydantic request/response models for both endpoints.

Field names and nesting mirror ``master-splinter-web/src/glue.py``'s JSON
contract on purpose, so the website's existing parsing code needs minimal
changes to switch from the in-browser Pyodide call to this HTTP call.

"""

from pydantic import BaseModel, Field

from master_splinter.configs.environment import SURFACE_PRESSURE
from master_splinter.configs.limits import (
    MAX_ASCENT_RATE,
    PPO2_WORKING_LIMIT,
)

DEFAULT_SEED = 1


class SegmentIn(BaseModel):
    """One leg of a planned dive, as the boundaries form submits it."""

    depth: float
    duration: float
    phase: str
    variation: float = 0.0


class ProfileAnalysisRequest(BaseModel):
    boundaries: list[SegmentIn]
    gas: str = "air"
    gradient_factors: str = "30/85"
    ppo2_limit: float = PPO2_WORKING_LIMIT
    ascent_rate: float = MAX_ASCENT_RATE
    surface_pressure: float = SURFACE_PRESSURE
    seed: int = DEFAULT_SEED


class SummaryOut(BaseModel):
    planned_runtime: float
    actual_runtime: float
    max_depth: float
    total_deco_time: float
    stop_count: int
    finding_count: int


class StopOut(BaseModel):
    depth: float
    duration: float
    started_at: float


class FindingOut(BaseModel):
    kind: str
    label: str
    time: float
    depth: float
    detail: str


class SampleOut(BaseModel):
    t: float
    planned: float
    actual: float
    ambient: float
    tolerated: float
    tissues: list[float]


class ProfileAnalysisResponse(BaseModel):
    seed: int
    summary: SummaryOut
    stops: list[StopOut]
    findings: list[FindingOut]
    track: list[SampleOut]
    final_tissues: list[float]


class AltitudeAnalysisRequest(BaseModel):
    tissues: list[float] = Field(min_length=16, max_length=16)
    elevation_gain: float
    surface_interval: float = 0.0
    gf_high: float = 0.85
    surface_pressure: float = SURFACE_PRESSURE


class VerdictOut(BaseModel):
    label: str
    gf: float
    safe: bool
    tolerated_pressure: float
    limiting_compartment: int
    limiting_half_time: float
    margin: float
    wait_minutes: float | None
    max_gain: float


class AltitudeAnalysisResponse(BaseModel):
    elevation_gain: float
    surface_interval: float
    start_elevation: float
    start_pressure: float
    target_pressure: float
    safe: bool
    raw: VerdictOut
    gradient: VerdictOut
