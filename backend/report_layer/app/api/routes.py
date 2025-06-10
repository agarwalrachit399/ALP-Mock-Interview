
from fastapi.responses import FileResponse
from app.services.report_services import analyze_all_principles_for_session
from app.pdf_utils import create_pdf_from_analysis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class SessionIDRequest(BaseModel):
    session_id: str

@router.post("/get_report")
def get_report(request: SessionIDRequest):
    try:
        report_results = analyze_all_principles_for_session(request.session_id)
        return {"session_id": request.session_id, "report": report_results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/get_report_pdf")
def get_report_pdf(request: SessionIDRequest):
    try:
        report = analyze_all_principles_for_session(request.session_id)
        pdf_path = create_pdf_from_analysis(report, filename=f"{request.session_id}_report.pdf")
        return FileResponse(path=pdf_path, filename=pdf_path, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
