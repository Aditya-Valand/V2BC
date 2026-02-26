"""
OCR orchestration service.

Calls Gemini Vision, maps results onto BusinessEvidence,
updates linked BusinessStatement confidence.
"""
import logging
from datetime import datetime

from core.extensions import db
from modules.ocr.client import extract_structured

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Evidence-strength helpers
# ------------------------------------------------------------------ #

def _strength(quality_score: float, has_amount: bool,
               has_gstin: bool, raw_text_len: int) -> str:
    """
    Compute evidence strength from quality + OCR outcome.

    strong  — usable quality + (amount + GSTIN) or amount + rich text
    medium  — acceptable quality + at least amount OR rich text
    weak    — low quality or no useful extraction
    """
    if quality_score >= 60:
        if has_amount and has_gstin:
            return "strong"
        if has_amount and raw_text_len > 50:
            return "strong"
        if has_amount or raw_text_len > 80:
            return "medium"
    elif quality_score >= 30:
        if has_amount:
            return "medium"
    return "weak"


def _strength_reason(quality_score: float, has_amount: bool,
                     has_gstin: bool, raw_text_len: int) -> str:
    parts = []
    if quality_score < 30:
        parts.append("blurry image")
    elif quality_score < 60:
        parts.append("low-quality image")
    else:
        parts.append("clear image")

    if has_amount and has_gstin:
        parts.append("amount and GSTIN extracted")
    elif has_amount:
        parts.append("amount extracted")
    elif raw_text_len > 50:
        parts.append("text extracted but no amount")
    else:
        parts.append("no useful data extracted")

    return ", ".join(parts)


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def run_ocr(evidence) -> dict:
    """
    Run Gemini Vision OCR on evidence.file_path.
    Updates evidence record (commits) and returns result dict.

    Returns:
        {
            "amount": float | None,
            "date": str | None,
            "gstin": str | None,
            "vendor_name": str | None,
            "document_type": str,
            "strength": str,
            "source": str,
        }
    """
    try:
        result = extract_structured(evidence.file_path)

        amount   = result["total_amount"]
        gstin    = result["gstin"]
        raw_text = result.get("raw_text", "")

        # Parse date string → datetime if provided
        detected_date = None
        if result.get("document_date"):
            try:
                detected_date = datetime.strptime(result["document_date"], "%Y-%m-%d")
            except ValueError:
                pass

        # Update evidence record
        evidence.ocr_text        = raw_text
        evidence.detected_amount = amount
        evidence.detected_gstin  = gstin
        evidence.detected_date   = detected_date
        evidence.evidence_type   = result.get("document_type") or evidence.evidence_type

        # Status based on extraction quality
        if amount or gstin:
            evidence.status = "usable"
        else:
            evidence.status = "needs_review"

        evidence.evidence_strength = _strength(
            evidence.quality_score or 0,
            has_amount=amount is not None,
            has_gstin=gstin is not None,
            raw_text_len=len(raw_text),
        )

        db.session.commit()

        # Update linked statement confidence
        if evidence.statement_id:
            _update_statement_confidence(evidence)

        logger.info(
            "OCR complete: evidence_id=%d amount=%s gstin=%s strength=%s source=%s",
            evidence.id, amount, gstin, evidence.evidence_strength, result["source"]
        )

        return {
            "amount":        amount,
            "date":          result.get("document_date"),
            "gstin":         gstin,
            "vendor_name":   result.get("vendor_name"),
            "document_type": result.get("document_type", "unknown"),
            "strength":      evidence.evidence_strength,
            "source":        result["source"],
        }

    except Exception as exc:
        logger.exception("run_ocr error (evidence_id=%s): %s", getattr(evidence, "id", "?"), exc)
        try:
            evidence.status = "error"
            db.session.commit()
        except Exception:
            db.session.rollback()
        return {"amount": None, "date": None, "gstin": None,
                "vendor_name": None, "document_type": "unknown",
                "strength": "weak", "source": "error"}


def _update_statement_confidence(evidence):
    """Upgrade/downgrade the linked BusinessStatement confidence based on OCR."""
    try:
        from modules.statements.models import BusinessStatement
        stmt = BusinessStatement.query.get(evidence.statement_id)
        if not stmt:
            return

        has_amount = evidence.detected_amount is not None
        has_gstin  = evidence.detected_gstin  is not None
        raw_len    = len(evidence.ocr_text or "")

        if has_amount and has_gstin:
            stmt.confidence_level = "high"
        elif has_amount or raw_len > 100:
            stmt.confidence_level = "medium"
        else:
            stmt.confidence_level = "low"

        db.session.commit()
    except Exception as exc:
        logger.warning("_update_statement_confidence: %s", exc)
        db.session.rollback()


# keep old name as alias so existing callers don't break
def classify_strength_from_quality(quality_score: float) -> str:
    if quality_score > 150:
        return "strong"
    if quality_score > 80:
        return "medium"
    return "weak"
