import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Spinner, Badge, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { useDropzone } from 'react-dropzone';
import { substratesAPI } from '../../services/api';
import { labToApproxHex, formatDate } from '../../utils/helpers';
import SpectralChart from '../common/SpectralChart';

function SubstrateList() {
  const [substrates, setSubstrates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editSubstrate, setEditSubstrate] = useState(null);
  const [form, setForm] = useState({ code: '', name: '', substrate_type: '', description: '' });
  const [cxfFile, setCxfFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [spectralData, setSpectralData] = useState(null);
  const [showSpectral, setShowSpectral] = useState(false);

  const loadSubstrates = async () => {
    try {
      const res = await substratesAPI.list();
      setSubstrates(res.data.substrates);
    } catch (err) {
      toast.error(err.serverMessage || 'Failed to load substrates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSubstrates(); }, []);

  const openModal = (s = null) => {
    if (s) {
      setEditSubstrate(s);
      setForm({ code: s.code, name: s.name, substrate_type: s.substrate_type || '', description: s.description || '' });
    } else {
      setEditSubstrate(null);
      setForm({ code: '', name: '', substrate_type: '', description: '' });
    }
    setCxfFile(null);
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editSubstrate) {
        await substratesAPI.update(editSubstrate.id, {
          name: form.name,
          substrate_type: form.substrate_type,
          description: form.description,
        });
        toast.success('Substrate updated');
      } else if (cxfFile) {
        const formData = new FormData();
        formData.append('file', cxfFile);
        formData.append('code', form.code);
        formData.append('name', form.name);
        formData.append('substrate_type', form.substrate_type);
        formData.append('description', form.description);
        await substratesAPI.createFromCxf(formData);
        toast.success('Substrate created from CXF');
      } else {
        await substratesAPI.create(form);
        toast.success('Substrate created');
      }
      setShowModal(false);
      loadSubstrates();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to save substrate');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await substratesAPI.delete(id);
      toast.success('Substrate deactivated');
      setDeleteConfirm(null);
      loadSubstrates();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete substrate');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: files => setCxfFile(files[0]),
    accept: { 'application/xml': ['.cxf', '.xml'] },
    maxFiles: 1,
  });

  if (loading) return <div className="page-spinner"><Spinner animation="border" variant="primary" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <div>
          <h2>Substrates</h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>
            Manage printing substrates with optional spectral reflectance data
          </p>
        </div>
        <Button variant="primary" onClick={() => openModal()}>
          + New Substrate
        </Button>
      </div>

      <Card>
        <Card.Body className="p-0">
          <Table hover>
            <thead>
              <tr>
                <th style={{ width: 48 }}></th>
                <th>Code</th>
                <th>Name</th>
                <th>Type</th>
                <th style={{ width: 80 }}>Spectral</th>
                <th style={{ width: 90 }}>Status</th>
                <th>Created</th>
                <th style={{ width: 220 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {substrates.map(s => (
                <tr key={s.id}>
                  <td>
                    <div
                      className="color-swatch"
                      style={{
                        backgroundColor: s.lab_values
                          ? labToApproxHex(s.lab_values.L, s.lab_values.a, s.lab_values.b)
                          : '#f1f5f9',
                        width: 28, height: 28,
                      }}
                    />
                  </td>
                  <td className="fw-semibold">{s.code}</td>
                  <td>{s.name}</td>
                  <td className="text-muted">{s.substrate_type || '--'}</td>
                  <td>
                    <Badge bg={s.has_spectral ? 'success' : 'secondary'}>
                      {s.has_spectral ? 'Yes' : 'No'}
                    </Badge>
                  </td>
                  <td>
                    <Badge bg={s.is_active ? 'success' : 'secondary'}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="text-muted">{formatDate(s.created_at)}</td>
                  <td>
                    <div className="d-flex gap-2">
                      {s.has_spectral && (
                        <Button variant="outline-info" size="sm" onClick={async () => {
                          try {
                            const res = await substratesAPI.get(s.id);
                            setSpectralData(res.data.substrate);
                            setShowSpectral(true);
                          } catch { toast.error('Failed to load spectral data'); }
                        }}>
                          Spectral
                        </Button>
                      )}
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
              {substrates.length === 0 && (
                <tr>
                  <td colSpan="8">
                    <div className="empty-state">
                      <h6>No substrates yet</h6>
                      <p>Add a substrate to define printing surfaces for accurate color formulation.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* Create/Edit Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title>{editSubstrate ? 'Edit Substrate' : 'New Substrate'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSave}>
          <Modal.Body>
            <Row className="g-3 mb-3">
              <Col md={4}>
                <Form.Group>
                  <Form.Label>Code</Form.Label>
                  <Form.Control
                    value={form.code}
                    onChange={e => setForm({ ...form, code: e.target.value })}
                    placeholder="e.g., COATED-C2S"
                    required
                    disabled={!!editSubstrate}
                  />
                  {editSubstrate && <Form.Text>Code cannot be changed</Form.Text>}
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label>Name</Form.Label>
                  <Form.Control
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g., Coated C2S Paper"
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label>Type</Form.Label>
                  <Form.Select
                    value={form.substrate_type}
                    onChange={e => setForm({ ...form, substrate_type: e.target.value })}
                  >
                    <option value="">Select type...</option>
                    <option value="Coated Paper">Coated Paper</option>
                    <option value="Uncoated Paper">Uncoated Paper</option>
                    <option value="Film">Film</option>
                    <option value="Foil">Foil</option>
                    <option value="Board">Board</option>
                    <option value="Label Stock">Label Stock</option>
                    <option value="Other">Other</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>
            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea" rows={2}
                value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Optional description..."
              />
            </Form.Group>
            {!editSubstrate && (
              <Form.Group>
                <Form.Label>Spectral Data (CXF File)</Form.Label>
                <div
                  {...getRootProps()}
                  className={`dropzone-area ${isDragActive ? 'active' : ''}`}
                >
                  <input {...getInputProps()} />
                  {cxfFile ? (
                    <p className="mb-0 fw-medium">{cxfFile.name}</p>
                  ) : (
                    <>
                      <div className="dropzone-icon">+</div>
                      <p>Drop a CXF file here or click to select</p>
                      <p className="text-muted" style={{ fontSize: '0.75rem' }}>
                        Optional — provides spectral reflectance for accurate formulation
                      </p>
                    </>
                  )}
                </div>
              </Form.Group>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : editSubstrate ? 'Save Changes' : 'Create Substrate'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Delete Confirmation */}
      <Modal show={deleteConfirm !== null} onHide={() => setDeleteConfirm(null)} centered size="sm">
        <Modal.Header closeButton><Modal.Title>Confirm Delete</Modal.Title></Modal.Header>
        <Modal.Body>
          Deactivate substrate <strong>{deleteConfirm?.code}</strong>?
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" size="sm" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" size="sm" onClick={() => handleDelete(deleteConfirm.id)}>
            Deactivate
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Spectral Data Modal */}
      <Modal show={showSpectral} onHide={() => setShowSpectral(false)} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title>Spectral Reflectance — {spectralData?.code}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {spectralData?.spectral_reflectance ? (
            <SpectralChart
              spectra={[{ label: spectralData.code, values: spectralData.spectral_reflectance, color: '#3b82f6' }]}
              height={350}
            />
          ) : (
            <p className="text-muted text-center">No spectral data available.</p>
          )}
          {spectralData?.lab_values && (
            <div className="text-center mt-3" style={{ fontSize: '0.875rem' }}>
              <span className="me-4"><strong>L*</strong> {spectralData.lab_values.L?.toFixed(2)}</span>
              <span className="me-4"><strong>a*</strong> {spectralData.lab_values.a?.toFixed(2)}</span>
              <span><strong>b*</strong> {spectralData.lab_values.b?.toFixed(2)}</span>
            </div>
          )}
        </Modal.Body>
      </Modal>
    </div>
  );
}

export default SubstrateList;
