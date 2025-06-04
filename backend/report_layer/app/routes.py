from fastapi import APIRouter
from app.models import ReportRequest, ReportResponse
from app.report_service import generate_report

router = APIRouter()

@router.post("/generate-report", response_model=ReportResponse)
def generate_report_endpoint(request: ReportRequest):
    return generate_report(request)
