from datetime import datetime, timezone

from app import db


class UploadedFile(db.Model):
    """Record of an uploaded file (CXF or other).

    Stores both the path to the raw file on disk and metadata about the upload.
    Raw files are preserved for audit and re-processing.
    """
    __tablename__ = 'uploaded_files'

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(500), nullable=False)
    stored_filename = db.Column(db.String(500), nullable=False, unique=True)
    file_type = db.Column(db.String(50), nullable=False)  # 'cxf', 'csv', etc.
    file_size = db.Column(db.Integer)  # bytes
    mime_type = db.Column(db.String(100))
    checksum_sha256 = db.Column(db.String(64))

    # What this file was uploaded for
    purpose = db.Column(db.String(50))  # 'base_spectral', 'target_color', etc.

    # Processing status
    status = db.Column(db.String(20), default='uploaded')  # uploaded, parsed, error
    parse_errors = db.Column(db.Text)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'purpose': self.purpose,
            'status': self.status,
            'parse_errors': self.parse_errors,
            'uploaded_by': self.uploaded_by.full_name if self.uploaded_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<UploadedFile {self.original_filename}>'
