"""Tolerance Profile API endpoints."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.tolerance_profile import ToleranceProfile
from app.models.audit import AuditLog
from app.utils.auth import login_required, role_required, get_current_user

tolerance_bp = Blueprint('tolerance', __name__)


@tolerance_bp.route('', methods=['GET'])
@login_required
def list_profiles():
    """List tolerance profiles."""
    query = ToleranceProfile.query
    if request.args.get('active_only', 'false').lower() == 'true':
        query = query.filter_by(is_active=True)
    profiles = query.order_by(ToleranceProfile.name).all()
    return jsonify({'profiles': [p.to_dict() for p in profiles]})


@tolerance_bp.route('/<int:profile_id>', methods=['GET'])
@login_required
def get_profile(profile_id):
    """Get a single tolerance profile."""
    profile = db.session.get(ToleranceProfile, profile_id)
    if not profile:
        return jsonify({'error': 'Tolerance profile not found'}), 404
    return jsonify({'profile': profile.to_dict()})


@tolerance_bp.route('', methods=['POST'])
@role_required('admin', 'formulator')
def create_profile():
    """Create a new tolerance profile."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    if ToleranceProfile.query.filter_by(name=name).first():
        return jsonify({'error': f'Profile "{name}" already exists'}), 409

    user = get_current_user()

    is_default = bool(data.get('is_default', False))
    if is_default:
        ToleranceProfile.query.filter_by(is_default=True).update({'is_default': False})

    profile = ToleranceProfile(
        name=name,
        description=data.get('description', '').strip() or None,
        customer_name=data.get('customer_name', '').strip() or None,
        de_excellent=float(data.get('de_excellent', 0.5)),
        de_good=float(data.get('de_good', 1.0)),
        de_acceptable=float(data.get('de_acceptable', 2.0)),
        de76_acceptable=float(data.get('de76_acceptable', 3.0)),
        is_default=is_default,
        created_by_id=user.id,
    )
    db.session.add(profile)

    AuditLog.log(user.id, 'create_tolerance_profile', 'tolerance_profile',
                 details={'name': name})
    db.session.commit()

    return jsonify({'profile': profile.to_dict()}), 201


@tolerance_bp.route('/<int:profile_id>', methods=['PUT'])
@role_required('admin', 'formulator')
def update_profile(profile_id):
    """Update a tolerance profile."""
    profile = db.session.get(ToleranceProfile, profile_id)
    if not profile:
        return jsonify({'error': 'Tolerance profile not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if 'name' in data:
        profile.name = data['name'].strip()
    if 'description' in data:
        profile.description = data['description'].strip() or None
    if 'customer_name' in data:
        profile.customer_name = data['customer_name'].strip() or None
    if 'de_excellent' in data:
        profile.de_excellent = float(data['de_excellent'])
    if 'de_good' in data:
        profile.de_good = float(data['de_good'])
    if 'de_acceptable' in data:
        profile.de_acceptable = float(data['de_acceptable'])
    if 'de76_acceptable' in data:
        profile.de76_acceptable = float(data['de76_acceptable'])
    if 'is_default' in data:
        if data['is_default']:
            ToleranceProfile.query.filter_by(is_default=True).update({'is_default': False})
        profile.is_default = bool(data['is_default'])
    if 'is_active' in data:
        profile.is_active = bool(data['is_active'])

    user = get_current_user()
    AuditLog.log(user.id, 'update_tolerance_profile', 'tolerance_profile',
                 profile.id, details=data)
    db.session.commit()

    return jsonify({'profile': profile.to_dict()})


@tolerance_bp.route('/<int:profile_id>', methods=['DELETE'])
@role_required('admin')
def delete_profile(profile_id):
    """Deactivate a tolerance profile."""
    profile = db.session.get(ToleranceProfile, profile_id)
    if not profile:
        return jsonify({'error': 'Tolerance profile not found'}), 404

    profile.is_active = False
    user = get_current_user()
    AuditLog.log(user.id, 'deactivate_tolerance_profile', 'tolerance_profile', profile.id)
    db.session.commit()

    return jsonify({'message': f'Profile "{profile.name}" deactivated'})
