# from .pdf_utils import generate_lp_report_pdf
# from services.report_service import get_report_for_session 
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

