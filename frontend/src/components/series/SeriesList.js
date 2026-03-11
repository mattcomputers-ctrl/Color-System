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
  const [form, setForm] = useState({ code: '', name: '', description: '' });
  const [saving, setSaving] = useState(false);

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

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await seriesAPI.create(form);
      toast.success('Ink series created');
      setShowModal(false);
      setForm({ code: '', name: '', description: '' });
      loadSeries();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create series');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <h2>Ink Series</h2>
        <Button variant="primary" onClick={() => setShowModal(true)}>
          + New Series
        </Button>
      </div>

      <Card>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr>
                <th>Code</th><th>Name</th><th>Bases</th>
                <th>Status</th><th>Created</th>
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
                </tr>
              ))}
              {series.length === 0 && (
                <tr><td colSpan="5" className="text-center text-muted p-4">
                  No ink series yet. Create one to get started.
                </td></tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton><Modal.Title>New Ink Series</Modal.Title></Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Series Code</Form.Label>
              <Form.Control
                value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value })}
                placeholder="e.g., UV-OFFSET"
                required
              />
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
              {saving ? 'Creating...' : 'Create Series'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}

export default SeriesList;
