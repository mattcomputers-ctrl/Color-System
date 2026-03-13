import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Spinner, Badge, Row, Col } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { seriesAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';

function SeriesList() {
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editSeries, setEditSeries] = useState(null);
  const [form, setForm] = useState({ code: '', name: '', description: '', ink_type: 'litho' });
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const loadSeries = async () => {
    try {
      const res = await seriesAPI.list();
      setSeries(res.data.series);
    } catch (err) {
      toast.error('Failed to load ink series');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSeries(); }, []);

  const openModal = (s = null) => {
    if (s) {
      setEditSeries(s);
      setForm({ code: s.code, name: s.name, description: s.description || '', ink_type: s.ink_type || 'litho' });
    } else {
      setEditSeries(null);
      setForm({ code: '', name: '', description: '', ink_type: 'litho' });
    }
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editSeries) {
        await seriesAPI.update(editSeries.id, { name: form.name, description: form.description, ink_type: form.ink_type });
        toast.success('Series updated');
      } else {
        await seriesAPI.create(form);
        toast.success('Ink series created');
      }
      setShowModal(false);
      loadSeries();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to save series');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await seriesAPI.delete(id);
      toast.success('Series deactivated');
      setDeleteConfirm(null);
      loadSeries();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete series');
    }
  };

  if (loading) return <div className="page-spinner"><Spinner animation="border" variant="primary" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <div>
          <h2>Ink Series</h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>
            Manage ink series and their mixing base configurations
          </p>
        </div>
        <Button variant="primary" onClick={() => openModal()}>
          + New Series
        </Button>
      </div>

      <Card>
        <Card.Body className="p-0">
          <Table hover>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Type</th>
                <th style={{ width: 80 }}>Bases</th>
                <th style={{ width: 90 }}>Status</th>
                <th>Created</th>
                <th style={{ width: 160 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {series.map(s => (
                <tr key={s.id}>
                  <td>
                    <Link to={`/series/${s.id}`} className="fw-semibold text-decoration-none">
                      {s.code}
                    </Link>
                  </td>
                  <td>{s.name}</td>
                  <td>
                    <Badge bg={s.ink_type === 'flexo' ? 'info' : 'secondary'} className="fw-normal">
                      {s.ink_type === 'flexo' ? 'Flexo' : 'Litho'}
                    </Badge>
                  </td>
                  <td className="text-center">{s.base_count}</td>
                  <td>
                    <Badge bg={s.is_active ? 'success' : 'secondary'}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="text-muted">{formatDate(s.created_at)}</td>
                  <td>
                    <div className="d-flex gap-2">
                      <Button variant="outline-primary" size="sm" onClick={() => openModal(s)}>
                        Edit
                      </Button>
                      <Button variant="outline-danger" size="sm" onClick={() => setDeleteConfirm(s)}>
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {series.length === 0 && (
                <tr>
                  <td colSpan="7">
                    <div className="empty-state">
                      <h6>No ink series yet</h6>
                      <p>Create your first ink series to start managing mixing bases and formulations.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* Create/Edit Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>{editSeries ? 'Edit Series' : 'New Ink Series'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSave}>
          <Modal.Body>
            <Row className="g-3 mb-3">
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Series Code</Form.Label>
                  <Form.Control
                    value={form.code}
                    onChange={e => setForm({ ...form, code: e.target.value })}
                    placeholder="e.g., UV-OFFSET"
                    required
                    disabled={!!editSeries}
                  />
                  {editSeries && <Form.Text>Code cannot be changed</Form.Text>}
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Ink Type</Form.Label>
                  <Form.Select
                    value={form.ink_type}
                    onChange={e => setForm({ ...form, ink_type: e.target.value })}
                  >
                    <option value="litho">Litho (Opaque)</option>
                    <option value="flexo">Flexo (Translucent)</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., UV Offset Process Series"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea" rows={3}
                value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Optional description..."
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : editSeries ? 'Save Changes' : 'Create Series'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Delete Confirmation */}
      <Modal show={deleteConfirm !== null} onHide={() => setDeleteConfirm(null)} centered size="sm">
        <Modal.Header closeButton><Modal.Title>Confirm Delete</Modal.Title></Modal.Header>
        <Modal.Body>
          Deactivate series <strong>{deleteConfirm?.code}</strong>? This won't delete any data.
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" size="sm" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" size="sm" onClick={() => handleDelete(deleteConfirm.id)}>
            Deactivate
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default SeriesList;
