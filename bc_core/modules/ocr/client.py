"""
Gemini Vision OCR client.

Uses google-genai (already in requirements.txt).
Requires GOOGLE_API_KEY env var.  Falls back to mock data in dev when key is absent.

Prompt is tuned for Indian business documents (printed bills, handwritten receipts,
UPI screenshots, GST invoices).
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

_PROMPT = """You are extracting structured data from an Indian business document (bill, receipt, GST invoice, or handwritten note).

Extract the following fields and return ONLY valid JSON. No explanation, no markdown.

{
  "total_amount": <number or null>,
  "document_date": "<YYYY-MM-DD or null>",
  "gstin": "<15-char GST identification number or null>",
  "vendor_name": "<string or null>",
  "document_type": "<one of: invoice, receipt, bill, handwritten, upi_screenshot, unknown>"
}

Rules:
- total_amount: the final payable amount (include tax). Numbers only, no currency symbols.
- document_date: look for date in any format (DD/MM/YYYY, DD-MM-YY, etc) and convert to ISO.
- gstin: must match pattern 2-digit state code + 10-char PAN + 1 digit + Z + 1 char.
- If a field is not visible or not applicable, use null.
- Return only the JSON object, nothing else."""


def _gemini_client():
    """Return a configured Gemini client, or None if API key not set."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as exc:
        logger.warning("Gemini client init failed: %s", exc)
        return None


def extract_structured(image_path: str) -> dict:
    """
    Send image to Gemini Vision and return structured dict.

    Returns:
        {
            "total_amount": float | None,
            "document_date": str | None,   # YYYY-MM-DD
            "gstin": str | None,
            "vendor_name": str | None,
            "document_type": str,
            "raw_text": str,               # full response for debug
            "source": "gemini" | "mock"
        }
    """
    client = _gemini_client()

    if client is None:
        logger.info("GOOGLE_API_KEY not set — returning mock OCR data")
        return {
            "total_amount": None,
            "document_date": None,
            "gstin": None,
            "vendor_name": None,
            "document_type": "unknown",
            "raw_text": "",
            "source": "mock",
        }

    try:
        from google.genai import types

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Detect MIME type from file extension
        ext = image_path.rsplit(".", 1)[-1].lower()
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "pdf": "application/pdf",
                    "webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                _PROMPT,
            ],
        )

        raw_text = response.text.strip() if response.text else ""

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)

        return {
            "total_amount": _safe_float(parsed.get("total_amount")),
            "document_date": parsed.get("document_date") or None,
            "gstin": parsed.get("gstin") or None,
            "vendor_name": parsed.get("vendor_name") or None,
            "document_type": parsed.get("document_type") or "unknown",
            "raw_text": raw_text,
            "source": "gemini",
        }

    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned non-JSON: %s — raw: %.200s", exc, raw_text if "raw_text" in dir() else "")
        return _error_result(raw_text if "raw_text" in locals() else "")
    except Exception as exc:
        logger.warning("Gemini OCR error: %s", exc)
        return _error_result("")


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _error_result(raw: str) -> dict:
    return {
        "total_amount": None,
        "document_date": None,
        "gstin": None,
        "vendor_name": None,
        "document_type": "unknown",
        "raw_text": raw,
        "source": "error",
    }
