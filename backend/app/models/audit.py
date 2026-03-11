from datetime import datetime, timezone

from app import db


class AuditLog(db.Model):
    """Audit trail for significant actions in the system."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(50), index=True)  # 'series', 'base', 'formula', etc.
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)  # Arbitrary details about the action
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           nullable=False, index=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.full_name if self.user else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def log(cls, user_id, action, entity_type=None, entity_id=None,
            details=None, ip_address=None):
        entry = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        db.session.add(entry)
        return entry
