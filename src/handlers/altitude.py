"""POST /altitude-analysis."""

import logging

from fastapi import APIRouter

from api.processors import altitude_analysis
from api.utils.schemas import AltitudeAnalysisRequest, AltitudeAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/altitude-analysis", response_model=AltitudeAnalysisResponse)
def analyse_altitude(
    request: AltitudeAnalysisRequest,
) -> AltitudeAnalysisResponse:
    logger.info(
        "altitude analysis requested"
        f" | elevation_gain={request.elevation_gain}"
        f" | surface_interval={request.surface_interval}"
    )
    response = altitude_analysis.run(request)
    logger.info(f"altitude analysis completed | safe={response.safe}")
    return response
