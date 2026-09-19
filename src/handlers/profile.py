"""POST /profile-analysis."""

import logging

from fastapi import APIRouter

from api.processors import profile_analysis
from api.utils.schemas import ProfileAnalysisRequest, ProfileAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/profile-analysis", response_model=ProfileAnalysisResponse)
def analyse_profile(
    request: ProfileAnalysisRequest,
) -> ProfileAnalysisResponse:
    logger.info(
        "profile analysis requested"
        f" | segment_count={len(request.boundaries)}"
        f" | seed={request.seed}"
    )
    response = profile_analysis.run(request)
    logger.info(
        "profile analysis completed"
        f" | stop_count={response.summary.stop_count}"
        f" | finding_count={response.summary.finding_count}"
    )
    return response
