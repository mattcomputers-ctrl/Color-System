import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Spinner, InputGroup, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { pantoneAPI } from '../../services/api';
import { labToApproxHex, formatDate } from '../../utils/helpers';

function PantoneTargets() {
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    pantone_code: '', pantone_name: '', library: 'PMS',
    lab_l: '', lab_a: '', lab_b: '', source: '',
  });
  const [saving, setSaving] = useState(false);

  const loadTargets = async () => {
    try {
      const res = await pantoneAPI.listTargets({ search, page, per_page: 50 });
      setTargets(res.data.targets);
      setTotalPages(res.data.pages);
    } catch (err) {
      toast.error('Failed to load targets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTargets(); }, [search, page]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await pantoneAPI.createTarget({
        ...form,
        lab_l: parseFloat(form.lab_l),
        lab_a: parseFloat(form.lab_a),
        lab_b: parseFloat(form.lab_b),
      });
      toast.success('Pantone target created');
      setShowModal(false);
      setForm({
        pantone_code: '', pantone_name: '', library: 'PMS',
        lab_l: '', lab_a: '', lab_b: '', source: '',
      });
      loadTargets();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create target');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <h2>Pantone Targets</h2>
        <Button variant="primary" onClick={() => setShowModal(true)}>+ Add Target</Button>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <InputGroup>
            <Form.Control
              placeholder="Search by Pantone code or name..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
            />
          </InputGroup>
        </Card.Body>
      </Card>

      <Card>
        <Card.Body className="p-0">
          <Table hover className="mb-0">
            <thead>
              <tr><th>Color</th><th>Code</th><th>Name</th><th>L*</th><th>a*</th><th>b*</th><th>Spectral</th></tr>
            </thead>
            <tbody>
              {targets.map(t => (
                <tr key={t.id}>
                  <td>
                    <div className="color-swatch" style={{
                      backgroundColor: t.lab_values
                        ? labToApproxHex(t.lab_values.L, t.lab_values.a, t.lab_values.b)
                        : '#ccc'
                    }} />
                  </td>
                  <td><strong>{t.pantone_code}</strong></td>
                  <td>{t.pantone_name || '—'}</td>
                  <td>{t.lab_values?.L?.toFixed(2) ?? '—'}</td>
                  <td>{t.lab_values?.a?.toFixed(2) ?? '—'}</td>
                  <td>{t.lab_values?.b?.toFixed(2) ?? '—'}</td>
                  <td>{t.has_spectral ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
        {totalPages > 1 && (
          <Card.Footer className="d-flex justify-content-between">
            <Button variant="outline-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              Previous
            </Button>
            <span className="align-self-center">Page {page} of {totalPages}</span>
            <Button variant="outline-secondary" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
              Next
            </Button>
          </Card.Footer>
        )}
      </Card>

      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton><Modal.Title>Add Pantone Target</Modal.Title></Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Row>
              <Col md={8}>
                <Form.Group className="mb-3">
                  <Form.Label>Pantone Code</Form.Label>
                  <Form.Control
                    value={form.pantone_code}
                    onChange={e => setForm({ ...form, pantone_code: e.target.value })}
                    placeholder="e.g., 185 C"
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Library</Form.Label>
                  <Form.Select
                    value={form.library}
                    onChange={e => setForm({ ...form, library: e.target.value })}
                  >
                    <option value="PMS">PMS</option>
                    <option value="PMS+">PMS+</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>
            <Form.Group className="mb-3">
              <Form.Label>Name (optional)</Form.Label>
              <Form.Control
                value={form.pantone_name}
                onChange={e => setForm({ ...form, pantone_name: e.target.value })}
              />
            </Form.Group>
            <Row>
              <Col>
                <Form.Group className="mb-3">
                  <Form.Label>L*</Form.Label>
                  <Form.Control type="number" step="0.01"
                    value={form.lab_l}
                    onChange={e => setForm({ ...form, lab_l: e.target.value })}
                    required
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group className="mb-3">
                  <Form.Label>a*</Form.Label>
                  <Form.Control type="number" step="0.01"
                    value={form.lab_a}
                    onChange={e => setForm({ ...form, lab_a: e.target.value })}
                    required
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group className="mb-3">
                  <Form.Label>b*</Form.Label>
                  <Form.Control type="number" step="0.01"
                    value={form.lab_b}
                    onChange={e => setForm({ ...form, lab_b: e.target.value })}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>
            <Form.Group>
              <Form.Label>Source</Form.Label>
              <Form.Control
                value={form.source}
                onChange={e => setForm({ ...form, source: e.target.value })}
                placeholder="e.g., Pantone PLUS Series Guide"
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving...' : 'Add Target'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}

export default PantoneTargets;
