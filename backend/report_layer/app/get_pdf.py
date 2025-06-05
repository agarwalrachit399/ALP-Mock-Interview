
from fpdf.enums import XPos, YPos

from services import analyze_lp
from llm_clients.gemini_client import gemini_llm
from fpdf import FPDF
report_text = analyze_lp(lp_key="lp1", llm_client=gemini_llm, data_file="data.json")

# Save as PDF locally

def dump_text_to_pdf(report_text: str, filename: str = "report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(w=0, h=8, text=report_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(filename)
    print(f"PDF saved as '{filename}'")
dump_text_to_pdf(report_text, "my_report.pdf")