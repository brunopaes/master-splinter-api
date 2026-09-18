"""POST /profile-analysis."""

from fastapi import APIRouter

from api.processors import profile_analysis
from api.utils.schemas import ProfileAnalysisRequest, ProfileAnalysisResponse

router = APIRouter()


@router.post("/profile-analysis", response_model=ProfileAnalysisResponse)
def analyse_profile(
    request: ProfileAnalysisRequest,
) -> ProfileAnalysisResponse:
    return profile_analysis.run(request)
