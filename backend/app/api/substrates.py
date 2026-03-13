"""Substrate management API endpoints."""

import logging

import numpy as np
from flask import Blueprint, request, jsonify

from app import db
from app.models.substrate import Substrate
from app.models.upload import UploadedFile
from app.models.audit import AuditLog
from app.services.cxf_parser import CxfParser
from app.services.color_science import spectral_to_lab, reflectance_to_ks
from app.utils.auth import login_required, role_required, get_current_user
from app.utils.file_handler import allowed_file, save_upload

logger = logging.getLogger(__name__)
substrates_bp = Blueprint('substrates', __name__)


@substrates_bp.route('', methods=['GET'])
@login_required
def list_substrates():
    """List substrates with optional filters."""
    query = Substrate.query

    active_only = request.args.get('active_only', '').lower() == 'true'
    if active_only:
        query = query.filter_by(is_active=True)

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            db.or_(
                Substrate.name.ilike(f'%{search}%'),
                Substrate.code.ilike(f'%{search}%'),
                Substrate.substrate_type.ilike(f'%{search}%'),
            )
        )

    substrates = query.order_by(Substrate.name).all()
    return jsonify({
        'substrates': [s.to_dict() for s in substrates],
    })


@substrates_bp.route('/<int:substrate_id>', methods=['GET'])
@login_required
def get_substrate(substrate_id):
    """Get a single substrate."""
    substrate = db.session.get(Substrate, substrate_id)
    if not substrate:
        return jsonify({'error': 'Substrate not found'}), 404
    return jsonify({'substrate': substrate.to_dict()})


@substrates_bp.route('', methods=['POST'])
@role_required('admin', 'formulator')
def create_substrate():
    """Create a substrate from JSON or CXF upload."""
    user = get_current_user()

    if request.content_type and 'multipart/form-data' in request.content_type:
        return _create_substrate_from_cxf(user)
    else:
        return _create_substrate_from_json(user)


def _create_substrate_from_json(user):
    """Create a substrate with manually entered data."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    code = data.get('code', '').strip()
    name = data.get('name', '').strip()
    if not code or not name:
        return jsonify({'error': 'code and name are required'}), 400

    existing = Substrate.query.filter_by(code=code).first()
    if existing:
        return jsonify({'error': f'Substrate with code "{code}" already exists'}), 409

    # If spectral reflectance is provided, compute K/S and LAB
    spectral = data.get('spectral_reflectance')
    ks_values = None
    lab_l, lab_a, lab_b = None, None, None
    if spectral and len(spectral) == 43:
        refl = np.array(spectral, dtype=float)
        ks_values = reflectance_to_ks(refl).tolist()
        lab = spectral_to_lab(refl)
        lab_l, lab_a, lab_b = float(lab[0]), float(lab[1]), float(lab[2])

    substrate = Substrate(
        code=code,
        name=name,
        substrate_type=data.get('substrate_type', '').strip() or None,
        description=data.get('description', '').strip() or None,
        spectral_reflectance=spectral,
        ks_values=ks_values,
        lab_l=lab_l,
        lab_a=lab_a,
        lab_b=lab_b,
        created_by_id=user.id,
    )
    db.session.add(substrate)
    AuditLog.log(user.id, 'create_substrate', 'substrate',
                 details={'code': code})
    db.session.commit()

    return jsonify({'substrate': substrate.to_dict()}), 201


def _create_substrate_from_cxf(user):
    """Create a substrate from an uploaded CXF file containing spectral data."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    if not code or not name:
        return jsonify({'error': 'code and name are required'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CXF/XML files are allowed'}), 400

    existing = Substrate.query.filter_by(code=code).first()
    if existing:
        return jsonify({'error': f'Substrate with code "{code}" already exists'}), 409

    # Save and parse file
    file_info = save_upload(file, purpose='substrate')
    upload_record = UploadedFile(
        original_filename=file_info['original_filename'],
        stored_filename=file_info['stored_filename'],
        file_type=file_info['file_type'],
        file_size=file_info['file_size'],
        mime_type=file_info['mime_type'],
        checksum_sha256=file_info['checksum_sha256'],
        purpose='substrate',
        uploaded_by_id=user.id,
    )
    db.session.add(upload_record)
    db.session.flush()

    parser = CxfParser()
    parse_result = parser.parse_bytes(file_info['content'])
    if not parse_result.success:
        upload_record.status = 'error'
        upload_record.parse_errors = '; '.join(parse_result.errors)
        db.session.commit()
        return jsonify({'error': 'Failed to parse CXF', 'details': parse_result.errors}), 400

    color = parse_result.primary_color
    upload_record.status = 'parsed'

    spectral = None
    ks_values = None
    lab_l, lab_a, lab_b = None, None, None

    if color.spectral:
        spectral = color.spectral.reflectance
        refl = np.array(spectral)
        ks_values = reflectance_to_ks(refl).tolist()
        lab = spectral_to_lab(refl)
        lab_l, lab_a, lab_b = float(lab[0]), float(lab[1]), float(lab[2])
    elif color.lab_l is not None:
        lab_l, lab_a, lab_b = color.lab_l, color.lab_a, color.lab_b

    substrate = Substrate(
        code=code,
        name=name,
        substrate_type=request.form.get('substrate_type', '').strip() or None,
        description=request.form.get('description', '').strip() or None,
        spectral_reflectance=spectral,
        ks_values=ks_values,
        lab_l=lab_l,
        lab_a=lab_a,
        lab_b=lab_b,
        uploaded_file_id=upload_record.id,
        created_by_id=user.id,
    )
    db.session.add(substrate)
    AuditLog.log(user.id, 'create_substrate', 'substrate',
                 details={'code': code, 'from_cxf': True})
    db.session.commit()

    return jsonify({'substrate': substrate.to_dict()}), 201


@substrates_bp.route('/<int:substrate_id>', methods=['PUT'])
@role_required('admin', 'formulator')
def update_substrate(substrate_id):
    """Update a substrate's metadata."""
    substrate = db.session.get(Substrate, substrate_id)
    if not substrate:
        return jsonify({'error': 'Substrate not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if 'name' in data:
        substrate.name = data['name'].strip()
    if 'substrate_type' in data:
        substrate.substrate_type = data['substrate_type'].strip() or None
    if 'description' in data:
        substrate.description = data['description'].strip() or None
    if 'is_active' in data:
        substrate.is_active = bool(data['is_active'])

    user = get_current_user()
    AuditLog.log(user.id, 'update_substrate', 'substrate', substrate.id)
    db.session.commit()

    return jsonify({'substrate': substrate.to_dict()})


@substrates_bp.route('/<int:substrate_id>', methods=['DELETE'])
@role_required('admin')
def delete_substrate(substrate_id):
    """Deactivate a substrate."""
    substrate = db.session.get(Substrate, substrate_id)
    if not substrate:
        return jsonify({'error': 'Substrate not found'}), 404

    substrate.is_active = False

    user = get_current_user()
    AuditLog.log(user.id, 'delete_substrate', 'substrate', substrate.id)
    db.session.commit()

    return jsonify({'message': f'Substrate "{substrate.code}" deactivated'})
