"""Shapes an altitude-analysis request into a call against the library."""

from dataclasses import asdict

from api.clients import master_splinter_client as client
from api.utils.schemas import (
    AltitudeAnalysisRequest,
    AltitudeAnalysisResponse,
    VerdictOut,
)


def run(request: AltitudeAnalysisRequest) -> AltitudeAnalysisResponse:
    """Runs one altitude analysis end to end, returning the API response."""
    report = client.run_altitude_analysis(
        request.tissues,
        request.elevation_gain,
        surface_interval=request.surface_interval,
        gf_high=request.gf_high,
        surface_pressure=request.surface_pressure,
    )

    return AltitudeAnalysisResponse(
        elevation_gain=report.elevation_gain,
        surface_interval=report.surface_interval,
        start_elevation=report.start_elevation,
        start_pressure=report.start_pressure,
        target_pressure=report.target_pressure,
        safe=report.safe,
        raw=VerdictOut(**asdict(report.raw)),
        gradient=VerdictOut(**asdict(report.gradient)),
    )
