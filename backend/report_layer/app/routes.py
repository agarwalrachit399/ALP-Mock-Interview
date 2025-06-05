from fastapi import APIRouter, HTTPException
from .services import analyze_lp
from .llm_clients.gemini_client import gemini_llm

router = APIRouter()

@router.get("/get_report")
def get_report(lp_key: str = "lp1"):
    try:
        report = analyze_lp(lp_key=lp_key, llm_client=gemini_llm, data_file="data.json")
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
