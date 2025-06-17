from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


try:
    pdfmetrics.registerFont(TTFont("Arial", "Arial.ttf"))
    base_font = "Arial"
except:
    base_font = "Helvetica"

def generate_pdf_from_json(reports: list[dict], output_path: str):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Header", fontName=base_font, fontSize=18, leading=22, textColor=colors.HexColor("#1A5276"), spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeader", fontName=base_font, fontSize=14, leading=18, textColor=colors.HexColor("#2471A3"), spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", fontName=base_font, fontSize=12, leading=16, textColor=colors.black, spaceAfter=6))
    styles.add(ParagraphStyle(name="Comment", fontName=base_font, fontSize=12, leading=16, textColor=colors.gray, leftIndent=12, spaceAfter=10))

    story = []

    story.append(Paragraph("Interview Report", styles["Header"]))
    story.append(Spacer(1, 12))

    for idx, data in enumerate(reports):
        story.append(Paragraph(f"Leadership Principle {idx + 1}", styles["Header"]))
        story.append(Spacer(1, 10))

        # Show List of LPs demonstrated instead of intended/demonstrated
        story.append(Paragraph("List of LPs Demonstrated", styles["SubHeader"]))
        other_lps = data.get("other_lps_mentioned", [])
        if other_lps:
            story.append(ListFlowable([ListItem(Paragraph(lp, styles["Body"])) for lp in other_lps], bulletType="bullet"))
        else:
            story.append(Paragraph("None provided.", styles["Body"]))
        story.append(Paragraph("STAR Format Analysis", styles["SubHeader"]))
        for key, val in data.get("star_format", {}).items():
            if key != "comment":
                story.append(Paragraph(f"{key.capitalize()}: {'True' if val else 'False'}", styles["Body"]))
        story.append(Paragraph(f"Comment: {data['star_format'].get('comment', '')}", styles["Comment"]))

        story.append(Spacer(1, 10))
        story.append(Paragraph("Answer Quality", styles["SubHeader"]))
        for key, val in data.get("answer_quality", {}).items():
            if key != "comment":
                story.append(Paragraph(f"{key.replace('_', ' ').capitalize()}: {'True' if val else 'False'}", styles["Body"]))
        story.append(Paragraph(f"Comment: {data['answer_quality'].get('comment', '')}", styles["Comment"]))

        # Add Final Score section
        story.append(Spacer(1, 10))
        story.append(Paragraph("Final Score", styles["SubHeader"]))
        story.append(Paragraph(str(data.get("score", "N/A")), styles["Body"]))

        # Add Strengths section
        story.append(Spacer(1, 10))
        story.append(Paragraph("Strengths", styles["SubHeader"]))
        positives = data.get("positives", [])
        if positives:
            story.append(ListFlowable([ListItem(Paragraph(p, styles["Body"])) for p in positives], bulletType="bullet"))
        else:
            story.append(Paragraph("None provided.", styles["Body"]))

        # Add Improvements Needed section
        story.append(Spacer(1, 10))
        story.append(Paragraph("Improvements Needed", styles["SubHeader"]))
        improvements = data.get("improvements_needed", [])
        if improvements:
            story.append(ListFlowable([ListItem(Paragraph(i, styles["Body"])) for i in improvements], bulletType="bullet"))
        else:
            story.append(Paragraph("None provided.", styles["Body"]))
        
        story.append(Spacer(1, 20))  # Space before next LP

    doc.build(story)
    return output_path
