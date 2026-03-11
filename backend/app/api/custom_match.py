"""Custom Color Match API endpoints."""

import logging

import numpy as np
from flask import Blueprint, request, jsonify

from app import db
from app.models.custom_match import CustomMatchJob, CustomMatchResult, CustomMatchComponent
from app.models.series import InkSeries
from app.models.upload import UploadedFile
from app.models.audit import AuditLog
from app.services.cxf_parser import CxfParser
from app.services.color_science import spectral_to_lab, delta_e_2000, reflectance_to_ks
from app.services.formulation_engine import FormulationEngine
from app.api.pantone import _load_series_colorants
from app.utils.auth import login_required, role_required, get_current_user
from app.utils.file_handler import allowed_file, save_upload
from pantone_data import PANTONE_COLORS

logger = logging.getLogger(__name__)
custom_match_bp = Blueprint('custom_match', __name__)


def find_closest_pantone(target_lab, count=5):
    """Find the closest Pantone colors to a target LAB value.

    Returns a list of dicts sorted by dE00 ascending, each containing:
    pantone_code, pantone_name, library, lab (L/a/b), delta_e_2000.
    """
    target = (float(target_lab[0]), float(target_lab[1]), float(target_lab[2]))
    scored = []
    for code, name, library, lab_l, lab_a, lab_b in PANTONE_COLORS:
        de = delta_e_2000(target, (lab_l, lab_a, lab_b))
        scored.append({
            'pantone_code': code,
            'pantone_name': name,
            'library': library,
            'lab': {'L': lab_l, 'a': lab_a, 'b': lab_b},
            'delta_e_2000': round(de, 4),
        })
    scored.sort(key=lambda x: x['delta_e_2000'])
    return scored[:count]


@custom_match_bp.route('/jobs', methods=['GET'])
@login_required
def list_jobs():
    """List custom match jobs with optional filters."""
    query = CustomMatchJob.query

    series_id = request.args.get('series_id', type=int)
    if series_id:
        query = query.filter_by(series_id=series_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            db.or_(
                CustomMatchJob.job_name.ilike(f'%{search}%'),
                CustomMatchJob.customer_name.ilike(f'%{search}%'),
                CustomMatchJob.project_name.ilike(f'%{search}%'),
            )
        )

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    per_page = min(per_page, 100)

    pagination = query.order_by(CustomMatchJob.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'jobs': [j.to_dict() for j in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@custom_match_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """Get a custom match job with results."""
    job = db.session.get(CustomMatchJob, job_id)
    if not job:
        return jsonify({'error': 'Match job not found'}), 404
    job_dict = job.to_dict(include_results=True)
    if job.target_lab_l is not None:
        job_dict['closest_pantone'] = find_closest_pantone(
            (job.target_lab_l, job.target_lab_a, job.target_lab_b), count=5
        )
    return jsonify({'job': job_dict})


@custom_match_bp.route('/match-lab', methods=['POST'])
@role_required('admin', 'formulator')
def match_from_lab():
    """Create a custom match job from manual LAB values."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    series_id = data.get('series_id')
    lab_l = data.get('lab_l')
    lab_a = data.get('lab_a')
    lab_b = data.get('lab_b')

    if not series_id:
        return jsonify({'error': 'series_id is required'}), 400
    if lab_l is None or lab_a is None or lab_b is None:
        return jsonify({'error': 'lab_l, lab_a, and lab_b are required'}), 400

    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    user = get_current_user()

    job = CustomMatchJob(
        series_id=series_id,
        job_name=data.get('job_name', '').strip() or None,
        customer_name=data.get('customer_name', '').strip() or None,
        project_name=data.get('project_name', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
        target_source_type='lab',
        target_lab_l=float(lab_l),
        target_lab_a=float(lab_a),
        target_lab_b=float(lab_b),
        status='processing',
        created_by_id=user.id,
    )
    db.session.add(job)
    db.session.flush()

    # Run formulation
    colorants, substrate_ks = _load_series_colorants(series_id)
    if not colorants:
        job.status = 'failed'
        db.session.commit()
        return jsonify({'error': 'No bases with spectral data in this series'}), 400

    engine = FormulationEngine()
    results = engine.formulate_multi(
        target_lab=(float(lab_l), float(lab_a), float(lab_b)),
        colorants=colorants,
        substrate_ks=substrate_ks,
        num_results=3,
    )

    _save_match_results(job, results)
    job.status = 'completed'

    AuditLog.log(user.id, 'custom_match_lab', 'custom_match', job.id,
                 details={'series_id': series_id, 'target_lab': [lab_l, lab_a, lab_b]})
    db.session.commit()

    job_dict = job.to_dict(include_results=True)
    job_dict['closest_pantone'] = find_closest_pantone(
        (float(lab_l), float(lab_a), float(lab_b)), count=5
    )
    return jsonify({'job': job_dict}), 201


@custom_match_bp.route('/match-cxf', methods=['POST'])
@role_required('admin', 'formulator')
def match_from_cxf():
    """Create a custom match job from an uploaded CXF file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    series_id = request.form.get('series_id', type=int)

    if not series_id:
        return jsonify({'error': 'series_id is required'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CXF/XML files are allowed'}), 400

    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    user = get_current_user()

    # Save and parse file
    file_info = save_upload(file, purpose='custom_target')
    upload_record = UploadedFile(
        original_filename=file_info['original_filename'],
        stored_filename=file_info['stored_filename'],
        file_type=file_info['file_type'],
        file_size=file_info['file_size'],
        mime_type=file_info['mime_type'],
        checksum_sha256=file_info['checksum_sha256'],
        purpose='custom_target',
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

    target_spectral = None
    target_reflectance = None
    lab_l, lab_a, lab_b = None, None, None

    if color.spectral:
        target_spectral = color.spectral.reflectance
        target_reflectance = np.array(target_spectral)
        lab = spectral_to_lab(target_reflectance)
        lab_l, lab_a, lab_b = float(lab[0]), float(lab[1]), float(lab[2])
    elif color.lab_l is not None:
        lab_l, lab_a, lab_b = color.lab_l, color.lab_a, color.lab_b

    job = CustomMatchJob(
        series_id=series_id,
        job_name=request.form.get('job_name', '').strip() or None,
        customer_name=request.form.get('customer_name', '').strip() or None,
        project_name=request.form.get('project_name', '').strip() or None,
        notes=request.form.get('notes', '').strip() or None,
        target_source_type='cxf',
        uploaded_file_id=upload_record.id,
        target_spectral=target_spectral,
        target_lab_l=lab_l,
        target_lab_a=lab_a,
        target_lab_b=lab_b,
        status='processing',
        created_by_id=user.id,
    )
    db.session.add(job)
    db.session.flush()

    # Run formulation
    colorants, substrate_ks = _load_series_colorants(series_id)
    if not colorants:
        job.status = 'failed'
        db.session.commit()
        return jsonify({'error': 'No bases with spectral data in this series'}), 400

    engine = FormulationEngine()
    results = engine.formulate_multi(
        target_reflectance=target_reflectance,
        target_lab=(lab_l, lab_a, lab_b) if lab_l is not None else None,
        colorants=colorants,
        substrate_ks=substrate_ks,
        num_results=3,
    )

    _save_match_results(job, results)
    job.status = 'completed'

    AuditLog.log(user.id, 'custom_match_cxf', 'custom_match', job.id,
                 details={'series_id': series_id, 'filename': file_info['original_filename']})
    db.session.commit()

    job_dict = job.to_dict(include_results=True)
    if lab_l is not None:
        job_dict['closest_pantone'] = find_closest_pantone(
            (lab_l, lab_a, lab_b), count=5
        )
    return jsonify({'job': job_dict}), 201


def _save_match_results(job, formulation_results):
    """Save formulation results to the database."""
    for rank, result in enumerate(formulation_results, 1):
        if not result.success:
            continue

        match_result = CustomMatchResult(
            job_id=job.id,
            rank=rank,
            predicted_spectral=result.predicted_reflectance.tolist()
            if len(result.predicted_reflectance) > 0 else None,
            predicted_lab_l=float(result.predicted_lab[0]),
            predicted_lab_a=float(result.predicted_lab[1]),
            predicted_lab_b=float(result.predicted_lab[2]),
            delta_e_76=result.delta_e_76,
            delta_e_2000=result.delta_e_2000,
        )
        db.session.add(match_result)
        db.session.flush()

        for comp in result.components:
            mc = CustomMatchComponent(
                result_id=match_result.id,
                base_id=comp.base_id,
                percentage=comp.percentage,
                weight_grams=comp.weight_grams,
            )
            db.session.add(mc)
