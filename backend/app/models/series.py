from datetime import datetime, timezone

from app import db


class SubstrateSeriesAssociation(db.Model):
    """Links substrates to ink series as defaults.

    When a substrate is associated with a series, it becomes the default
    substrate selection for formulations in that series.
    """
    __tablename__ = 'substrate_series_associations'

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey('ink_series.id'), nullable=False)
    substrate_id = db.Column(db.Integer, db.ForeignKey('substrates.id'), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    series = db.relationship('InkSeries', back_populates='substrate_associations')
    substrate = db.relationship('Substrate')

    __table_args__ = (
        db.UniqueConstraint('series_id', 'substrate_id', name='uq_series_substrate'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'series_id': self.series_id,
            'substrate_id': self.substrate_id,
            'is_default': self.is_default,
            'substrate': self.substrate.to_dict() if self.substrate else None,
        }


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
    ink_type = db.Column(db.String(50), default='litho')  # 'litho' or 'flexo'
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
    substrate_associations = db.relationship('SubstrateSeriesAssociation',
                                             back_populates='series', lazy='dynamic',
                                             cascade='all, delete-orphan')

    @property
    def default_substrate(self):
        """Get the default substrate for this series, if any."""
        assoc = self.substrate_associations.filter_by(is_default=True).first()
        return assoc.substrate if assoc else None

    def to_dict(self):
        default_sub = self.default_substrate
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'ink_type': self.ink_type or 'litho',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by.full_name if self.created_by else None,
            'base_count': self.mixing_bases.count(),
            'default_substrate': default_sub.to_dict() if default_sub else None,
        }

    def __repr__(self):
        return f'<InkSeries {self.code}: {self.name}>'
