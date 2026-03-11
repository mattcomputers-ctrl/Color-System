"""Authentication API endpoints."""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from app import db
from app.models.user import User
from app.models.audit import AuditLog
from app.utils.auth import generate_token, login_required, get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403

    user.last_login = datetime.now(timezone.utc)
    AuditLog.log(user.id, 'login', ip_address=request.remote_addr)
    db.session.commit()

    token = generate_token(user)
    return jsonify({
        'token': token,
        'user': user.to_dict(),
    })


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    """Get current authenticated user profile."""
    user = get_current_user()
    return jsonify({'user': user.to_dict()})


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change current user's password."""
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new passwords are required'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400

    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    user.set_password(new_password)
    AuditLog.log(user.id, 'password_changed', ip_address=request.remote_addr)
    db.session.commit()

    return jsonify({'message': 'Password changed successfully'})
