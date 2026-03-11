"""Mixing Base API endpoints."""

import logging

import numpy as np
from flask import Blueprint, request, jsonify

from app import db
from app.models.base import MixingBase, MixingBaseConcentration, BaseSpectralData
from app.models.upload import UploadedFile
from app.models.series import InkSeries
from app.models.audit import AuditLog
from app.services.cxf_parser import CxfParser
from app.services.color_science import spectral_to_lab, reflectance_to_ks
from app.utils.auth import login_required, role_required, get_current_user
from app.utils.file_handler import allowed_file, save_upload

logger = logging.getLogger(__name__)
bases_bp = Blueprint('bases', __name__)


@bases_bp.route('/series/<int:series_id>', methods=['GET'])
@login_required
def list_bases(series_id):
    """List all mixing bases for an ink series."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    query = MixingBase.query.filter_by(series_id=series_id)
    if request.args.get('active_only', 'false').lower() == 'true':
        query = query.filter_by(is_active=True)

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            db.or_(
                MixingBase.code.ilike(f'%{search}%'),
                MixingBase.name.ilike(f'%{search}%'),
            )
        )

    include_conc = request.args.get('include_concentrations', 'false').lower() == 'true'
    bases = query.order_by(MixingBase.code).all()
    return jsonify({'bases': [b.to_dict(include_concentrations=include_conc) for b in bases]})


@bases_bp.route('/<int:base_id>', methods=['GET'])
@login_required
def get_base(base_id):
    """Get a single mixing base with concentrations."""
    base = db.session.get(MixingBase, base_id)
    if not base:
        return jsonify({'error': 'Mixing base not found'}), 404
    return jsonify({'base': base.to_dict(include_concentrations=True)})


@bases_bp.route('/series/<int:series_id>', methods=['POST'])
@role_required('admin', 'formulator')
def create_base(series_id):
    """Create a new mixing base."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    code = data.get('code', '').strip()
    name = data.get('name', '').strip()

    if not code or not name:
        return jsonify({'error': 'Code and name are required'}), 400

    existing = MixingBase.query.filter_by(series_id=series_id, code=code).first()
    if existing:
        return jsonify({'error': f'Base "{code}" already exists in this series'}), 409

    user = get_current_user()
    base = MixingBase(
        series_id=series_id,
        code=code,
        name=name,
        color_index=data.get('color_index', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
        created_by_id=user.id,
    )
    db.session.add(base)
    AuditLog.log(user.id, 'create_base', 'base', details={'code': code, 'series_id': series_id})
    db.session.commit()

    return jsonify({'base': base.to_dict()}), 201


@bases_bp.route('/<int:base_id>', methods=['PUT'])
@role_required('admin', 'formulator')
def update_base(base_id):
    """Update a mixing base."""
    base = db.session.get(MixingBase, base_id)
    if not base:
        return jsonify({'error': 'Mixing base not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if 'name' in data:
        base.name = data['name'].strip()
    if 'color_index' in data:
        base.color_index = data['color_index'].strip() or None
    if 'notes' in data:
        base.notes = data['notes'].strip() or None
    if 'is_active' in data:
        base.is_active = bool(data['is_active'])

    user = get_current_user()
    AuditLog.log(user.id, 'update_base', 'base', base.id, details=data)
    db.session.commit()

    return jsonify({'base': base.to_dict(include_concentrations=True)})


@bases_bp.route('/<int:base_id>/concentrations', methods=['POST'])
@role_required('admin', 'formulator')
def add_concentration(base_id):
    """Add a concentration level to a mixing base."""
    base = db.session.get(MixingBase, base_id)
    if not base:
        return jsonify({'error': 'Mixing base not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    pct = data.get('concentration_pct')
    if pct is None:
        return jsonify({'error': 'concentration_pct is required'}), 400

    try:
        pct = float(pct)
    except (ValueError, TypeError):
        return jsonify({'error': 'concentration_pct must be a number'}), 400

    if pct <= 0 or pct > 100:
        return jsonify({'error': 'concentration_pct must be between 0 and 100'}), 400

    existing = MixingBaseConcentration.query.filter_by(base_id=base_id, concentration_pct=pct).first()
    if existing:
        return jsonify({'error': f'Concentration {pct}% already exists for this base'}), 409

    conc = MixingBaseConcentration(
        base_id=base_id,
        concentration_pct=pct,
        label=data.get('label', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
    )
    db.session.add(conc)
    db.session.commit()

    return jsonify({'concentration': conc.to_dict()}), 201


@bases_bp.route('/concentrations/<int:conc_id>/upload-cxf', methods=['POST'])
@role_required('admin', 'formulator')
def upload_cxf(conc_id):
    """Upload a CXF file for a concentration level.

    Parses the CXF, extracts spectral data, computes LAB and K/S values,
    and creates a new version of spectral data for this concentration.
    """
    conc = db.session.get(MixingBaseConcentration, conc_id)
    if not conc:
        return jsonify({'error': 'Concentration level not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CXF/XML files are allowed'}), 400

    user = get_current_user()

    # Save raw file
    file_info = save_upload(file, purpose='base_spectral')

    upload_record = UploadedFile(
        original_filename=file_info['original_filename'],
        stored_filename=file_info['stored_filename'],
        file_type=file_info['file_type'],
        file_size=file_info['file_size'],
        mime_type=file_info['mime_type'],
        checksum_sha256=file_info['checksum_sha256'],
        purpose='base_spectral',
        uploaded_by_id=user.id,
    )
    db.session.add(upload_record)
    db.session.flush()

    # Parse CXF
    parser = CxfParser()
    result = parser.parse_bytes(file_info['content'])

    if not result.success:
        upload_record.status = 'error'
        upload_record.parse_errors = '; '.join(result.errors)
        db.session.commit()
        return jsonify({
            'error': 'Failed to parse CXF file',
            'details': result.errors,
        }), 400

    color = result.primary_color
    if not color or not color.spectral:
        upload_record.status = 'error'
        upload_record.parse_errors = 'No spectral reflectance data found in CXF file'
        db.session.commit()
        return jsonify({'error': 'No spectral reflectance data found in CXF file'}), 400

    upload_record.status = 'parsed'

    # Determine next version
    current = conc.current_spectral
    next_version = (current.version + 1) if current else 1

    # Mark previous version as non-current
    if current:
        current.is_current = False

    # Compute LAB and K/S
    reflectance = np.array(color.spectral.reflectance)
    lab = spectral_to_lab(reflectance)
    ks = reflectance_to_ks(reflectance)

    spectral = BaseSpectralData(
        concentration_id=conc.id,
        version=next_version,
        uploaded_file_id=upload_record.id,
        spectral_reflectance=color.spectral.reflectance,
        wavelength_start=color.spectral.wavelength_start,
        wavelength_end=color.spectral.wavelength_end,
        wavelength_interval=color.spectral.wavelength_interval,
        lab_l=float(lab[0]),
        lab_a=float(lab[1]),
        lab_b=float(lab[2]),
        ks_values=ks.tolist(),
        is_current=True,
        created_by_id=user.id,
    )
    db.session.add(spectral)

    AuditLog.log(
        user.id, 'upload_cxf', 'base_spectral', conc.id,
        details={
            'base_id': conc.base_id,
            'concentration_pct': conc.concentration_pct,
            'version': next_version,
            'filename': file_info['original_filename'],
        }
    )
    db.session.commit()

    return jsonify({
        'spectral_data': spectral.to_dict(),
        'warnings': result.warnings,
    }), 201


@bases_bp.route('/concentrations/<int:conc_id>/spectral', methods=['GET'])
@login_required
def get_spectral_data(conc_id):
    """Get spectral data for a concentration level."""
    conc = db.session.get(MixingBaseConcentration, conc_id)
    if not conc:
        return jsonify({'error': 'Concentration level not found'}), 404

    version = request.args.get('version')
    if version:
        spectral = BaseSpectralData.query.filter_by(
            concentration_id=conc_id, version=int(version)
        ).first()
    else:
        spectral = conc.current_spectral

    if not spectral:
        return jsonify({'error': 'No spectral data available'}), 404

    return jsonify({'spectral_data': spectral.to_dict()})


@bases_bp.route('/concentrations/<int:conc_id>/spectral/history', methods=['GET'])
@login_required
def get_spectral_history(conc_id):
    """Get all versions of spectral data for a concentration level."""
    conc = db.session.get(MixingBaseConcentration, conc_id)
    if not conc:
        return jsonify({'error': 'Concentration level not found'}), 404

    all_versions = conc.spectral_data.order_by(BaseSpectralData.version.desc()).all()
    return jsonify({
        'versions': [s.to_dict() for s in all_versions],
    })
