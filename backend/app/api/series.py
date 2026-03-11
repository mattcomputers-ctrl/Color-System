"""Ink Series API endpoints."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.series import InkSeries
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
