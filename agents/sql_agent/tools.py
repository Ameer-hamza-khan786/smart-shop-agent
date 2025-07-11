# tools.py
from .shared import _db


def format_sql_results(result):
    if not result:
        return "No matching records found"

    if isinstance(result, list):
        if not result:
            return "No results returned"
        if len(result) == 1:
            return "\n".join(f"{k}: {v}" for k, v in result[0].items())
        return "\n\n".join(
            f"Record {i + 1}:\n" + "\n".join(f"{k}: {v}" for k, v in row.items())
            for i, row in enumerate(result[:5])
        )  # Show max 5 for readability
    return str(result)
