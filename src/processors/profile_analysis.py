"""Shapes a profile-analysis request into a call against the library.

Boundary validation and phase/gas checks mirror
``master-splinter-web/src/glue.py``'s ``_boundaries``/``analyse`` exactly, so
the three consumers (CLI, web glue, this API) cannot drift on what counts as
a legal request.

"""

from dataclasses import asdict

from master_splinter import validation
from master_splinter.configs.limits import GAS_MIXES

from api.clients import master_splinter_client as client
from api.utils.schemas import (
    FindingOut,
    ProfileAnalysisRequest,
    ProfileAnalysisResponse,
    SampleOut,
    StopOut,
    SummaryOut,
)

PHASES = ("descend", "constant", "ascend")

VIOLATION_LABEL = {
    "ceiling_violation": "Ceiling",
    "ascent_rate_exceeded": "Ascent rate",
    "surfaced_with_obligation": "Surfaced owing",
    "mod_exceeded": "Oxygen (MOD)",
}


def _boundaries(segments):
    """Turns the request's segments into ``generate_dive_profile``'s tuples."""
    if not segments:
        raise ValueError("the profile needs at least one segment")

    out = []
    for index, segment in enumerate(segments, start=1):
        if segment.phase not in PHASES:
            raise ValueError(
                f"segment {index}: phase must be one of "
                f"{', '.join(PHASES)}, got {segment.phase!r}"
            )
        if segment.duration <= 0.0:
            raise ValueError(
                f"segment {index}: duration must be positive, got "
                f"{segment.duration}"
            )
        if segment.variation < 0.0:
            raise ValueError(
                f"segment {index}: variation cannot be negative, got "
                f"{segment.variation}"
            )
        out.append(
            (
                segment.depth,
                segment.duration,
                (-segment.variation, segment.variation),
                segment.phase,
            )
        )
    return out


def run(request: ProfileAnalysisRequest) -> ProfileAnalysisResponse:
    """Runs one profile analysis end to end, returning the API response."""
    boundaries = _boundaries(request.boundaries)

    if request.gas not in GAS_MIXES:
        raise ValueError(
            f"unknown gas {request.gas!r}, expected one of "
            f"{', '.join(sorted(GAS_MIXES))}"
        )

    gf_low, gf_high = validation.gradient_factors(request.gradient_factors)
    ppo2_limit = validation.ppo2_limit(str(request.ppo2_limit))

    report = client.run_profile_analysis(
        boundaries,
        seed=request.seed,
        gas_fraction=GAS_MIXES[request.gas],
        gf_low=gf_low,
        gf_high=gf_high,
        ppo2_limit=ppo2_limit,
        ascent_rate=request.ascent_rate,
        surface_pressure=request.surface_pressure,
    )

    return ProfileAnalysisResponse(
        seed=request.seed,
        summary=SummaryOut(
            planned_runtime=report.planned_runtime,
            actual_runtime=report.actual_runtime,
            max_depth=report.max_depth,
            total_deco_time=report.total_deco_time,
            stop_count=len(report.stops),
            finding_count=len(report.findings),
        ),
        stops=[StopOut(**asdict(stop)) for stop in report.stops],
        findings=[
            FindingOut(
                kind=finding.kind.value,
                label=VIOLATION_LABEL.get(
                    finding.kind.value, finding.kind.value
                ),
                time=finding.time,
                depth=finding.depth,
                detail=finding.detail,
            )
            for finding in report.findings
        ],
        track=[
            SampleOut(
                t=round(sample.time, 4),
                planned=round(sample.planned_depth, 3),
                actual=round(sample.actual_depth, 3),
                ambient=round(
                    client.sample_ambient_pressure(
                        sample.actual_depth, request.surface_pressure
                    ),
                    5,
                ),
                tolerated=round(
                    client.sample_tolerated_pressure(sample.tissues, gf_high),
                    5,
                ),
                tissues=[round(p, 5) for p in sample.tissues],
            )
            for sample in report.samples
        ],
        final_tissues=list(report.final_state.tissues),
    )
