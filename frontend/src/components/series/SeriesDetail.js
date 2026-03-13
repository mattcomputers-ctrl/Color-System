import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Card, Table, Button, Modal, Form, Spinner, Badge, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { seriesAPI, basesAPI, substratesAPI } from '../../services/api';
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
  const [seriesForm, setSeriesForm] = useState({ name: '', description: '', ink_type: 'litho' });
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [substrateAssocs, setSubstrateAssocs] = useState([]);
  const [allSubstrates, setAllSubstrates] = useState([]);
  const [showSubstrateModal, setShowSubstrateModal] = useState(false);
  const [selectedSubstrate, setSelectedSubstrate] = useState('');

  const loadData = async () => {
    try {
      const [seriesRes, basesRes, assocRes, subsRes] = await Promise.all([
        seriesAPI.get(id),
        basesAPI.listBySeries(id, { include_concentrations: 'true' }),
        seriesAPI.listSubstrates(id),
        substratesAPI.list({ active_only: 'true' }),
      ]);
      setSeries(seriesRes.data.series);
      setBases(basesRes.data.bases);
      setSubstrateAssocs(assocRes.data.substrates);
      setAllSubstrates(subsRes.data.substrates);
    } catch (err) {
      toast.error('Failed to load series data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [id]);

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

  const openEditSeries = () => {
    setSeriesForm({ name: series.name, description: series.description || '', ink_type: series.ink_type || 'litho' });
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
      toast.success('Series deactivated');
      navigate('/series');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete series');
    }
  };

  if (loading) return <div className="page-spinner"><Spinner animation="border" variant="primary" /></div>;
  if (!series) return (
    <div className="empty-state">
      <h6>Series not found</h6>
      <p>The ink series you're looking for doesn't exist.</p>
      <Link to="/series" className="btn btn-primary btn-sm mt-2">Back to Series</Link>
    </div>
  );

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-2">
            <li className="breadcrumb-item"><Link to="/series">Ink Series</Link></li>
            <li className="breadcrumb-item active">{series.code}</li>
          </ol>
        </nav>
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <h2 className="mb-1">{series.name}</h2>
            <div className="d-flex align-items-center gap-2">
              <Badge bg={series.ink_type === 'flexo' ? 'info' : 'secondary'}>
                {series.ink_type === 'flexo' ? 'Flexo' : 'Litho'}
              </Badge>
              {series.description && (
                <span className="text-muted" style={{ fontSize: '0.875rem' }}>{series.description}</span>
              )}
            </div>
          </div>
          <div className="d-flex gap-2">
            <Button variant="outline-primary" size="sm" onClick={openEditSeries}>
              Edit Series
            </Button>
            <Button variant="outline-danger" size="sm" onClick={() => setDeleteConfirm('series')}>
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <Row className="g-3 mb-4">
        <Col xs={6} md={3}>
          <Card className="stat-card">
            <div className="stat-value">{bases.length}</div>
            <div className="stat-label">Mixing Bases</div>
          </Card>
        </Col>
        <Col xs={6} md={3}>
          <Card className="stat-card">
            <div className="stat-value">
              {bases.filter(b => b.concentrations?.some(c => c.has_spectral_data)).length}
            </div>
            <div className="stat-label">With Spectral Data</div>
          </Card>
        </Col>
        <Col xs={6} md={3}>
          <Card className="stat-card">
            <div className="stat-value">{substrateAssocs.length}</div>
            <div className="stat-label">Substrates</div>
          </Card>
        </Col>
        <Col xs={6} md={3}>
          <Card className="stat-card">
            <div className="stat-value">
              {bases.reduce((sum, b) => sum + (b.concentration_count || 0), 0)}
            </div>
            <div className="stat-label">Concentrations</div>
          </Card>
        </Col>
      </Row>

      {/* Substrate Associations */}
      <Card className="mb-4">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>Associated Substrates</strong>
          <Button variant="outline-primary" size="sm" onClick={() => {
            setSelectedSubstrate('');
            setShowSubstrateModal(true);
          }}>+ Add Substrate</Button>
        </Card.Header>
        <Card.Body className="p-0">
          {substrateAssocs.length > 0 ? (
            <Table hover>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th style={{ width: 110 }}>Default</th>
                  <th style={{ width: 100 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {substrateAssocs.map(a => (
                  <tr key={a.id}>
                    <td className="fw-semibold">{a.substrate?.code}</td>
                    <td>{a.substrate?.name}</td>
                    <td className="text-muted">{a.substrate?.substrate_type || '--'}</td>
                    <td>
                      {a.is_default ? (
                        <Badge bg="primary">Default</Badge>
                      ) : (
                        <Button variant="link" size="sm" className="p-0" style={{ fontSize: '0.8125rem' }}
                          onClick={async () => {
                            await seriesAPI.updateSubstrate(id, a.id, { is_default: true });
                            loadData();
                          }}>
                          Set Default
                        </Button>
                      )}
                    </td>
                    <td>
                      <Button variant="outline-danger" size="sm" onClick={async () => {
                        await seriesAPI.removeSubstrate(id, a.id);
                        toast.success('Substrate removed');
                        loadData();
                      }}>Remove</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <h6>No substrates linked</h6>
              <p>Add a substrate to set a default printing surface for formulations.</p>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Add Substrate Modal */}
      <Modal show={showSubstrateModal} onHide={() => setShowSubstrateModal(false)} centered>
        <Modal.Header closeButton><Modal.Title>Add Substrate to Series</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group>
            <Form.Label>Substrate</Form.Label>
            <Form.Select value={selectedSubstrate} onChange={e => setSelectedSubstrate(e.target.value)}>
              <option value="">Select a substrate...</option>
              {allSubstrates
                .filter(s => !substrateAssocs.find(a => a.substrate_id === s.id))
                .map(s => (
                  <option key={s.id} value={s.id}>{s.code} — {s.name}</option>
                ))}
            </Form.Select>
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowSubstrateModal(false)}>Cancel</Button>
          <Button variant="primary" disabled={!selectedSubstrate} onClick={async () => {
            try {
              await seriesAPI.addSubstrate(id, {
                substrate_id: parseInt(selectedSubstrate),
                is_default: substrateAssocs.length === 0,
              });
              toast.success('Substrate added');
              setShowSubstrateModal(false);
              loadData();
            } catch (err) {
              toast.error(err.response?.data?.error || 'Failed to add substrate');
            }
          }}>Add</Button>
        </Modal.Footer>
      </Modal>

      {/* Mixing Bases */}
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>Mixing Bases</strong>
          <Button variant="primary" size="sm" onClick={() => openBaseModal()}>
            + Add Base
          </Button>
        </Card.Header>
        <Card.Body className="p-0">
          <Table hover>
            <thead>
              <tr>
                <th style={{ width: 48 }}>Color</th>
                <th>Code</th>
                <th>Name</th>
                <th>Color Index</th>
                <th style={{ width: 90 }}>Conc.</th>
                <th>LAB</th>
                <th style={{ width: 90 }}>Status</th>
                <th style={{ width: 160 }}>Actions</th>
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
                        style={{
                          backgroundColor: lab ? labToApproxHex(lab.L, lab.a, lab.b) : '#e2e8f0',
                          width: 28, height: 28,
                        }}
                      />
                    </td>
                    <td>
                      <Link to={`/bases/${b.id}`} className="fw-semibold text-decoration-none">
                        {b.code}
                      </Link>
                    </td>
                    <td>{b.name}</td>
                    <td className="text-muted text-mono">{b.color_index || '--'}</td>
                    <td className="text-center">{b.concentration_count}</td>
                    <td className="text-mono" style={{ fontSize: '0.8125rem' }}>
                      {lab
                        ? `${lab.L.toFixed(1)} / ${lab.a.toFixed(1)} / ${lab.b.toFixed(1)}`
                        : '--'
                      }
                    </td>
                    <td>
                      <Badge bg={b.is_active ? 'success' : 'secondary'}>
                        {b.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td>
                      <div className="d-flex gap-2">
                        <Button variant="outline-primary" size="sm" onClick={() => openBaseModal(b)}>
                          Edit
                        </Button>
                        <Button variant="outline-danger" size="sm" onClick={() => setDeleteConfirm(b.id)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {bases.length === 0 && (
                <tr>
                  <td colSpan="8">
                    <div className="empty-state">
                      <h6>No mixing bases yet</h6>
                      <p>Add mixing bases and upload CXF spectral data to enable formulation.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* Add/Edit Base Modal */}
      <Modal show={showBaseModal} onHide={() => setShowBaseModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>{editBase ? 'Edit Mixing Base' : 'Add Mixing Base'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveBase}>
          <Modal.Body>
            <Row className="g-3 mb-3">
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Base Code</Form.Label>
                  <Form.Control
                    value={baseForm.code}
                    onChange={e => setBaseForm({ ...baseForm, code: e.target.value })}
                    placeholder="e.g., Y, R, B, BK"
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label>Color Index</Form.Label>
                  <Form.Control
                    value={baseForm.color_index}
                    onChange={e => setBaseForm({ ...baseForm, color_index: e.target.value })}
                    placeholder="e.g., PY 13, PB 15:3"
                  />
                </Form.Group>
              </Col>
            </Row>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                value={baseForm.name}
                onChange={e => setBaseForm({ ...baseForm, name: e.target.value })}
                placeholder="e.g., Yellow, Warm Red"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Notes</Form.Label>
              <Form.Control
                as="textarea" rows={2}
                value={baseForm.notes}
                onChange={e => setBaseForm({ ...baseForm, notes: e.target.value })}
                placeholder="Optional notes..."
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
      <Modal show={showEditSeries} onHide={() => setShowEditSeries(false)} centered>
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
            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea" rows={3}
                value={seriesForm.description}
                onChange={e => setSeriesForm({ ...seriesForm, description: e.target.value })}
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Ink Type</Form.Label>
              <Form.Select
                value={seriesForm.ink_type}
                onChange={e => setSeriesForm({ ...seriesForm, ink_type: e.target.value })}
              >
                <option value="litho">Litho (Opaque)</option>
                <option value="flexo">Flexo (Translucent)</option>
              </Form.Select>
              <Form.Text>
                Litho uses single-constant K-M; Flexo uses two-constant K-M
              </Form.Text>
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

      {/* Delete Confirmation */}
      <Modal show={deleteConfirm !== null} onHide={() => setDeleteConfirm(null)} centered size="sm">
        <Modal.Header closeButton><Modal.Title>Confirm Delete</Modal.Title></Modal.Header>
        <Modal.Body>
          {deleteConfirm === 'series' ? (
            <p className="mb-0">Deactivate series <strong>{series.code}</strong>? This will deactivate the series and all its bases.</p>
          ) : (
            <p className="mb-0">Delete base <strong>{bases.find(b => b.id === deleteConfirm)?.code}</strong>? This permanently removes the base and all spectral data.</p>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" size="sm" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button
            variant="danger" size="sm"
            onClick={() => deleteConfirm === 'series' ? handleDeleteSeries() : handleDeleteBase(deleteConfirm)}
          >
            {deleteConfirm === 'series' ? 'Deactivate' : 'Delete'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default SeriesDetail;
