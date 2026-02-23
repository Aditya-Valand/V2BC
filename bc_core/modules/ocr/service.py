from modules.ocr.client import extract_text
from modules.ocr.extractor import extract_amount, extract_date, extract_gstin
from core.extensions import db


def classify_strength_from_quality(quality_score: float) -> str:
    """
    Classify evidence strength based on image quality score.
    
    Args:
        quality_score: Laplacian blur detection score
        
    Returns:
        'strong', 'medium', or 'weak'
    """
    if quality_score > 150:
        return "strong"  # Clear, legible
    elif quality_score > 80:
        return "medium"  # Acceptable
    else:
        return "weak"    # Blurry/illegible


def refine_strength_from_ocr(evidence) -> str:
    """
    Refine evidence strength classification based on OCR results.
    
    Args:
        evidence: BusinessEvidence object with OCR data populated
        
    Returns:
        'strong', 'medium', or 'weak'
    """
    # Start with quality-based assessment
    base_strength = classify_strength_from_quality(evidence.quality_score)
    
    # Upgrade if we extracted good data
    has_amount = evidence.detected_amount is not None
    has_gstin = evidence.detected_gstin is not None
    has_date = evidence.detected_date is not None
    has_ocr_text = evidence.ocr_text and len(evidence.ocr_text) > 50
    
    # Strong: clear image + (amount + GSTIN) or good OCR text
    if base_strength in ("strong", "medium"):
        if (has_amount and has_gstin) or (has_ocr_text and has_amount):
            return "strong"
    
    # Medium: acceptable image + some extracted data
    if base_strength == "medium":
        if has_amount or (has_ocr_text and len(evidence.ocr_text) > 30):
            return "medium"
    
    # Weak: poor quality or minimal extracted data
    return "weak"


def run_ocr(evidence):
    """
    Run OCR on an evidence file and update confidence levels.
    
    Args:
        evidence: BusinessEvidence object to process
        
    Returns:
        Dictionary with extracted fields: amount, gstin, date
    """
    try:
        full_text, blocks = extract_text(evidence.file_path)

        amount = extract_amount(full_text)
        gstin = extract_gstin(full_text)
        date = extract_date(full_text)

        evidence.ocr_text = full_text
        evidence.detected_amount = amount
        evidence.detected_gstin = gstin
        evidence.detected_date = date

        # Update status based on extracted data
        if amount or gstin:
            evidence.status = "usable"
        else:
            evidence.status = "needs_review"

        # Refine evidence strength based on OCR results
        evidence.evidence_strength = refine_strength_from_ocr(evidence)

        db.session.commit()

        # If this evidence is linked to a statement, update its confidence
        if evidence.statement_id:
            from modules.statements.models import BusinessStatement
            update_statement_confidence(evidence, BusinessStatement)

        return {
            "amount": amount,
            "gstin": gstin,
            "date": str(date) if date else None,
            "strength": evidence.evidence_strength
        }
        
    except Exception as e:
        print(f"Error running OCR on evidence {evidence.id}: {str(e)}")
        evidence.status = "error"
        db.session.commit()
        return {
            "amount": None,
            "gstin": None,
            "date": None,
            "error": str(e)
        }


def update_statement_confidence(evidence, BusinessStatement):
    """
    Update a statement's confidence level based on linked evidence.
    
    Args:
        evidence: BusinessEvidence with OCR data
        BusinessStatement: Model class (passed to avoid circular import)
    """
    if not evidence.statement_id:
        return
    
    statement = BusinessStatement.query.get(evidence.statement_id)
    if not statement:
        return
    
    # Determine confidence based on what we extracted
    has_amount = evidence.detected_amount is not None
    has_gstin = evidence.detected_gstin is not None
    has_ocr_text = evidence.ocr_text and len(evidence.ocr_text) > 50
    
    # High confidence: clear amount AND GSTIN
    if has_amount and has_gstin:
        statement.confidence_level = 'high'
    # Medium confidence: amount extracted or good OCR text
    elif has_amount or (has_ocr_text and len(evidence.ocr_text) > 100):
        statement.confidence_level = 'medium'
    # Low confidence: minimal extracted data
    else:
        statement.confidence_level = 'low'
    
    db.session.commit()
