"""Tests for API endpoints."""

import json
import pytest


class TestAuthAPI:
    def test_login_success(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.com',
            'password': 'testpass123',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['user']['username'] == 'admin'

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.com',
            'password': 'wrongpass',
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={'email': 'admin@test.com'})
        assert resp.status_code == 400

    def test_get_me_authenticated(self, client, auth_headers):
        resp = client.get('/api/v1/auth/me', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['user']['username'] == 'admin'

    def test_get_me_unauthenticated(self, client):
        resp = client.get('/api/v1/auth/me')
        assert resp.status_code == 401


class TestSeriesAPI:
    def test_create_series(self, client, auth_headers):
        resp = client.post('/api/v1/series', headers=auth_headers, json={
            'code': 'TEST-SERIES',
            'name': 'Test Series',
            'description': 'A test ink series',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['series']['code'] == 'TEST-SERIES'

    def test_list_series(self, client, auth_headers):
        # Create first
        client.post('/api/v1/series', headers=auth_headers, json={
            'code': 'S1', 'name': 'Series 1'
        })
        resp = client.get('/api/v1/series', headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()['series']) >= 1

    def test_create_duplicate_code(self, client, auth_headers):
        client.post('/api/v1/series', headers=auth_headers, json={
            'code': 'DUP', 'name': 'First'
        })
        resp = client.post('/api/v1/series', headers=auth_headers, json={
            'code': 'DUP', 'name': 'Second'
        })
        assert resp.status_code == 409

    def test_update_series(self, client, auth_headers):
        resp = client.post('/api/v1/series', headers=auth_headers, json={
            'code': 'UPD', 'name': 'Original'
        })
        series_id = resp.get_json()['series']['id']

        resp = client.put(f'/api/v1/series/{series_id}', headers=auth_headers, json={
            'name': 'Updated Name'
        })
        assert resp.status_code == 200
        assert resp.get_json()['series']['name'] == 'Updated Name'


class TestBasesAPI:
    def _create_series(self, client, auth_headers):
        resp = client.post('/api/v1/series', headers=auth_headers, json={
            'code': 'BASE-TEST', 'name': 'Base Test Series'
        })
        return resp.get_json()['series']['id']

    def test_create_base(self, client, auth_headers):
        series_id = self._create_series(client, auth_headers)
        resp = client.post(f'/api/v1/bases/series/{series_id}', headers=auth_headers, json={
            'code': 'Y', 'name': 'Yellow', 'color_index': 'PY 13'
        })
        assert resp.status_code == 201
        assert resp.get_json()['base']['code'] == 'Y'

    def test_add_concentration(self, client, auth_headers):
        series_id = self._create_series(client, auth_headers)
        resp = client.post(f'/api/v1/bases/series/{series_id}', headers=auth_headers, json={
            'code': 'R', 'name': 'Red'
        })
        base_id = resp.get_json()['base']['id']

        resp = client.post(f'/api/v1/bases/{base_id}/concentrations', headers=auth_headers, json={
            'concentration_pct': 100.0, 'label': 'Full Strength'
        })
        assert resp.status_code == 201
        assert resp.get_json()['concentration']['concentration_pct'] == 100.0


class TestDashboard:
    def test_dashboard_stats(self, client, auth_headers):
        resp = client.get('/api/v1/admin/dashboard-stats', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total_series' in data
        assert 'total_bases' in data
