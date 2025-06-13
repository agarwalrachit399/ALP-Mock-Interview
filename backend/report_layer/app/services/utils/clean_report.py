def clean_full_report(full_report: dict) -> list[dict]:
    """
    Extracts only the 'Result' dictionaries from the report list.
    """

    return [entry["Result"] for entry in full_report.get("report", []) if "Result" in entry]
