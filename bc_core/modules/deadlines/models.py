"""
ComplianceDeadline model — Feature 6.

Tracks filing deadlines per client (GSTR-1, GSTR-3B, CMP-08, Advance Tax,
FSSAI Renewal, etc.).

Status flow:  pending → reminded → acknowledged → completed
              pending → missed  (auto, by daily job if past due_date)
"""
from datetime import datetime

from core.extensions import db


class ComplianceDeadline(db.Model):
    __tablename__ = "compliance_deadline"

    id = db.Column(db.Integer, primary_key=True)

    # Which client + org
    client_id = db.Column(
        db.Integer, db.ForeignKey("business.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    org_id = db.Column(
        db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Deadline info
    deadline_type = db.Column(db.String(50), nullable=False)
    # e.g. gstr1_monthly, gstr1_quarterly, gstr3b, cmp08,
    #      advance_tax_q1..q4, fssai_renewal
    description = db.Column(db.String(200), nullable=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    period_start = db.Column(db.Date, nullable=True)
    period_end = db.Column(db.Date, nullable=True)

    # Status: pending | reminded | acknowledged | completed | missed
    status = db.Column(
        db.String(20), nullable=False, default="pending", index=True,
    )

    # Tracking timestamps
    reminder_sent_at = db.Column(db.DateTime, nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow,
    )

    # Relationships
    client = db.relationship(
        "Business", backref=db.backref("deadlines", lazy="dynamic"),
    )
    completer = db.relationship("User", foreign_keys=[completed_by])

    def __repr__(self):
        return (
            f"<ComplianceDeadline id={self.id} type={self.deadline_type} "
            f"due={self.due_date} status={self.status}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "client_id":        self.client_id,
            "org_id":           self.org_id,
            "deadline_type":    self.deadline_type,
            "description":      self.description,
            "due_date":         self.due_date.isoformat() if self.due_date else None,
            "period_start":     self.period_start.isoformat() if self.period_start else None,
            "period_end":       self.period_end.isoformat() if self.period_end else None,
            "status":           self.status,
            "reminder_sent_at": self.reminder_sent_at.isoformat() if self.reminder_sent_at else None,
            "acknowledged_at":  self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "completed_at":     self.completed_at.isoformat() if self.completed_at else None,
            "completed_by":     self.completed_by,
            "notes":            self.notes,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }
