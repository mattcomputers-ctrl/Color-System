from datetime import datetime, timezone

from app import db


class InkSeries(db.Model):
    """An ink series is a product line of mixing bases.

    Each series is independent — formulations are always scoped to a single series.
    Examples: "UV Process Series", "Conventional Offset Series", "Flexo Water-Based Series"
    """
    __tablename__ = 'ink_series'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    mixing_bases = db.relationship('MixingBase', backref='series', lazy='dynamic',
                                   cascade='all, delete-orphan')
    pantone_formulas = db.relationship('PantoneFormula', backref='series', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by.full_name if self.created_by else None,
            'base_count': self.mixing_bases.count(),
        }

    def __repr__(self):
        return f'<InkSeries {self.code}: {self.name}>'
