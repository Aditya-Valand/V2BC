import os
import uuid
from core.extensions import db
from modules.evidence.models import BusinessEvidence
from modules.evidence.quality import image_quality_score
from modules.ocr.service import run_ocr, classify_strength_from_quality

UPLOAD_DIR = "storage/uploads"


def save_evidence(file, business_id, statement_id=None, source="whatsapp"):
    """
    Save an evidence file and classify its strength.
    
    Args:
        file: File object from Flask request
        business_id: ID of business this evidence belongs to
        statement_id: ID of statement this evidence supports (optional)
        source: Where the file came from (whatsapp, web, etc)
        
    Returns:
        BusinessEvidence: Saved evidence object with strength classified
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)

    # Calculate quality score (measures image clarity)
    quality_score = image_quality_score(path)

    # Determine initial status based on quality
    status = "usable" if quality_score > 100 else "needs_review"
    
    # Classify evidence strength (will be refined by OCR)
    evidence_strength = classify_strength_from_quality(quality_score)

    # Create evidence record
    ev = BusinessEvidence(
        business_id=business_id,
        statement_id=statement_id,
        file_name=file.filename,
        file_path=path,
        source=source,
        quality_score=quality_score,
        status=status,
        evidence_strength=evidence_strength,
        evidence_type="unknown"  # Will be updated by OCR
    )

    db.session.add(ev)
    db.session.commit()
    
    # Run OCR to extract text and refine strength
    run_ocr(ev)
    
    return ev
