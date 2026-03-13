from datetime import datetime, timezone

from app import db


class Substrate(db.Model):
    """A printing substrate (paper, film, foil, etc.).

    Substrates affect color appearance because the base reflectance of
    the substrate is the starting point for Kubelka-Munk predictions.
    Each substrate stores spectral reflectance and derived K/S values
    so formulations can account for the actual printing surface.
    """
    __tablename__ = 'substrates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    substrate_type = db.Column(db.String(100))  # e.g., 'Coated Paper', 'Uncoated Paper', 'Film', 'Foil'
    description = db.Column(db.Text)

    # Spectral reflectance: array of 43 floats, 360-780nm at 10nm intervals
    spectral_reflectance = db.Column(db.JSON)
    wavelength_start = db.Column(db.Integer, default=360)
    wavelength_end = db.Column(db.Integer, default=780)
    wavelength_interval = db.Column(db.Integer, default=10)

    # Derived K/S values (computed from spectral_reflectance)
    ks_values = db.Column(db.JSON)

    # Derived LAB values (D50/2deg observer)
    lab_l = db.Column(db.Float)
    lab_a = db.Column(db.Float)
    lab_b = db.Column(db.Float)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    uploaded_file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'))

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    uploaded_file = db.relationship('UploadedFile', foreign_keys=[uploaded_file_id])

    @property
    def lab_values(self):
        if self.lab_l is not None:
            return {'L': self.lab_l, 'a': self.lab_a, 'b': self.lab_b}
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'substrate_type': self.substrate_type,
            'description': self.description,
            'has_spectral': self.spectral_reflectance is not None,
            'lab_values': self.lab_values,
            'is_active': self.is_active,
            'created_by': self.created_by.full_name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Substrate {self.code}: {self.name}>'
