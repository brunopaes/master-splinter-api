"""POST /altitude-analysis."""

from fastapi import APIRouter

from api.processors import altitude_analysis
from api.utils.schemas import AltitudeAnalysisRequest, AltitudeAnalysisResponse

router = APIRouter()


@router.post("/altitude-analysis", response_model=AltitudeAnalysisResponse)
def analyse_altitude(
    request: AltitudeAnalysisRequest,
) -> AltitudeAnalysisResponse:
    return altitude_analysis.run(request)
