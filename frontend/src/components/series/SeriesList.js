import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Spinner, Badge } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { seriesAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';

function SeriesList() {
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editSeries, setEditSeries] = useState(null);
  const [form, setForm] = useState({ code: '', name: '', description: '' });
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
      setForm({ code: s.code, name: s.name, description: s.description || '' });
    } else {
      setEditSeries(null);
      setForm({ code: '', name: '', description: '' });
    }
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editSeries) {
        await seriesAPI.update(editSeries.id, { name: form.name, description: form.description });
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
      toast.success('Series deleted');
      setDeleteConfirm(null);
      loadSeries();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete series');
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <h2>Ink Series</h2>
        <Button variant="primary" onClick={() => openModal()}>
          + New Series
        </Button>
      </div>

      <Card>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr>
                <th>Code</th><th>Name</th><th>Bases</th>
                <th>Status</th><th>Created</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {series.map(s => (
                <tr key={s.id}>
                  <td><Link to={`/series/${s.id}`}><strong>{s.code}</strong></Link></td>
                  <td>{s.name}</td>
                  <td>{s.base_count}</td>
                  <td>
                    <Badge bg={s.is_active ? 'success' : 'secondary'}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="text-muted small">{formatDate(s.created_at)}</td>
                  <td>
                    <Button variant="outline-primary" size="sm" className="me-1" onClick={() => openModal(s)}>
                      Edit
                    </Button>
                    <Button variant="outline-danger" size="sm" onClick={() => setDeleteConfirm(s)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
              {series.length === 0 && (
                <tr><td colSpan="6" className="text-center text-muted p-4">
                  No ink series yet. Create one to get started.
                </td></tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* Create/Edit Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{editSeries ? 'Edit Series' : 'New Ink Series'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSave}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Series Code</Form.Label>
              <Form.Control
                value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value })}
                placeholder="e.g., UV-OFFSET"
                required
                disabled={!!editSeries}
              />
              {editSeries && <Form.Text className="text-muted">Code cannot be changed</Form.Text>}
            </Form.Group>
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
      <Modal show={deleteConfirm !== null} onHide={() => setDeleteConfirm(null)}>
        <Modal.Header closeButton><Modal.Title>Confirm Delete</Modal.Title></Modal.Header>
        <Modal.Body>
          Are you sure you want to delete series <strong>{deleteConfirm?.code}</strong>?
          This will deactivate the series.
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => handleDelete(deleteConfirm.id)}>
            Delete
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default SeriesList;
