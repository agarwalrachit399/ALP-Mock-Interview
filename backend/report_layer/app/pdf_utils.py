from fpdf import FPDF


def create_pdf_from_analysis(report_data: list, filename: str = "report.pdf") -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for item in report_data:
        principle = item.get("principle", "Unknown Principle")
        analysis = item.get("analysis", "")

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Principle: {principle}", ln=True)
        pdf.ln(1)

        pdf.set_font("Arial", size=12)
        lines = analysis.split("\n")
        for line in lines:
            if line.strip().startswith("- "):
                pdf.set_font("Arial", "B", 12)
                pdf.multi_cell(0, 8, line.strip())
                pdf.set_font("Arial", size=12)
            else:
                pdf.multi_cell(0, 8, line.strip())

        pdf.ln(5)

    pdf.output(filename)
    return filename
