import requests
import logging
import sys, os
import json
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.constants import REPORT_ENDPOINT, REPORT_PDF_ENDPOINT  

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
            
            headers = {"Content-Type": "application/json"}

            response = requests.post(REPORT_PDF_ENDPOINT, json=payload)
        
            response.raise_for_status()

            pdf_path = f"{session_id}_report.pdf"
            with open(pdf_path, "wb") as f:
                f.write(response.content)

            return {"status": "success", "file_path": pdf_path}
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching report PDF: {e}")
            if e.response is not None:
                logging.error(f"Server response text: {e.response.text}")
            return {"error": str(e)}

rep=ReportService()
rep.get_report_pdf("1ea49c9e-c0df-46b8-b95e-66c67a25431d")
