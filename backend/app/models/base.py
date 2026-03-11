from datetime import datetime, timezone

from app import db


class MixingBase(db.Model):
    """A mixing base (colorant/pigment) within an ink series.

    A base is a specific colorant identified by its code and name.
    Each base can have multiple concentration levels, each with its own spectral data.
    """
    __tablename__ = 'mixing_bases'

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey('ink_series.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    color_index = db.Column(db.String(100))  # e.g., "PB 15:3" for Pigment Blue 15:3
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Unique within a series
    __table_args__ = (
        db.UniqueConstraint('series_id', 'code', name='uq_base_series_code'),
    )

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    concentrations = db.relationship('MixingBaseConcentration', backref='base',
                                     lazy='dynamic', cascade='all, delete-orphan',
                                     order_by='MixingBaseConcentration.concentration_pct')

    def to_dict(self, include_concentrations=False):
        result = {
            'id': self.id,
            'series_id': self.series_id,
            'code': self.code,
            'name': self.name,
            'color_index': self.color_index,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'concentration_count': self.concentrations.count(),
        }
        if include_concentrations:
            result['concentrations'] = [c.to_dict() for c in self.concentrations.all()]
        return result

    def __repr__(self):
        return f'<MixingBase {self.code}: {self.name}>'


class MixingBaseConcentration(db.Model):
    """A specific concentration level of a mixing base.

    For Kubelka-Munk formulation, we typically need spectral data at a known
    concentration (drawdown) against a known substrate. This model stores that
    relationship and links to the spectral data.
    """
    __tablename__ = 'mixing_base_concentrations'

    id = db.Column(db.Integer, primary_key=True)
    base_id = db.Column(db.Integer, db.ForeignKey('mixing_bases.id'), nullable=False, index=True)
    concentration_pct = db.Column(db.Float, nullable=False)  # e.g., 100.0 for full strength
    label = db.Column(db.String(100))  # e.g., "Full Strength", "25% Letdown"
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Each concentration level can have multiple spectral data records (revisions)
    spectral_data = db.relationship('BaseSpectralData', backref='concentration',
                                    lazy='dynamic', cascade='all, delete-orphan',
                                    order_by='BaseSpectralData.version.desc()')

    __table_args__ = (
        db.UniqueConstraint('base_id', 'concentration_pct', name='uq_base_concentration'),
    )

    @property
    def current_spectral(self):
        """Return the most recent (highest version) spectral data."""
        return self.spectral_data.order_by(BaseSpectralData.version.desc()).first()

    def to_dict(self, include_spectral=False):
        current = self.current_spectral
        result = {
            'id': self.id,
            'base_id': self.base_id,
            'concentration_pct': self.concentration_pct,
            'label': self.label,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'has_spectral_data': current is not None,
            'current_version': current.version if current else None,
            'lab_values': current.lab_values if current else None,
        }
        if include_spectral and current:
            result['spectral'] = current.to_dict()
        return result

    def __repr__(self):
        return f'<Concentration {self.base.code} @ {self.concentration_pct}%>'


class BaseSpectralData(db.Model):
    """Spectral reflectance data for a mixing base at a specific concentration.

    Each record is a version — when new CXF data is uploaded for the same base/concentration,
    a new version is created, preserving the old one for audit purposes.

    Spectral data is stored as a JSON array of reflectance values at 10nm intervals
    from 360nm to 780nm (43 values).
    """
    __tablename__ = 'base_spectral_data'

    id = db.Column(db.Integer, primary_key=True)
    concentration_id = db.Column(db.Integer,
                                 db.ForeignKey('mixing_base_concentrations.id'),
                                 nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'))

    # Spectral reflectance: array of floats, 360-780nm at 10nm intervals
    # Stored as PostgreSQL JSONB for efficient querying
    spectral_reflectance = db.Column(db.JSON, nullable=False)

    # Wavelength range metadata
    wavelength_start = db.Column(db.Integer, default=360)
    wavelength_end = db.Column(db.Integer, default=780)
    wavelength_interval = db.Column(db.Integer, default=10)

    # Derived LAB values (D50/2° observer, standard for printing industry)
    lab_l = db.Column(db.Float)
    lab_a = db.Column(db.Float)
    lab_b = db.Column(db.Float)

    # Derived K/S values (Kubelka-Munk absorption/scattering ratios)
    # Calculated from reflectance: K/S = (1-R)² / (2R)
    ks_values = db.Column(db.JSON)

    notes = db.Column(db.Text)
    is_current = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    __table_args__ = (
        db.UniqueConstraint('concentration_id', 'version', name='uq_spectral_version'),
    )

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    uploaded_file = db.relationship('UploadedFile', foreign_keys=[uploaded_file_id])

    @property
    def lab_values(self):
        if self.lab_l is not None:
            return {'L': self.lab_l, 'a': self.lab_a, 'b': self.lab_b}
        return None

    @property
    def wavelengths(self):
        """Return the list of wavelengths corresponding to the spectral data."""
        return list(range(self.wavelength_start, self.wavelength_end + 1, self.wavelength_interval))

    def to_dict(self):
        return {
            'id': self.id,
            'concentration_id': self.concentration_id,
            'version': self.version,
            'spectral_reflectance': self.spectral_reflectance,
            'wavelength_start': self.wavelength_start,
            'wavelength_end': self.wavelength_end,
            'wavelength_interval': self.wavelength_interval,
            'lab_values': self.lab_values,
            'ks_values': self.ks_values,
            'is_current': self.is_current,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploaded_file_id': self.uploaded_file_id,
        }

    def __repr__(self):
        return f'<SpectralData conc={self.concentration_id} v{self.version}>'
