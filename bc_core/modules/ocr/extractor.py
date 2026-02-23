import re
from dateutil import parser

def extract_amount(text):
    matches = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})?", text.replace("₹", ""))
    amounts = [float(m.replace(",", "")) for m in matches]
    return max(amounts) if amounts else None


def extract_gstin(text):
    match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}\b", text)
    return match.group() if match else None


def extract_date(text):
    try:
        return parser.parse(text, fuzzy=True)
    except:
        return None
