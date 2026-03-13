import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Spinner, Badge, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { toleranceAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';

function ToleranceProfiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editProfile, setEditProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: '', description: '', customer_name: '',
    de_excellent: 0.5, de_good: 1.0, de_acceptable: 2.0,
    de76_acceptable: 3.0, is_default: false,
  });

  const loadProfiles = async () => {
    try {
      const res = await toleranceAPI.list();
      setProfiles(res.data.profiles);
    } catch {
      toast.error('Failed to load tolerance profiles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadProfiles(); }, []);

  const openModal = (p = null) => {
    if (p) {
      setEditProfile(p);
      setForm({
        name: p.name, description: p.description || '',
        customer_name: p.customer_name || '',
        de_excellent: p.de_excellent, de_good: p.de_good,
        de_acceptable: p.de_acceptable, de76_acceptable: p.de76_acceptable || 3.0,
        is_default: p.is_default,
      });
    } else {
      setEditProfile(null);
      setForm({
        name: '', description: '', customer_name: '',
        de_excellent: 0.5, de_good: 1.0, de_acceptable: 2.0,
        de76_acceptable: 3.0, is_default: false,
      });
    }
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const data = {
        ...form,
        de_excellent: parseFloat(form.de_excellent),
        de_good: parseFloat(form.de_good),
        de_acceptable: parseFloat(form.de_acceptable),
        de76_acceptable: parseFloat(form.de76_acceptable),
      };
      if (editProfile) {
        await toleranceAPI.update(editProfile.id, data);
        toast.success('Profile updated');
      } else {
        await toleranceAPI.create(data);
        toast.success('Profile created');
      }
      setShowModal(false);
      loadProfiles();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <h2>Tolerance Profiles</h2>
        <Button variant="primary" onClick={() => openModal()}>+ New Profile</Button>
      </div>

      <Card>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr>
                <th>Name</th><th>Customer</th>
                <th>Excellent</th><th>Good</th><th>Acceptable</th>
                <th>Default</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map(p => (
                <tr key={p.id}>
                  <td><strong>{p.name}</strong></td>
                  <td className="text-muted">{p.customer_name || '—'}</td>
                  <td><Badge bg="success">&le; {p.de_excellent}</Badge></td>
                  <td><Badge bg="info">&le; {p.de_good}</Badge></td>
                  <td><Badge bg="warning" text="dark">&le; {p.de_acceptable}</Badge></td>
                  <td>{p.is_default && <Badge bg="primary">Default</Badge>}</td>
                  <td>
                    <Badge bg={p.is_active ? 'success' : 'secondary'}>
                      {p.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td>
                    <Button variant="outline-primary" size="sm" onClick={() => openModal(p)}>
                      Edit
                    </Button>
                  </td>
                </tr>
              ))}
              {profiles.length === 0 && (
                <tr><td colSpan="8" className="text-center text-muted p-4">
                  No tolerance profiles yet. Create one to define custom dE thresholds.
                </td></tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{editProfile ? 'Edit Profile' : 'New Tolerance Profile'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSave}>
          <Modal.Body>
            <Row className="mb-3">
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Profile Name</Form.Label>
                  <Form.Control
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g., Standard Litho, Tight Match"
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Customer Name</Form.Label>
                  <Form.Control
                    value={form.customer_name}
                    onChange={e => setForm({ ...form, customer_name: e.target.value })}
                    placeholder="Optional"
                  />
                </Form.Group>
              </Col>
            </Row>
            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea" rows={2}
                value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })}
              />
            </Form.Group>
            <h6>dE2000 Thresholds</h6>
            <Row className="mb-3">
              <Col md={4}>
                <Form.Group>
                  <Form.Label>Excellent (dE &le;)</Form.Label>
                  <Form.Control
                    type="number" step="0.1" min="0"
                    value={form.de_excellent}
                    onChange={e => setForm({ ...form, de_excellent: e.target.value })}
                  />
                  <Form.Text className="text-muted">Best match quality</Form.Text>
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label>Good (dE &le;)</Form.Label>
                  <Form.Control
                    type="number" step="0.1" min="0"
                    value={form.de_good}
                    onChange={e => setForm({ ...form, de_good: e.target.value })}
                  />
                  <Form.Text className="text-muted">Acceptable for most work</Form.Text>
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label>Acceptable (dE &le;)</Form.Label>
                  <Form.Control
                    type="number" step="0.1" min="0"
                    value={form.de_acceptable}
                    onChange={e => setForm({ ...form, de_acceptable: e.target.value })}
                  />
                  <Form.Text className="text-muted">Maximum tolerance</Form.Text>
                </Form.Group>
              </Col>
            </Row>
            <Form.Check
              type="checkbox"
              label="Set as default profile"
              checked={form.is_default}
              onChange={e => setForm({ ...form, is_default: e.target.checked })}
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : editProfile ? 'Save Changes' : 'Create Profile'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}

export default ToleranceProfiles;
