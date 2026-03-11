"""Authentication and authorization utilities."""

import functools
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, request, jsonify, g

from app.models.user import User


def generate_token(user: User) -> str:
    """Generate a JWT access token for a user."""
    expires = datetime.now(timezone.utc) + timedelta(
        seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    )
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role.name if user.role else None,
        'exp': expires,
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])


def get_current_user() -> User | None:
    """Get the current authenticated user from the request."""
    if hasattr(g, '_current_user'):
        return g._current_user

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]
    try:
        payload = decode_token(token)
        from app import db
        user = db.session.get(User, payload['user_id'])
        if user and user.is_active:
            g._current_user = user
            return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass

    return None


def login_required(f):
    """Decorator: require valid JWT authentication."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Decorator: require the user to have one of the specified roles."""
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return jsonify({'error': 'Authentication required'}), 401
            if user.role.name not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
