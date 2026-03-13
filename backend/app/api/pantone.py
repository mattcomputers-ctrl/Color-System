"""Pantone formulation API endpoints."""

import logging

import numpy as np
from flask import Blueprint, request, jsonify

from app import db
from app.models.pantone import PantoneTarget, PantoneFormula, PantoneFormulaComponent
from app.models.series import InkSeries
from app.models.base import MixingBase, MixingBaseConcentration, BaseSpectralData
from app.models.upload import UploadedFile
from app.models.audit import AuditLog
from app.services.cxf_parser import CxfParser
from app.services.color_science import (
    spectral_to_lab, reflectance_to_ks, metamerism_index,
    compute_lab_multi_condition, spectral_to_lab_full,
    OBSERVERS, MEASUREMENT_FILTERS,
)
from app.services.formulation_engine import FormulationEngine, ColorantData
from app.utils.auth import login_required, role_required, get_current_user
from app.utils.file_handler import allowed_file, save_upload

logger = logging.getLogger(__name__)
pantone_bp = Blueprint('pantone', __name__)


# --- Pantone Targets ---

@pantone_bp.route('/targets', methods=['GET'])
@login_required
def list_targets():
    """List Pantone targets with optional search."""
    query = PantoneTarget.query
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            db.or_(
                PantoneTarget.pantone_code.ilike(f'%{search}%'),
                PantoneTarget.pantone_name.ilike(f'%{search}%'),
            )
        )
    library = request.args.get('library')
    if library:
        query = query.filter_by(library=library)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 200)

    pagination = query.order_by(PantoneTarget.pantone_code).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'targets': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@pantone_bp.route('/targets', methods=['POST'])
@role_required('admin', 'formulator')
def create_target():
    """Create a Pantone target from LAB values or CXF upload."""
    user = get_current_user()

    # Check if this is a file upload or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        return _create_target_from_cxf(user)
    else:
        return _create_target_from_lab(user)


def _create_target_from_lab(user):
    """Create a Pantone target from manually entered LAB values."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    code = data.get('pantone_code', '').strip()
    if not code:
        return jsonify({'error': 'pantone_code is required'}), 400

    lab_l = data.get('lab_l')
    lab_a = data.get('lab_a')
    lab_b = data.get('lab_b')

    if lab_l is None or lab_a is None or lab_b is None:
        return jsonify({'error': 'lab_l, lab_a, and lab_b are required'}), 400

    library = data.get('library', 'PMS')
    existing = PantoneTarget.query.filter_by(pantone_code=code, library=library).first()
    if existing:
        return jsonify({'error': f'Target {code} already exists in library {library}'}), 409

    target = PantoneTarget(
        pantone_code=code,
        pantone_name=data.get('pantone_name', '').strip() or None,
        library=library,
        lab_l=float(lab_l),
        lab_a=float(lab_a),
        lab_b=float(lab_b),
        source=data.get('source', '').strip() or None,
    )
    db.session.add(target)
    AuditLog.log(user.id, 'create_pantone_target', 'pantone_target',
                 details={'code': code})
    db.session.commit()

    return jsonify({'target': target.to_dict()}), 201


def _create_target_from_cxf(user):
    """Create a Pantone target from an uploaded CXF file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    code = request.form.get('pantone_code', '').strip()
    if not code:
        return jsonify({'error': 'pantone_code is required'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CXF/XML files are allowed'}), 400

    library = request.form.get('library', 'PMS')
    existing = PantoneTarget.query.filter_by(pantone_code=code, library=library).first()
    if existing:
        return jsonify({'error': f'Target {code} already exists in library {library}'}), 409

    file_info = save_upload(file, purpose='pantone_target')
    upload_record = UploadedFile(
        original_filename=file_info['original_filename'],
        stored_filename=file_info['stored_filename'],
        file_type=file_info['file_type'],
        file_size=file_info['file_size'],
        mime_type=file_info['mime_type'],
        checksum_sha256=file_info['checksum_sha256'],
        purpose='pantone_target',
        uploaded_by_id=user.id,
    )
    db.session.add(upload_record)
    db.session.flush()

    parser = CxfParser()
    result = parser.parse_bytes(file_info['content'])
    if not result.success:
        upload_record.status = 'error'
        upload_record.parse_errors = '; '.join(result.errors)
        db.session.commit()
        return jsonify({'error': 'Failed to parse CXF', 'details': result.errors}), 400

    color = result.primary_color
    upload_record.status = 'parsed'

    lab_l, lab_a, lab_b = None, None, None
    spectral = None
    if color.spectral:
        spectral = color.spectral.reflectance
        lab = spectral_to_lab(np.array(spectral))
        lab_l, lab_a, lab_b = float(lab[0]), float(lab[1]), float(lab[2])
    elif color.lab_l is not None:
        lab_l, lab_a, lab_b = color.lab_l, color.lab_a, color.lab_b

    target = PantoneTarget(
        pantone_code=code,
        pantone_name=request.form.get('pantone_name', '').strip() or color.name or None,
        library=library,
        spectral_reflectance=spectral,
        lab_l=lab_l,
        lab_a=lab_a,
        lab_b=lab_b,
        source=request.form.get('source', '').strip() or None,
        uploaded_file_id=upload_record.id,
    )
    db.session.add(target)
    AuditLog.log(user.id, 'create_pantone_target', 'pantone_target',
                 details={'code': code, 'from_cxf': True})
    db.session.commit()

    return jsonify({'target': target.to_dict()}), 201


# --- Pantone Formulas ---

@pantone_bp.route('/formulas', methods=['GET'])
@login_required
def list_formulas():
    """List Pantone formulas with filters."""
    query = PantoneFormula.query

    series_id = request.args.get('series_id', type=int)
    if series_id:
        query = query.filter_by(series_id=series_id)

    target_id = request.args.get('target_id', type=int)
    if target_id:
        query = query.filter_by(target_id=target_id)

    current_only = request.args.get('current_only', 'true').lower() == 'true'
    if current_only:
        query = query.filter_by(is_current=True)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    search = request.args.get('search', '').strip()
    if search:
        query = query.join(PantoneTarget).filter(
            PantoneTarget.pantone_code.ilike(f'%{search}%')
        )

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 200)

    pagination = query.order_by(PantoneFormula.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    formulas = []
    for f in pagination.items:
        fd = f.to_dict()
        fd['target_code'] = f.target.pantone_code if f.target else None
        fd['series_name'] = f.series.name if f.series else None
        formulas.append(fd)

    return jsonify({
        'formulas': formulas,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@pantone_bp.route('/formulas/<int:formula_id>', methods=['GET'])
@login_required
def get_formula(formula_id):
    """Get a single Pantone formula with full details."""
    formula = db.session.get(PantoneFormula, formula_id)
    if not formula:
        return jsonify({'error': 'Formula not found'}), 404

    fd = formula.to_dict()
    fd['target'] = formula.target.to_dict() if formula.target else None
    fd['series_name'] = formula.series.name if formula.series else None

    # Get observer and filter from query params
    observer = request.args.get('observer', '2')
    measurement_filter = request.args.get('filter')
    if observer not in OBSERVERS:
        observer = '2'
    if measurement_filter and measurement_filter not in MEASUREMENT_FILTERS:
        measurement_filter = None

    # Compute metamerism if both target and predicted spectral data exist
    target = formula.target
    if (target and target.spectral_reflectance and formula.predicted_spectral):
        try:
            target_R = np.array(target.spectral_reflectance)
            predicted_R = np.array(formula.predicted_spectral)
            fd['metamerism'] = metamerism_index(
                target_R, predicted_R,
                observer=observer, measurement_filter=measurement_filter
            )
            # Multi-condition LAB for the predicted color
            fd['multi_condition_lab'] = compute_lab_multi_condition(predicted_R)
        except Exception:
            pass

    # Recompute LAB under requested observer/filter if spectral data exists
    if formula.predicted_spectral and (observer != '2' or measurement_filter):
        try:
            predicted_R = np.array(formula.predicted_spectral)
            lab = spectral_to_lab_full(predicted_R, 'D50', observer, measurement_filter)
            fd['predicted_lab_custom'] = {
                'L': round(lab[0], 2), 'a': round(lab[1], 2), 'b': round(lab[2], 2),
                'observer': observer, 'filter': measurement_filter,
            }
        except Exception:
            pass

    return jsonify({'formula': fd})


@pantone_bp.route('/formulate', methods=['POST'])
@role_required('admin', 'formulator')
def formulate():
    """Generate a Pantone formula.

    Request body:
        target_id: int — Pantone target to formulate
        series_id: int — Ink series to use
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    target_id = data.get('target_id')
    series_id = data.get('series_id')

    if not target_id or not series_id:
        return jsonify({'error': 'target_id and series_id are required'}), 400

    target = db.session.get(PantoneTarget, target_id)
    if not target:
        return jsonify({'error': 'Pantone target not found'}), 404

    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    # Get target color data
    target_reflectance = None
    target_lab = None
    if target.spectral_reflectance:
        target_reflectance = np.array(target.spectral_reflectance)
    elif target.lab_l is not None:
        target_lab = (target.lab_l, target.lab_a, target.lab_b)
    else:
        return jsonify({'error': 'Target has no color data'}), 400

    # Load colorant data from bases in this series
    substrate_id = data.get('substrate_id')
    colorants, substrate_ks = _load_series_colorants(series_id, substrate_id=substrate_id)
    if not colorants:
        return jsonify({'error': 'No bases with spectral data in this series'}), 400

    # Run formulation
    engine = FormulationEngine()
    result = engine.formulate(
        target_reflectance=target_reflectance,
        target_lab=target_lab,
        colorants=colorants,
        substrate_ks=substrate_ks,
    )

    if not result.success:
        return jsonify({'error': result.error_message}), 400

    # Save formula
    user = get_current_user()

    # Get next version
    existing = PantoneFormula.query.filter_by(
        target_id=target_id, series_id=series_id, is_current=True
    ).first()
    next_version = (existing.version + 1) if existing else 1
    if existing:
        existing.is_current = False

    formula = PantoneFormula(
        target_id=target_id,
        series_id=series_id,
        version=next_version,
        predicted_spectral=result.predicted_reflectance.tolist(),
        predicted_lab_l=float(result.predicted_lab[0]),
        predicted_lab_a=float(result.predicted_lab[1]),
        predicted_lab_b=float(result.predicted_lab[2]),
        delta_e_76=result.delta_e_76,
        delta_e_2000=result.delta_e_2000,
        generated_by_id=user.id,
        is_current=True,
    )
    db.session.add(formula)
    db.session.flush()

    for comp in result.components:
        fc = PantoneFormulaComponent(
            formula_id=formula.id,
            base_id=comp.base_id,
            percentage=comp.percentage,
            weight_grams=comp.weight_grams,
        )
        db.session.add(fc)

    AuditLog.log(
        user.id, 'generate_pantone_formula', 'pantone_formula', formula.id,
        details={
            'target_code': target.pantone_code,
            'series_code': series.code,
            'version': next_version,
            'delta_e_2000': result.delta_e_2000,
        }
    )
    db.session.commit()

    fd = formula.to_dict()
    fd['target'] = target.to_dict()
    fd['series_name'] = series.name
    return jsonify({'formula': fd}), 201


@pantone_bp.route('/formulate-all', methods=['POST'])
@role_required('admin', 'formulator')
def formulate_all():
    """Generate formulas for ALL Pantone targets in a given series.

    Request body:
        series_id: int — Ink series to use
        library: str (optional) — Filter targets by library (default: all)
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    series_id = data.get('series_id')
    if not series_id:
        return jsonify({'error': 'series_id is required'}), 400

    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    # Load colorants once for the whole batch
    substrate_id = data.get('substrate_id')
    colorants, substrate_ks = _load_series_colorants(series_id, substrate_id=substrate_id)
    if not colorants:
        return jsonify({'error': 'No bases with spectral data in this series'}), 400

    # Get all active targets
    query = PantoneTarget.query.filter_by(is_active=True)
    library = data.get('library')
    if library:
        query = query.filter_by(library=library)
    targets = query.all()

    if not targets:
        return jsonify({'error': 'No Pantone targets found'}), 400

    user = get_current_user()
    engine = FormulationEngine()

    results = []
    succeeded = 0
    failed = 0

    for target in targets:
        target_reflectance = None
        target_lab = None
        if target.spectral_reflectance:
            target_reflectance = np.array(target.spectral_reflectance)
        elif target.lab_l is not None:
            target_lab = (target.lab_l, target.lab_a, target.lab_b)
        else:
            failed += 1
            continue

        try:
            result = engine.formulate(
                target_reflectance=target_reflectance,
                target_lab=target_lab,
                colorants=colorants,
                substrate_ks=substrate_ks,
            )
        except Exception as e:
            logger.warning(f'Formulation failed for {target.pantone_code}: {e}')
            failed += 1
            continue

        if not result.success:
            failed += 1
            continue

        # Get next version
        existing = PantoneFormula.query.filter_by(
            target_id=target.id, series_id=series_id, is_current=True
        ).first()
        next_version = (existing.version + 1) if existing else 1
        if existing:
            existing.is_current = False

        formula = PantoneFormula(
            target_id=target.id,
            series_id=series_id,
            version=next_version,
            predicted_spectral=result.predicted_reflectance.tolist(),
            predicted_lab_l=float(result.predicted_lab[0]),
            predicted_lab_a=float(result.predicted_lab[1]),
            predicted_lab_b=float(result.predicted_lab[2]),
            delta_e_76=result.delta_e_76,
            delta_e_2000=result.delta_e_2000,
            generated_by_id=user.id,
            is_current=True,
        )
        db.session.add(formula)
        db.session.flush()

        for comp in result.components:
            fc = PantoneFormulaComponent(
                formula_id=formula.id,
                base_id=comp.base_id,
                percentage=comp.percentage,
                weight_grams=comp.weight_grams,
            )
            db.session.add(fc)

        succeeded += 1
        results.append({
            'target_code': target.pantone_code,
            'delta_e_2000': result.delta_e_2000,
            'formula_id': formula.id,
        })

    AuditLog.log(
        user.id, 'bulk_formulate_pantone', 'pantone_formula',
        details={
            'series_code': series.code,
            'total_targets': len(targets),
            'succeeded': succeeded,
            'failed': failed,
        }
    )
    db.session.commit()

    return jsonify({
        'message': f'Generated {succeeded} formulas ({failed} failed)',
        'succeeded': succeeded,
        'failed': failed,
        'total': len(targets),
        'results': results,
    }), 201


@pantone_bp.route('/formulas/<int:formula_id>/approve', methods=['POST'])
@role_required('admin', 'formulator')
def approve_formula(formula_id):
    """Approve a generated Pantone formula."""
    from datetime import datetime, timezone

    formula = db.session.get(PantoneFormula, formula_id)
    if not formula:
        return jsonify({'error': 'Formula not found'}), 404

    user = get_current_user()
    formula.status = 'approved'
    formula.approved_by_id = user.id
    formula.approved_at = datetime.now(timezone.utc)

    data = request.get_json() or {}
    if 'notes' in data:
        formula.notes = data['notes']

    AuditLog.log(user.id, 'approve_pantone_formula', 'pantone_formula', formula.id)
    db.session.commit()

    return jsonify({'formula': formula.to_dict()})


def _load_series_colorants(series_id, substrate_id=None):
    """Load colorant data for all active bases in a series.

    Args:
        series_id: The ink series to load bases from.
        substrate_id: Optional substrate ID. If provided, its K/S values are used
            as the substrate instead of auto-detecting from white bases.

    Returns:
        Tuple of (list[ColorantData], substrate_ks).
        substrate_ks is derived from the selected substrate, the first white base,
        or a default white if none found.
    """
    from app.models.substrate import Substrate

    bases = MixingBase.query.filter_by(series_id=series_id, is_active=True).all()
    colorants = []
    substrate_ks = None

    # Use explicit substrate if provided
    if substrate_id:
        substrate = db.session.get(Substrate, substrate_id)
        if substrate and substrate.ks_values:
            substrate_ks = np.array(substrate.ks_values)

    for base in bases:
        # Use the highest concentration level with spectral data
        conc = (MixingBaseConcentration.query
                .filter_by(base_id=base.id, is_active=True)
                .order_by(MixingBaseConcentration.concentration_pct.desc())
                .first())
        if not conc:
            continue

        spectral = conc.current_spectral
        if not spectral or not spectral.ks_values:
            continue

        ks = np.array(spectral.ks_values)

        # Detect substrate/white base only if no explicit substrate was provided
        if substrate_ks is None:
            code_lower = base.code.lower()
            is_white = any(w in code_lower for w in ['white', 'transparent', 'substrate', 'tl', 'tw'])
            if is_white:
                substrate_ks = ks
                # Still include white as a colorant (it's part of the formula)

        colorants.append(ColorantData(
            base_id=base.id,
            code=base.code,
            name=base.name,
            ks_spectrum=ks,
            concentration_pct=conc.concentration_pct,
        ))

    # Default substrate if no white base found
    if substrate_ks is None:
        substrate_ks = reflectance_to_ks(np.full(43, 0.9))

    # Subtract substrate K/S from each colorant to get net colorant contribution
    for c in colorants:
        c.ks_spectrum = np.maximum(c.ks_spectrum - substrate_ks, 0.0)

    return colorants, substrate_ks
