import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Card, Table, Button, Modal, Form, Spinner, Row, Col, Alert } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { useDropzone } from 'react-dropzone';
import { basesAPI } from '../../services/api';
import { labToApproxHex, formatDate } from '../../utils/helpers';

function BaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [base, setBase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showConcModal, setShowConcModal] = useState(false);
  const [concForm, setConcForm] = useState({ concentration_pct: '', label: '' });
  const [uploadConc, setUploadConc] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [spectralHistory, setSpectralHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(null);

  // Edit/delete state
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState({ code: '', name: '', color_index: '', notes: '' });
  const [saving, setSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const loadBase = async () => {
    try {
      const res = await basesAPI.get(id);
      setBase(res.data.base);
    } catch (err) {
      toast.error('Failed to load base data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadBase(); }, [id]);

  const handleAddConc = async (e) => {
    e.preventDefault();
    try {
      await basesAPI.addConcentration(id, {
        concentration_pct: parseFloat(concForm.concentration_pct),
        label: concForm.label,
      });
      toast.success('Concentration level added');
      setShowConcModal(false);
      setConcForm({ concentration_pct: '', label: '' });
      loadBase();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to add concentration');
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!uploadConc || acceptedFiles.length === 0) return;
    setUploading(true);
    try {
      const res = await basesAPI.uploadCxf(uploadConc.id, acceptedFiles[0]);
      toast.success('CXF file uploaded and parsed successfully');
      if (res.data.warnings?.length > 0) {
        res.data.warnings.forEach(w => toast.warn(w));
      }
      setUploadConc(null);
      loadBase();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to upload CXF file');
    } finally {
      setUploading(false);
    }
  }, [uploadConc]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/xml': ['.cxf', '.xml'] },
    maxFiles: 1,
  });

  const loadHistory = async (concId) => {
    try {
      const res = await basesAPI.getSpectralHistory(concId);
      setSpectralHistory(res.data.versions);
      setShowHistory(concId);
    } catch (err) {
      toast.error('Failed to load history');
    }
  };

  // Edit base
  const openEditModal = () => {
    setEditForm({
      code: base.code,
      name: base.name,
      color_index: base.color_index || '',
      notes: base.notes || '',
    });
    setShowEditModal(true);
  };

  const handleEditBase = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await basesAPI.update(id, editForm);
      toast.success('Base updated');
      setShowEditModal(false);
      loadBase();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to update base');
    } finally {
      setSaving(false);
    }
  };

  // Delete base
  const handleDeleteBase = async () => {
    try {
      await basesAPI.delete(id);
      toast.success('Base deleted');
      navigate(`/series/${base.series_id}`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete base');
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;
  if (!base) return <p>Base not found.</p>;

  const lab = base.concentrations?.find(c => c.lab_values)?.lab_values;

  return (
    <div>
      <div className="page-header">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-1">
            <li className="breadcrumb-item"><Link to="/series">Ink Series</Link></li>
            <li className="breadcrumb-item"><Link to={`/series/${base.series_id}`}>Series</Link></li>
            <li className="breadcrumb-item active">{base.code}</li>
          </ol>
        </nav>
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-3">
            {lab && (
              <div className="color-swatch" style={{
                backgroundColor: labToApproxHex(lab.L, lab.a, lab.b),
                width: 48, height: 48
              }} />
            )}
            <div>
              <h2 className="mb-0">{base.name} ({base.code})</h2>
              {base.color_index && <span className="text-muted">{base.color_index}</span>}
            </div>
          </div>
          <div>
            <Button variant="outline-primary" size="sm" className="me-2" onClick={openEditModal}>
              Edit Base
            </Button>
            <Button variant="outline-danger" size="sm" onClick={() => setShowDeleteConfirm(true)}>
              Delete Base
            </Button>
          </div>
        </div>
      </div>

      {base.notes && <Alert variant="info">{base.notes}</Alert>}

      <Card className="mb-4">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>Concentration Levels</strong>
          <Button variant="primary" size="sm" onClick={() => setShowConcModal(true)}>
            + Add Concentration
          </Button>
        </Card.Header>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr>
                <th>Concentration</th><th>Label</th><th>Spectral Data</th>
                <th>LAB</th><th>Version</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {base.concentrations?.map(c => (
                <tr key={c.id}>
                  <td><strong>{c.concentration_pct}%</strong></td>
                  <td>{c.label || '—'}</td>
                  <td>{c.has_spectral_data ? 'Yes' : 'No'}</td>
                  <td className="small">
                    {c.lab_values
                      ? `L*${c.lab_values.L.toFixed(1)} a*${c.lab_values.a.toFixed(1)} b*${c.lab_values.b.toFixed(1)}`
                      : '—'}
                  </td>
                  <td>{c.current_version || '—'}</td>
                  <td>
                    <Button
                      variant="outline-primary" size="sm" className="me-2"
                      onClick={() => setUploadConc(c)}
                    >
                      Upload CXF
                    </Button>
                    {c.has_spectral_data && (
                      <Button
                        variant="outline-secondary" size="sm"
                        onClick={() => loadHistory(c.id)}
                      >
                        History
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* CXF Upload Modal */}
      <Modal show={!!uploadConc} onHide={() => setUploadConc(null)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Upload CXF — {base.code} @ {uploadConc?.concentration_pct}%</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div
            {...getRootProps()}
            className={`border border-2 rounded p-5 text-center ${isDragActive ? 'border-primary bg-light' : 'border-dashed'}`}
            style={{ cursor: 'pointer' }}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <Spinner animation="border" />
            ) : isDragActive ? (
              <p className="mb-0">Drop the CXF file here...</p>
            ) : (
              <div>
                <p className="mb-1"><strong>Drag & drop a CXF file here</strong></p>
                <p className="text-muted mb-0">or click to select a file (.cxf, .xml)</p>
              </div>
            )}
          </div>
          <p className="text-muted small mt-3">
            The CXF file will be parsed to extract spectral reflectance data.
            A new version will be created, preserving any existing data.
          </p>
        </Modal.Body>
      </Modal>

      {/* Spectral History Modal */}
      <Modal show={!!showHistory} onHide={() => setShowHistory(null)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Spectral Data History</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Table hover>
            <thead>
              <tr><th>Version</th><th>LAB</th><th>Current</th><th>Uploaded</th></tr>
            </thead>
            <tbody>
              {spectralHistory.map(s => (
                <tr key={s.id}>
                  <td>v{s.version}</td>
                  <td className="small">
                    {s.lab_values
                      ? `L*${s.lab_values.L.toFixed(2)} a*${s.lab_values.a.toFixed(2)} b*${s.lab_values.b.toFixed(2)}`
                      : '—'}
                  </td>
                  <td>{s.is_current ? 'Current' : ''}</td>
                  <td className="text-muted small">{formatDate(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Modal.Body>
      </Modal>

      {/* Add Concentration Modal */}
      <Modal show={showConcModal} onHide={() => setShowConcModal(false)}>
        <Modal.Header closeButton><Modal.Title>Add Concentration Level</Modal.Title></Modal.Header>
        <Form onSubmit={handleAddConc}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Concentration (%)</Form.Label>
              <Form.Control
                type="number" step="0.1" min="0.1" max="100"
                value={concForm.concentration_pct}
                onChange={e => setConcForm({ ...concForm, concentration_pct: e.target.value })}
                placeholder="e.g., 100, 50, 25"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Label</Form.Label>
              <Form.Control
                value={concForm.label}
                onChange={e => setConcForm({ ...concForm, label: e.target.value })}
                placeholder="e.g., Full Strength, 25% Letdown"
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowConcModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary">Add</Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Edit Base Modal */}
      <Modal show={showEditModal} onHide={() => setShowEditModal(false)}>
        <Modal.Header closeButton><Modal.Title>Edit Base</Modal.Title></Modal.Header>
        <Form onSubmit={handleEditBase}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Base Code</Form.Label>
              <Form.Control
                value={editForm.code}
                onChange={e => setEditForm({ ...editForm, code: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                value={editForm.name}
                onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Color Index</Form.Label>
              <Form.Control
                value={editForm.color_index}
                onChange={e => setEditForm({ ...editForm, color_index: e.target.value })}
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Notes</Form.Label>
              <Form.Control
                as="textarea" rows={2}
                value={editForm.notes}
                onChange={e => setEditForm({ ...editForm, notes: e.target.value })}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEditModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Delete Confirmation */}
      <Modal show={showDeleteConfirm} onHide={() => setShowDeleteConfirm(false)}>
        <Modal.Header closeButton><Modal.Title>Confirm Delete</Modal.Title></Modal.Header>
        <Modal.Body>
          Are you sure you want to delete base <strong>{base.code}</strong>?
          This will permanently remove the base and all its spectral data.
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>Cancel</Button>
          <Button variant="danger" onClick={handleDeleteBase}>Delete</Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default BaseDetail;
