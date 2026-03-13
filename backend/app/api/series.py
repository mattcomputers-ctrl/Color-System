"""Ink Series API endpoints."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.series import InkSeries, SubstrateSeriesAssociation
from app.models.substrate import Substrate
from app.models.audit import AuditLog
from app.utils.auth import login_required, role_required, get_current_user

series_bp = Blueprint('series', __name__)


@series_bp.route('', methods=['GET'])
@login_required
def list_series():
    """List all ink series."""
    query = InkSeries.query
    if request.args.get('active_only', 'false').lower() == 'true':
        query = query.filter_by(is_active=True)

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            db.or_(
                InkSeries.code.ilike(f'%{search}%'),
                InkSeries.name.ilike(f'%{search}%'),
            )
        )

    series = query.order_by(InkSeries.name).all()
    return jsonify({'series': [s.to_dict() for s in series]})


@series_bp.route('/<int:series_id>', methods=['GET'])
@login_required
def get_series(series_id):
    """Get a single ink series."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404
    return jsonify({'series': series.to_dict()})


@series_bp.route('', methods=['POST'])
@role_required('admin', 'formulator')
def create_series():
    """Create a new ink series."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    code = data.get('code', '').strip()
    name = data.get('name', '').strip()

    if not code or not name:
        return jsonify({'error': 'Code and name are required'}), 400

    if InkSeries.query.filter_by(code=code).first():
        return jsonify({'error': f'Series code "{code}" already exists'}), 409

    user = get_current_user()
    series = InkSeries(
        code=code,
        name=name,
        description=data.get('description', '').strip(),
        ink_type=data.get('ink_type', 'litho').strip(),
        created_by_id=user.id,
    )
    db.session.add(series)
    AuditLog.log(user.id, 'create_series', 'series', details={'code': code, 'name': name})
    db.session.commit()

    return jsonify({'series': series.to_dict()}), 201


@series_bp.route('/<int:series_id>', methods=['PUT'])
@role_required('admin', 'formulator')
def update_series(series_id):
    """Update an ink series."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if 'name' in data:
        series.name = data['name'].strip()
    if 'description' in data:
        series.description = data['description'].strip()
    if 'ink_type' in data:
        series.ink_type = data['ink_type'].strip()
    if 'is_active' in data:
        series.is_active = bool(data['is_active'])

    user = get_current_user()
    AuditLog.log(user.id, 'update_series', 'series', series.id, details=data)
    db.session.commit()

    return jsonify({'series': series.to_dict()})


@series_bp.route('/<int:series_id>', methods=['DELETE'])
@role_required('admin')
def delete_series(series_id):
    """Soft-delete an ink series (deactivate)."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    series.is_active = False
    user = get_current_user()
    AuditLog.log(user.id, 'deactivate_series', 'series', series.id)
    db.session.commit()

    return jsonify({'message': f'Series "{series.code}" deactivated'})


# --- Substrate-Series Associations ---

@series_bp.route('/<int:series_id>/substrates', methods=['GET'])
@login_required
def list_series_substrates(series_id):
    """List substrates associated with a series."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    assocs = SubstrateSeriesAssociation.query.filter_by(series_id=series_id).all()
    return jsonify({'substrates': [a.to_dict() for a in assocs]})


@series_bp.route('/<int:series_id>/substrates', methods=['POST'])
@role_required('admin', 'formulator')
def add_series_substrate(series_id):
    """Associate a substrate with a series."""
    series = db.session.get(InkSeries, series_id)
    if not series:
        return jsonify({'error': 'Ink series not found'}), 404

    data = request.get_json()
    substrate_id = data.get('substrate_id')
    if not substrate_id:
        return jsonify({'error': 'substrate_id is required'}), 400

    substrate = db.session.get(Substrate, substrate_id)
    if not substrate:
        return jsonify({'error': 'Substrate not found'}), 404

    existing = SubstrateSeriesAssociation.query.filter_by(
        series_id=series_id, substrate_id=substrate_id
    ).first()
    if existing:
        return jsonify({'error': 'Substrate already associated with this series'}), 409

    is_default = bool(data.get('is_default', False))

    # If setting as default, clear other defaults
    if is_default:
        SubstrateSeriesAssociation.query.filter_by(
            series_id=series_id, is_default=True
        ).update({'is_default': False})

    assoc = SubstrateSeriesAssociation(
        series_id=series_id,
        substrate_id=substrate_id,
        is_default=is_default,
    )
    db.session.add(assoc)
    db.session.commit()

    return jsonify({'association': assoc.to_dict()}), 201


@series_bp.route('/<int:series_id>/substrates/<int:assoc_id>', methods=['PUT'])
@role_required('admin', 'formulator')
def update_series_substrate(series_id, assoc_id):
    """Update a substrate-series association (e.g., set as default)."""
    assoc = db.session.get(SubstrateSeriesAssociation, assoc_id)
    if not assoc or assoc.series_id != series_id:
        return jsonify({'error': 'Association not found'}), 404

    data = request.get_json()
    if 'is_default' in data and data['is_default']:
        SubstrateSeriesAssociation.query.filter_by(
            series_id=series_id, is_default=True
        ).update({'is_default': False})
        assoc.is_default = True
    elif 'is_default' in data:
        assoc.is_default = False

    db.session.commit()
    return jsonify({'association': assoc.to_dict()})


@series_bp.route('/<int:series_id>/substrates/<int:assoc_id>', methods=['DELETE'])
@role_required('admin', 'formulator')
def remove_series_substrate(series_id, assoc_id):
    """Remove a substrate-series association."""
    assoc = db.session.get(SubstrateSeriesAssociation, assoc_id)
    if not assoc or assoc.series_id != series_id:
        return jsonify({'error': 'Association not found'}), 404

    db.session.delete(assoc)
    db.session.commit()
    return jsonify({'message': 'Substrate removed from series'})
