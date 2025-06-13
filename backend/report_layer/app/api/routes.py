
from fastapi.responses import FileResponse
from app.services.report_services import analyze_all_principles_for_session
from app.services.utils.create_pdf import generate_pdf_from_json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.utils.clean_report import clean_full_report
from app.schemas.schema import SessionIDRequest

router = APIRouter()

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
        full_report = analyze_all_principles_for_session(request.session_id)
        
        lp_reports = clean_full_report({"report": full_report} )
        
        pdf_path = generate_pdf_from_json(lp_reports, output_path=f"{request.session_id}_report.pdf")

        return FileResponse(
            path=pdf_path,
            filename=f"{request.session_id}_report.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in get_report_pdf: {e}")
