"""Tolerance profiles for configurable dE thresholds."""

from datetime import datetime, timezone

from app import db


class ToleranceProfile(db.Model):
    """Configurable color tolerance thresholds per customer/project.

    Instead of hardcoded dE thresholds (1.0/2.0), users can define
    named profiles with custom acceptable/marginal/out-of-tolerance levels.
    """
    __tablename__ = 'tolerance_profiles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    customer_name = db.Column(db.String(200))

    # dE2000 thresholds
    de_excellent = db.Column(db.Float, nullable=False, default=0.5)
    de_good = db.Column(db.Float, nullable=False, default=1.0)
    de_acceptable = db.Column(db.Float, nullable=False, default=2.0)

    # dE76 thresholds (optional legacy support)
    de76_acceptable = db.Column(db.Float, default=3.0)

    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def classify(self, de2000):
        """Classify a dE2000 value against this profile's thresholds."""
        if de2000 <= self.de_excellent:
            return 'excellent'
        elif de2000 <= self.de_good:
            return 'good'
        elif de2000 <= self.de_acceptable:
            return 'acceptable'
        else:
            return 'out_of_tolerance'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'customer_name': self.customer_name,
            'de_excellent': self.de_excellent,
            'de_good': self.de_good,
            'de_acceptable': self.de_acceptable,
            'de76_acceptable': self.de76_acceptable,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by.full_name if self.created_by else None,
        }

    def __repr__(self):
        return f'<ToleranceProfile {self.name}>'
