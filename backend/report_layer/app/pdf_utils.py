from fpdf import FPDF
from fpdf.enums import XPos, YPos

def create_pdf_from_analysis(report_data: list, filename: str = "report.pdf") -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)

    for item in report_data:
        principle = item.get("principle", "Unknown Principle")
        analysis = item.get("analysis", "")

        # Title for each principle
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 10, f"Principle: {principle}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        # Reset font for body text
        pdf.set_font("Helvetica", size=12)
        lines = analysis.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(1)
                continue
            if line.startswith("- "):  # Section header
                pdf.set_font("Helvetica", "B", 12)
                pdf.multi_cell(0, 8, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", size=12)
            else:  # Regular text
                # Safely wrap text to avoid layout error
                pdf.multi_cell(0, 8, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(4)  # Extra spacing between principles

    pdf.output(filename)
    return filename
