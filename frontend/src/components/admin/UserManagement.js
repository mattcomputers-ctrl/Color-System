import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Badge, Spinner, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { adminAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    email: '', username: '', password: '', first_name: '', last_name: '', role: 'viewer',
  });
  const [saving, setSaving] = useState(false);

  const loadData = async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        adminAPI.listUsers(), adminAPI.listRoles(),
      ]);
      setUsers(usersRes.data.users);
      setRoles(rolesRes.data.roles);
    } catch (err) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await adminAPI.createUser(form);
      toast.success('User created');
      setShowModal(false);
      setForm({ email: '', username: '', password: '', first_name: '', last_name: '', role: 'viewer' });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create user');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (user) => {
    try {
      if (user.is_active) {
        await adminAPI.deactivateUser(user.id);
        toast.success(`User ${user.username} deactivated`);
      } else {
        await adminAPI.updateUser(user.id, { is_active: true });
        toast.success(`User ${user.username} activated`);
      }
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to update user');
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <h2>User Management</h2>
        <Button variant="primary" onClick={() => setShowModal(true)}>+ Add User</Button>
      </div>

      <Card>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr><th>Username</th><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Last Login</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td><strong>{u.username}</strong></td>
                  <td>{u.email}</td>
                  <td>{u.full_name}</td>
                  <td><Badge bg="info">{u.role}</Badge></td>
                  <td><Badge bg={u.is_active ? 'success' : 'secondary'}>{u.is_active ? 'Active' : 'Inactive'}</Badge></td>
                  <td className="text-muted small">{u.last_login ? formatDate(u.last_login) : 'Never'}</td>
                  <td>
                    <Button size="sm" variant={u.is_active ? 'outline-danger' : 'outline-success'}
                      onClick={() => handleToggleActive(u)}>
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton><Modal.Title>Add User</Modal.Title></Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Row>
              <Col><Form.Group className="mb-3"><Form.Label>First Name</Form.Label><Form.Control value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} /></Form.Group></Col>
              <Col><Form.Group className="mb-3"><Form.Label>Last Name</Form.Label><Form.Control value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} /></Form.Group></Col>
            </Row>
            <Form.Group className="mb-3"><Form.Label>Username</Form.Label><Form.Control value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} required /></Form.Group>
            <Form.Group className="mb-3"><Form.Label>Email</Form.Label><Form.Control type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required /></Form.Group>
            <Form.Group className="mb-3"><Form.Label>Password</Form.Label><Form.Control type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required minLength={8} /></Form.Group>
            <Form.Group className="mb-3"><Form.Label>Role</Form.Label>
              <Form.Select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
                {roles.map(r => <option key={r.id} value={r.name}>{r.name} — {r.description}</option>)}
              </Form.Select>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>{saving ? 'Creating...' : 'Create User'}</Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}

export default UserManagement;
