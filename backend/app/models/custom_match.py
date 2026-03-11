from datetime import datetime, timezone

from app import db


class CustomMatchJob(db.Model):
    """A custom color matching request.

    Users can submit a target color (via CXF upload or manual LAB entry)
    and the system will calculate the best formula using a selected ink series.
    """
    __tablename__ = 'custom_match_jobs'

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey('ink_series.id'), nullable=False, index=True)

    # Job metadata
    job_name = db.Column(db.String(200))
    customer_name = db.Column(db.String(200))
    project_name = db.Column(db.String(200))
    notes = db.Column(db.Text)

    # Target source
    target_source_type = db.Column(db.String(20), nullable=False)  # 'cxf' or 'lab'
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'))

    # Target spectral data (from CXF)
    target_spectral = db.Column(db.JSON)

    # Target LAB values (entered manually or derived from spectral)
    target_lab_l = db.Column(db.Float)
    target_lab_a = db.Column(db.Float)
    target_lab_b = db.Column(db.Float)

    # Status
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    series = db.relationship('InkSeries')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    uploaded_file = db.relationship('UploadedFile', foreign_keys=[uploaded_file_id])
    results = db.relationship('CustomMatchResult', backref='job',
                              cascade='all, delete-orphan',
                              order_by='CustomMatchResult.delta_e_2000')

    @property
    def target_lab(self):
        if self.target_lab_l is not None:
            return {'L': self.target_lab_l, 'a': self.target_lab_a, 'b': self.target_lab_b}
        return None

    @property
    def best_result(self):
        if self.results:
            return self.results[0]  # Already ordered by delta_e_2000 asc
        return None

    def to_dict(self, include_results=False):
        result = {
            'id': self.id,
            'series_id': self.series_id,
            'series_name': self.series.name if self.series else None,
            'job_name': self.job_name,
            'customer_name': self.customer_name,
            'project_name': self.project_name,
            'notes': self.notes,
            'target_source_type': self.target_source_type,
            'target_lab': self.target_lab,
            'status': self.status,
            'created_by': self.created_by.full_name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'best_delta_e': self.best_result.delta_e_2000 if self.best_result else None,
        }
        if include_results:
            result['results'] = [r.to_dict() for r in self.results]
        return result

    def __repr__(self):
        return f'<CustomMatchJob {self.id}: {self.job_name}>'


class CustomMatchResult(db.Model):
    """A formula result from a custom color match job.

    Multiple results may be generated per job (e.g., top 3 best matches).
    """
    __tablename__ = 'custom_match_results'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('custom_match_jobs.id'), nullable=False, index=True)
    rank = db.Column(db.Integer, default=1)

    # Predicted result
    predicted_spectral = db.Column(db.JSON)
    predicted_lab_l = db.Column(db.Float)
    predicted_lab_a = db.Column(db.Float)
    predicted_lab_b = db.Column(db.Float)

    # Quality metrics
    delta_e_76 = db.Column(db.Float)
    delta_e_2000 = db.Column(db.Float)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    components = db.relationship('CustomMatchComponent', backref='result',
                                 cascade='all, delete-orphan',
                                 order_by='CustomMatchComponent.percentage.desc()')

    @property
    def predicted_lab(self):
        if self.predicted_lab_l is not None:
            return {'L': self.predicted_lab_l, 'a': self.predicted_lab_a, 'b': self.predicted_lab_b}
        return None

    def to_dict(self, include_components=True):
        result = {
            'id': self.id,
            'job_id': self.job_id,
            'rank': self.rank,
            'predicted_lab': self.predicted_lab,
            'delta_e_76': self.delta_e_76,
            'delta_e_2000': self.delta_e_2000,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_components:
            result['components'] = [c.to_dict() for c in self.components]
        return result


class CustomMatchComponent(db.Model):
    """A single component in a custom match formula."""
    __tablename__ = 'custom_match_components'

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('custom_match_results.id'), nullable=False)
    base_id = db.Column(db.Integer, db.ForeignKey('mixing_bases.id'), nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    weight_grams = db.Column(db.Float)

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
