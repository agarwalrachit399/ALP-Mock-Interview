from fastapi.responses import FileResponse
from .services import analyze_all_principles_for_session
from .pdf_utils import create_pdf_from_analysis
from .llm_clients.gemini_client import gemini_llm
from fpdf import FPDF
from fastapi import APIRouter, HTTPException, Query
from .services import analyze_all_principles_for_session

router = APIRouter()

@router.get("/get_report")
def get_report(session_id: str = Query(..., description="Session ID to fetch report for")):
    try:
        report_results = analyze_all_principles_for_session(session_id)
        return {"session_id": session_id, "report": report_results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/get_report_pdf")
def get_report_pdf(session_id: str):
    try:
        report = analyze_all_principles_for_session(session_id)
        pdf_path = create_pdf_from_analysis(report, filename=f"{session_id}_report.pdf")
        return FileResponse(path=pdf_path, filename=pdf_path, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))