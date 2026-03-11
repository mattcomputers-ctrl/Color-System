from datetime import datetime, timezone

from app import db


class PantoneTarget(db.Model):
    """A Pantone color target with its reference spectral/LAB data.

    Pantone spectral data is proprietary and must be imported from licensed sources.
    This table stores the target data that formulas are matched against.
    """
    __tablename__ = 'pantone_targets'

    id = db.Column(db.Integer, primary_key=True)
    pantone_code = db.Column(db.String(50), nullable=False, index=True)
    pantone_name = db.Column(db.String(200))
    library = db.Column(db.String(100), default='PMS')  # PMS, PMS+, etc.

    # Target spectral data (if available)
    spectral_reflectance = db.Column(db.JSON)
    wavelength_start = db.Column(db.Integer, default=360)
    wavelength_end = db.Column(db.Integer, default=780)
    wavelength_interval = db.Column(db.Integer, default=10)

    # Target LAB values (D50/2°)
    lab_l = db.Column(db.Float)
    lab_a = db.Column(db.Float)
    lab_b = db.Column(db.Float)

    # Source of data
    source = db.Column(db.String(200))  # e.g., "Pantone PLUS Series Guide 2023"
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'))

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('pantone_code', 'library', name='uq_pantone_library'),
    )

    formulas = db.relationship('PantoneFormula', backref='target', lazy='dynamic')

    @property
    def lab_values(self):
        if self.lab_l is not None:
            return {'L': self.lab_l, 'a': self.lab_a, 'b': self.lab_b}
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'pantone_code': self.pantone_code,
            'pantone_name': self.pantone_name,
            'library': self.library,
            'has_spectral': self.spectral_reflectance is not None,
            'lab_values': self.lab_values,
            'source': self.source,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<PantoneTarget {self.pantone_code}>'


class PantoneFormula(db.Model):
    """A generated formula for a Pantone color using a specific ink series.

    Formulas are versioned — when bases are updated and formulas regenerated,
    old versions are preserved.
    """
    __tablename__ = 'pantone_formulas'

    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('pantone_targets.id'), nullable=False, index=True)
    series_id = db.Column(db.Integer, db.ForeignKey('ink_series.id'), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    # Predicted result
    predicted_spectral = db.Column(db.JSON)
    predicted_lab_l = db.Column(db.Float)
    predicted_lab_a = db.Column(db.Float)
    predicted_lab_b = db.Column(db.Float)

    # Quality metrics
    delta_e_76 = db.Column(db.Float)     # CIE76 Delta E
    delta_e_2000 = db.Column(db.Float)   # CIEDE2000 (preferred metric)

    # Status
    status = db.Column(db.String(20), default='generated')  # generated, approved, rejected
    is_current = db.Column(db.Boolean, default=True)

    notes = db.Column(db.Text)
    generated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint('target_id', 'series_id', 'version', name='uq_pantone_formula_version'),
    )

    generated_by = db.relationship('User', foreign_keys=[generated_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    components = db.relationship('PantoneFormulaComponent', backref='formula',
                                 cascade='all, delete-orphan',
                                 order_by='PantoneFormulaComponent.percentage.desc()')

    @property
    def predicted_lab(self):
        if self.predicted_lab_l is not None:
            return {'L': self.predicted_lab_l, 'a': self.predicted_lab_a, 'b': self.predicted_lab_b}
        return None

    def to_dict(self, include_components=True):
        result = {
            'id': self.id,
            'target_id': self.target_id,
            'series_id': self.series_id,
            'version': self.version,
            'predicted_lab': self.predicted_lab,
            'delta_e_76': self.delta_e_76,
            'delta_e_2000': self.delta_e_2000,
            'status': self.status,
            'is_current': self.is_current,
            'notes': self.notes,
            'generated_by': self.generated_by.full_name if self.generated_by else None,
            'approved_by': self.approved_by.full_name if self.approved_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
        }
        if include_components:
            result['components'] = [c.to_dict() for c in self.components]
        return result

    def __repr__(self):
        return f'<PantoneFormula target={self.target_id} series={self.series_id} v{self.version}>'


class PantoneFormulaComponent(db.Model):
    """A single component (mixing base) within a Pantone formula."""
    __tablename__ = 'pantone_formula_components'

    id = db.Column(db.Integer, primary_key=True)
    formula_id = db.Column(db.Integer, db.ForeignKey('pantone_formulas.id'), nullable=False)
    base_id = db.Column(db.Integer, db.ForeignKey('mixing_bases.id'), nullable=False)
    percentage = db.Column(db.Float, nullable=False)  # Weight percentage in formula
    weight_grams = db.Column(db.Float)  # Optional absolute weight for a standard batch

    base = db.relationship('MixingBase')

    def to_dict(self):
        return {
            'id': self.id,
            'base_id': self.base_id,
            'base_code': self.base.code if self.base else None,
            'base_name': self.base.name if self.base else None,
            'percentage': self.percentage,
            'weight_grams': self.weight_grams,
        }
