from fastapi import APIRouter, Depends, status

try:
    from backend.app.schemas.report import CoachingReportResponse
    from backend.app.services.report_service import ReportService
except ImportError:
    from app.schemas.report import CoachingReportResponse
    from app.services.report_service import ReportService

router = APIRouter(tags=["Coaching Reports"])


def get_report_service() -> ReportService:
    return ReportService()


@router.get(
    "/sessions/{session_id}/coaching-report",
    status_code=status.HTTP_200_OK,
    response_model=CoachingReportResponse,
    summary="Get coaching report for a session",
)
@router.get(
    "/sessions/{session_id}/coaching-report/",
    status_code=status.HTTP_200_OK,
    response_model=CoachingReportResponse,
    include_in_schema=False,
)
def get_coaching_report(
    session_id: str,
    service: ReportService = Depends(get_report_service),
) -> CoachingReportResponse:
    return service.get_coaching_report(session_id)
