import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Form, Spinner, InputGroup, Badge, Row, Col, Modal, ProgressBar } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { pantoneAPI, seriesAPI, exportAPI } from '../../services/api';
import { getDeltaEClass, formatDate, downloadBlob, labToApproxHex } from '../../utils/helpers';

function PantoneFormulas() {
  const [formulas, setFormulas] = useState([]);
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [seriesFilter, setSeriesFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Bulk generation state
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkSeriesId, setBulkSeriesId] = useState('');
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  useEffect(() => {
    seriesAPI.list({ active_only: 'true' }).then(res => setSeries(res.data.series));
  }, []);

  const loadFormulas = async () => {
    setLoading(true);
    try {
      const params = { search, page, per_page: 50, current_only: 'true' };
      if (seriesFilter) params.series_id = seriesFilter;
      const res = await pantoneAPI.listFormulas(params);
      setFormulas(res.data.formulas);
      setTotalPages(res.data.pages);
    } catch (err) {
      toast.error('Failed to load formulas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadFormulas(); }, [search, seriesFilter, page]);

  const handleExportExcel = async () => {
    try {
      const params = seriesFilter ? { series_id: seriesFilter } : {};
      const res = await exportAPI.pantoneFormulasExcel(params);
      downloadBlob(new Blob([res.data]), 'pantone_formulas.xlsx');
      toast.success('Excel file downloaded');
    } catch (err) {
      toast.error('Failed to export');
    }
  };

  const handleBulkFormulate = async () => {
    if (!bulkSeriesId) {
      toast.error('Select a series first');
      return;
    }
    setBulkRunning(true);
    setBulkResult(null);
    try {
      const res = await pantoneAPI.formulateAll(parseInt(bulkSeriesId));
      setBulkResult(res.data);
      toast.success(res.data.message);
      loadFormulas();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Bulk formulation failed');
    } finally {
      setBulkRunning(false);
    }
  };

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <h2>Pantone Formulas</h2>
        <div>
          <Button variant="outline-success" className="me-2" onClick={() => setShowBulkModal(true)}>
            Generate All
          </Button>
          <Button variant="outline-secondary" className="me-2" onClick={handleExportExcel}>
            Export Excel
          </Button>
          <Link to="/pantone/formulate" className="btn btn-primary">
            Generate Formula
          </Link>
        </div>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <Row>
            <Col md={8}>
              <InputGroup>
                <Form.Control
                  placeholder="Search by Pantone code..."
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1); }}
                />
              </InputGroup>
            </Col>
            <Col md={4}>
              <Form.Select
                value={seriesFilter}
                onChange={e => { setSeriesFilter(e.target.value); setPage(1); }}
              >
                <option value="">All Series</option>
                {series.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </Form.Select>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      <Card>
        <Card.Body className="p-0">
          {loading ? (
            <div className="text-center p-4"><Spinner animation="border" /></div>
          ) : (
            <Table hover className="mb-0 formula-table">
              <thead>
                <tr>
                  <th>Color</th><th>Target</th><th>Series</th><th>Version</th>
                  <th>DE*00</th><th>Status</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
                {formulas.map(f => (
                  <tr key={f.id}>
                    <td>
                      <div className="color-swatch" style={{
                        backgroundColor: f.predicted_lab
                          ? labToApproxHex(f.predicted_lab.L, f.predicted_lab.a, f.predicted_lab.b)
                          : '#ccc'
                      }} />
                    </td>
                    <td>
                      <Link to={`/pantone/formulas/${f.id}`}>
                        <strong>{f.target_code}</strong>
                      </Link>
                    </td>
                    <td>{f.series_name}</td>
                    <td>v{f.version}</td>
                    <td>
                      <span className={`delta-e-badge ${getDeltaEClass(f.delta_e_2000)}`}>
                        {f.delta_e_2000?.toFixed(2) ?? '—'}
                      </span>
                    </td>
                    <td>
                      <Badge className={`status-${f.status}`}>{f.status}</Badge>
                    </td>
                    <td className="text-muted small">{formatDate(f.created_at)}</td>
                  </tr>
                ))}
                {formulas.length === 0 && (
                  <tr><td colSpan="7" className="text-center text-muted p-4">
                    No formulas found.
                  </td></tr>
                )}
              </tbody>
            </Table>
          )}
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

      {/* Bulk Generate Modal */}
      <Modal show={showBulkModal} onHide={() => { if (!bulkRunning) setShowBulkModal(false); }} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Generate Formulas for All Pantone Colors</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {!bulkResult && !bulkRunning && (
            <>
              <p>This will generate best-match formulas for every Pantone target color using the selected ink series. Existing formulas will be versioned (not overwritten).</p>
              <Form.Group className="mb-3">
                <Form.Label>Ink Series</Form.Label>
                <Form.Select
                  value={bulkSeriesId}
                  onChange={e => setBulkSeriesId(e.target.value)}
                >
                  <option value="">Select a series...</option>
                  {series.map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                  ))}
                </Form.Select>
              </Form.Group>
              <p className="text-muted small">
                This may take several minutes depending on the number of targets and system speed.
              </p>
            </>
          )}

          {bulkRunning && (
            <div className="text-center py-4">
              <Spinner animation="border" className="mb-3" />
              <p>Generating formulas for all Pantone targets...</p>
              <p className="text-muted small">This may take a few minutes. Please wait.</p>
              <ProgressBar animated now={100} />
            </div>
          )}

          {bulkResult && (
            <div>
              <div className="text-center mb-3">
                <h4 className="text-success">{bulkResult.message}</h4>
              </div>
              <Row className="mb-3">
                <Col>
                  <Card className="text-center p-3 bg-light">
                    <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{bulkResult.total}</div>
                    <div className="text-muted">Total Targets</div>
                  </Card>
                </Col>
                <Col>
                  <Card className="text-center p-3 bg-light">
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#28a745' }}>{bulkResult.succeeded}</div>
                    <div className="text-muted">Succeeded</div>
                  </Card>
                </Col>
                <Col>
                  <Card className="text-center p-3 bg-light">
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: bulkResult.failed > 0 ? '#dc3545' : '#6c757d' }}>{bulkResult.failed}</div>
                    <div className="text-muted">Failed</div>
                  </Card>
                </Col>
              </Row>
              {bulkResult.results?.length > 0 && (
                <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                  <Table size="sm" hover>
                    <thead>
                      <tr><th>Target</th><th>DE*00</th></tr>
                    </thead>
                    <tbody>
                      {bulkResult.results.map((r, i) => (
                        <tr key={i}>
                          <td>{r.target_code}</td>
                          <td>
                            <span className={`delta-e-badge ${getDeltaEClass(r.delta_e_2000)}`}>
                              {r.delta_e_2000?.toFixed(2)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              )}
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          {!bulkRunning && (
            <Button variant="secondary" onClick={() => { setShowBulkModal(false); setBulkResult(null); }}>
              {bulkResult ? 'Close' : 'Cancel'}
            </Button>
          )}
          {!bulkResult && !bulkRunning && (
            <Button variant="success" onClick={handleBulkFormulate} disabled={!bulkSeriesId}>
              Generate All Formulas
            </Button>
          )}
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default PantoneFormulas;
