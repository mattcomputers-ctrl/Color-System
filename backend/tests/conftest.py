"""Shared test fixtures."""

import os
import pytest

from app import create_app, db as _db
from app.models.user import User, Role


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app('testing')
    return app


@pytest.fixture(scope='function')
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    role = Role(name='admin', description='Admin', permissions='all')
    db.session.add(role)
    db.session.flush()

    user = User(
        email='admin@test.com',
        username='admin',
        first_name='Test',
        last_name='Admin',
        role_id=role.id,
    )
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_headers(app, admin_user):
    """Get JWT auth headers for the admin user."""
    with app.app_context():
        from app.utils.auth import generate_token
        token = generate_token(admin_user)
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
