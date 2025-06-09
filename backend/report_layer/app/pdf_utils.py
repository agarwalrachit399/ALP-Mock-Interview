from fpdf import FPDF
import os

def create_pdf_from_analysis(report_data: list, filename: str = "report.pdf") -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Load Unicode font
    font_path = os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    for item in report_data:
        principle = item.get("principle", "Unknown Principle")
        analysis = item.get("analysis", "")

        pdf.set_font("DejaVu", size=12)
        pdf.cell(200, 10, txt=f"Principle: {principle}", ln=True)
        pdf.multi_cell(0, 10, analysis)
        pdf.ln()

    save_path = os.path.join("generated_reports", filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    pdf.output(save_path)
    return save_path
