import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Card, Table, Button, Modal, Form, Spinner, Badge, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { seriesAPI, basesAPI } from '../../services/api';
import { labToApproxHex, formatDate } from '../../utils/helpers';

function SeriesDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [series, setSeries] = useState(null);
  const [bases, setBases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showBaseModal, setShowBaseModal] = useState(false);
  const [editBase, setEditBase] = useState(null);
  const [baseForm, setBaseForm] = useState({ code: '', name: '', color_index: '', notes: '' });
  const [saving, setSaving] = useState(false);
  const [showEditSeries, setShowEditSeries] = useState(false);
  const [seriesForm, setSeriesForm] = useState({ name: '', description: '' });
  const [deleteConfirm, setDeleteConfirm] = useState(null); // 'series' | base_id | null

  const loadData = async () => {
    try {
      const [seriesRes, basesRes] = await Promise.all([
        seriesAPI.get(id),
        basesAPI.listBySeries(id, { include_concentrations: 'true' }),
      ]);
      setSeries(seriesRes.data.series);
      setBases(basesRes.data.bases);
    } catch (err) {
      toast.error('Failed to load series data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [id]);

  // --- Base CRUD ---
  const openBaseModal = (base = null) => {
    if (base) {
      setEditBase(base);
      setBaseForm({ code: base.code, name: base.name, color_index: base.color_index || '', notes: base.notes || '' });
    } else {
      setEditBase(null);
      setBaseForm({ code: '', name: '', color_index: '', notes: '' });
    }
    setShowBaseModal(true);
  };

  const handleSaveBase = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editBase) {
        await basesAPI.update(editBase.id, baseForm);
        toast.success('Base updated');
      } else {
        await basesAPI.create(id, baseForm);
        toast.success('Mixing base created');
      }
      setShowBaseModal(false);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to save base');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBase = async (baseId) => {
    try {
      await basesAPI.delete(baseId);
      toast.success('Base deleted');
      setDeleteConfirm(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete base');
    }
  };

  // --- Series CRUD ---
  const openEditSeries = () => {
    setSeriesForm({ name: series.name, description: series.description || '' });
    setShowEditSeries(true);
  };

  const handleUpdateSeries = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await seriesAPI.update(id, seriesForm);
      toast.success('Series updated');
      setShowEditSeries(false);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to update series');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSeries = async () => {
    try {
      await seriesAPI.delete(id);
      toast.success('Series deleted');
      navigate('/series');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete series');
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;
  if (!series) return <p>Series not found.</p>;

  return (
    <div>
      <div className="page-header">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-1">
            <li className="breadcrumb-item"><Link to="/series">Ink Series</Link></li>
            <li className="breadcrumb-item active">{series.code}</li>
          </ol>
        </nav>
        <div className="d-flex justify-content-between align-items-center">
          <h2>{series.name}</h2>
          <div>
            <Button variant="outline-primary" size="sm" className="me-2" onClick={openEditSeries}>
              Edit Series
            </Button>
            <Button variant="outline-danger" size="sm" onClick={() => setDeleteConfirm('series')}>
              Delete Series
            </Button>
          </div>
        </div>
        {series.description && <p className="text-muted">{series.description}</p>}
      </div>

      <Row className="mb-3">
        <Col>
          <Card className="stat-card p-3">
            <div className="stat-value">{bases.length}</div>
            <div className="stat-label">Mixing Bases</div>
          </Card>
        </Col>
        <Col>
          <Card className="stat-card p-3">
            <div className="stat-value">
              {bases.filter(b => b.concentrations?.some(c => c.has_spectral_data)).length}
            </div>
            <div className="stat-label">With Spectral Data</div>
          </Card>
        </Col>
      </Row>

      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>Mixing Bases</strong>
          <Button variant="primary" size="sm" onClick={() => openBaseModal()}>
            + Add Base
          </Button>
        </Card.Header>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr>
                <th>Color</th><th>Code</th><th>Name</th>
                <th>Color Index</th><th>Concentrations</th>
                <th>LAB</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {bases.map(b => {
                const primaryConc = b.concentrations?.find(c => c.has_spectral_data);
                const lab = primaryConc?.lab_values;
                return (
                  <tr key={b.id}>
                    <td>
                      <div
                        className="color-swatch"
                        style={{ backgroundColor: lab ? labToApproxHex(lab.L, lab.a, lab.b) : '#ccc' }}
                      />
                    </td>
                    <td><Link to={`/bases/${b.id}`}><strong>{b.code}</strong></Link></td>
                    <td>{b.name}</td>
                    <td className="text-muted">{b.color_index || '—'}</td>
                    <td>{b.concentration_count}</td>
                    <td className="small">
                      {lab ? `L*${lab.L.toFixed(1)} a*${lab.a.toFixed(1)} b*${lab.b.toFixed(1)}` : '—'}
                    </td>
                    <td>
                      <Badge bg={b.is_active ? 'success' : 'secondary'}>
                        {b.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td>
                      <Button variant="outline-primary" size="sm" className="me-1" onClick={() => openBaseModal(b)}>
                        Edit
                      </Button>
                      <Button variant="outline-danger" size="sm" onClick={() => setDeleteConfirm(b.id)}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                );
              })}
              {bases.length === 0 && (
                <tr><td colSpan="8" className="text-center text-muted p-4">
                  No mixing bases yet. Add one to get started.
                </td></tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* Add/Edit Base Modal */}
      <Modal show={showBaseModal} onHide={() => setShowBaseModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{editBase ? 'Edit Mixing Base' : 'Add Mixing Base'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveBase}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Base Code</Form.Label>
              <Form.Control
                value={baseForm.code}
                onChange={e => setBaseForm({ ...baseForm, code: e.target.value })}
                placeholder="e.g., Y, R, B, BK"
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                value={baseForm.name}
                onChange={e => setBaseForm({ ...baseForm, name: e.target.value })}
                placeholder="e.g., Yellow, Warm Red"
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Color Index (optional)</Form.Label>
              <Form.Control
                value={baseForm.color_index}
                onChange={e => setBaseForm({ ...baseForm, color_index: e.target.value })}
                placeholder="e.g., PY 13, PB 15:3"
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Notes</Form.Label>
              <Form.Control
                as="textarea" rows={2}
                value={baseForm.notes}
                onChange={e => setBaseForm({ ...baseForm, notes: e.target.value })}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowBaseModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : editBase ? 'Save Changes' : 'Add Base'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Edit Series Modal */}
      <Modal show={showEditSeries} onHide={() => setShowEditSeries(false)}>
        <Modal.Header closeButton><Modal.Title>Edit Series</Modal.Title></Modal.Header>
        <Form onSubmit={handleUpdateSeries}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                value={seriesForm.name}
                onChange={e => setSeriesForm({ ...seriesForm, name: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea" rows={3}
                value={seriesForm.description}
                onChange={e => setSeriesForm({ ...seriesForm, description: e.target.value })}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEditSeries(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal show={deleteConfirm !== null} onHide={() => setDeleteConfirm(null)}>
        <Modal.Header closeButton><Modal.Title>Confirm Delete</Modal.Title></Modal.Header>
        <Modal.Body>
          {deleteConfirm === 'series' ? (
            <p>Are you sure you want to delete series <strong>{series.code}</strong>? This will deactivate the series and all its bases.</p>
          ) : (
            <p>Are you sure you want to delete base <strong>{bases.find(b => b.id === deleteConfirm)?.code}</strong>? This will permanently remove the base and all its spectral data.</p>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button
            variant="danger"
            onClick={() => deleteConfirm === 'series' ? handleDeleteSeries() : handleDeleteBase(deleteConfirm)}
          >
            Delete
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default SeriesDetail;
