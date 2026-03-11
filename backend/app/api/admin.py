"""Admin API endpoints for user management and system administration."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.user import User, Role
from app.models.audit import AuditLog
from app.utils.auth import login_required, role_required, get_current_user

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@role_required('admin')
def list_users():
    """List all users."""
    users = User.query.order_by(User.username).all()
    return jsonify({'users': [u.to_dict() for u in users]})


@admin_bp.route('/users', methods=['POST'])
@role_required('admin')
def create_user():
    """Create a new user."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role_name = data.get('role', 'viewer')

    if not email or not username or not password:
        return jsonify({'error': 'email, username, and password are required'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({'error': f'Role "{role_name}" not found'}), 400

    user = User(
        email=email,
        username=username,
        first_name=data.get('first_name', '').strip() or None,
        last_name=data.get('last_name', '').strip() or None,
        role_id=role.id,
    )
    user.set_password(password)
    db.session.add(user)

    admin = get_current_user()
    AuditLog.log(admin.id, 'create_user', 'user', details={'username': username, 'role': role_name})
    db.session.commit()

    return jsonify({'user': user.to_dict()}), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@role_required('admin')
def update_user(user_id):
    """Update a user's profile."""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if 'first_name' in data:
        user.first_name = data['first_name'].strip() or None
    if 'last_name' in data:
        user.last_name = data['last_name'].strip() or None
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    if 'role' in data:
        role = Role.query.filter_by(name=data['role']).first()
        if role:
            user.role_id = role.id

    if 'password' in data and data['password']:
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        user.set_password(data['password'])

    admin = get_current_user()
    AuditLog.log(admin.id, 'update_user', 'user', user.id)
    db.session.commit()

    return jsonify({'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@role_required('admin')
def deactivate_user(user_id):
    """Deactivate a user account."""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    admin = get_current_user()
    if user.id == admin.id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400

    user.is_active = False
    AuditLog.log(admin.id, 'deactivate_user', 'user', user.id)
    db.session.commit()

    return jsonify({'message': f'User "{user.username}" deactivated'})


@admin_bp.route('/roles', methods=['GET'])
@role_required('admin')
def list_roles():
    """List all roles."""
    roles = Role.query.all()
    return jsonify({'roles': [{'id': r.id, 'name': r.name, 'description': r.description}
                              for r in roles]})


@admin_bp.route('/audit-log', methods=['GET'])
@role_required('admin')
def get_audit_log():
    """Get audit log entries."""
    query = AuditLog.query

    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter_by(user_id=user_id)

    action = request.args.get('action')
    if action:
        query = query.filter_by(action=action)

    entity_type = request.args.get('entity_type')
    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 200)

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'entries': [e.to_dict() for e in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@admin_bp.route('/dashboard-stats', methods=['GET'])
@login_required
def dashboard_stats():
    """Get summary statistics for the dashboard."""
    from app.models.series import InkSeries
    from app.models.base import MixingBase
    from app.models.pantone import PantoneTarget, PantoneFormula
    from app.models.custom_match import CustomMatchJob

    stats = {
        'total_series': InkSeries.query.filter_by(is_active=True).count(),
        'total_bases': MixingBase.query.filter_by(is_active=True).count(),
        'total_pantone_targets': PantoneTarget.query.filter_by(is_active=True).count(),
        'total_pantone_formulas': PantoneFormula.query.filter_by(is_current=True).count(),
        'total_custom_matches': CustomMatchJob.query.count(),
        'recent_formulas': [
            {
                **f.to_dict(include_components=False),
                'target_code': f.target.pantone_code if f.target else None,
                'series_name': f.series.name if f.series else None,
            }
            for f in PantoneFormula.query
                .filter_by(is_current=True)
                .order_by(PantoneFormula.created_at.desc())
                .limit(5)
                .all()
        ],
        'recent_matches': [
            j.to_dict()
            for j in CustomMatchJob.query
                .order_by(CustomMatchJob.created_at.desc())
                .limit(5)
                .all()
        ],
    }
    return jsonify(stats)
