from core.extensions import db
from modules.statements.models import BusinessStatement
from modules.statements.parser import parse_statement

def create_statement(business_id, raw_text, source="whatsapp"):
    parsed = parse_statement(raw_text)

    stmt = BusinessStatement(
        business_id=business_id,
        raw_text=raw_text,
        statement_type=parsed["statement_type"] if parsed else "unknown",
        amount=parsed["amount"] if parsed else None,
        source=source,
        confidence_level="low"
    )

    db.session.add(stmt)
    db.session.commit()
    return stmt
