"""Health check endpoint for monitoring and debugging."""

from flask import Blueprint, jsonify

from app import db

health_bp = Blueprint('health', __name__)


@health_bp.route('', methods=['GET'])
def health_check():
    """Check application and database health.

    No authentication required — this is used by the installer and
    monitoring tools to verify the system is operational.
    """
    status = {'app': 'ok'}

    # Test database connectivity
    try:
        db.session.execute(db.text('SELECT 1'))
        status['database'] = 'ok'
    except Exception as e:
        status['database'] = 'error'
        status['database_error'] = str(e)
        return jsonify(status), 503

    # Check that critical tables exist
    try:
        from app.models.user import User, Role
        role_count = Role.query.count()
        user_count = User.query.count()
        status['roles'] = role_count
        status['users'] = user_count

        if role_count == 0:
            status['warning'] = 'No roles found — seed data may not have loaded'
        if user_count == 0:
            status['warning'] = 'No users found — seed data may not have loaded'
    except Exception as e:
        status['tables'] = 'error'
        status['tables_error'] = str(e)
        return jsonify(status), 503

    return jsonify(status)
