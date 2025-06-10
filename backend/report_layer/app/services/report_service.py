import requests
import logging
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.constants import REPORT_ENDPOINT, REPORT_PDF_ENDPOINT  

class ReportService:
    def get_report(self, session_id):
        try:
            payload = {"session_id": session_id}
            response = requests.post(REPORT_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching report: {e}")
            return {"error": str(e)}

    def get_report_pdf(self, session_id):
        try:
            payload = {"session_id": session_id}
            response = requests.post(REPORT_PDF_ENDPOINT, json=payload)
            response.raise_for_status()
            # Save the PDF locally
            pdf_path = f"{session_id}_report.pdf"
            with open(pdf_path, "wb") as f:
                f.write(response.content)
            return {"status": "success", "file_path": pdf_path}
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching report PDF: {e}")
            return {"error": str(e)}
