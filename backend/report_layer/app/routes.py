from fastapi import APIRouter, HTTPException
from .services import analyze_lp
from .llm_clients.gemini_client import gemini_llm
from fpdf import FPDF

router = APIRouter()

@router.get("/get_report")
def get_report(lp_key: str = "lp1"):
    try:
        report_text = analyze_lp(lp_key=lp_key, llm_client=gemini_llm, data_file="data.json")
        return {"report": report_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

report_text = analyze_lp(lp_key="lp1", llm_client=gemini_llm, data_file="data.json")

# Save as PDF locally

def create_beautiful_pdf(report_text: str, filename: str = "report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    lines = report_text.strip().split("\n")

    for line in lines:
        if line.startswith("- "):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt=line[2:], ln=True)
            pdf.ln(2)
            pdf.set_font("Arial", size=12)
        elif line.strip().isdigit():
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, txt=line.strip(), ln=True)
            pdf.ln(2)
            pdf.set_font("Arial", size=12)
        else:
            pdf.multi_cell(0, 8, txt=line)

    pdf.output(filename)
    print(f"PDF saved as '{filename}'")
create_beautiful_pdf(report_text, "my_local_report.pdf")