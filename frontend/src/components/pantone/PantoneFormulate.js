import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Spinner, Row, Col, Table } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { pantoneAPI, seriesAPI, substratesAPI } from '../../services/api';
import { labToApproxHex, getDeltaEClass, getDeltaELabel } from '../../utils/helpers';

function PantoneFormulate() {
  const [series, setSeries] = useState([]);
  const [substrates, setSubstrates] = useState([]);
  const [targets, setTargets] = useState([]);
  const [selectedSeries, setSelectedSeries] = useState('');
  const [selectedSubstrate, setSelectedSubstrate] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('');
  const [targetSearch, setTargetSearch] = useState('');
  const [formulating, setFormulating] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    seriesAPI.list({ active_only: 'true' }).then(res => setSeries(res.data.series));
    substratesAPI.list({ active_only: 'true' }).then(res => setSubstrates(res.data.substrates));
  }, []);

  useEffect(() => {
    if (targetSearch.length >= 1) {
      pantoneAPI.listTargets({ search: targetSearch, per_page: 20 })
        .then(res => setTargets(res.data.targets));
    }
  }, [targetSearch]);

  const handleFormulate = async () => {
    if (!selectedSeries || !selectedTarget) {
      toast.warn('Please select both a target and an ink series');
      return;
    }
    setFormulating(true);
    setResult(null);
    try {
      const res = await pantoneAPI.formulate(
        parseInt(selectedTarget),
        parseInt(selectedSeries),
        selectedSubstrate ? parseInt(selectedSubstrate) : null
      );
      setResult(res.data.formula);
      toast.success('Formula generated successfully');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Formulation failed');
    } finally {
      setFormulating(false);
    }
  };

  const target = targets.find(t => t.id === parseInt(selectedTarget));

  return (
    <div>
      <div className="page-header">
        <h2>Generate Pantone Formula</h2>
        <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>
          Select a Pantone target color and ink series to compute an optimal formula
        </p>
      </div>

      <Row className="g-4">
        {/* Left Column - Input */}
        <Col lg={5}>
          <Card className="mb-4">
            <Card.Header><strong>Configuration</strong></Card.Header>
            <Card.Body>
              {/* Target Search */}
              <Form.Group className="mb-4">
                <Form.Label>Pantone Target</Form.Label>
                <Form.Control
                  value={targetSearch}
                  onChange={e => setTargetSearch(e.target.value)}
                  placeholder="Search by Pantone code (e.g., 185 C)..."
                  className="mb-2"
                />
                {targets.length > 0 && (
                  <Form.Select
                    value={selectedTarget}
                    onChange={e => setSelectedTarget(e.target.value)}
                  >
                    <option value="">Select from results...</option>
                    {targets.map(t => (
                      <option key={t.id} value={t.id}>
                        {t.pantone_code} — L*{t.lab_values?.L?.toFixed(1)} a*{t.lab_values?.a?.toFixed(1)} b*{t.lab_values?.b?.toFixed(1)}
                      </option>
                    ))}
                  </Form.Select>
                )}
              </Form.Group>

              {/* Target Preview */}
              {target && (
                <div className="d-flex align-items-center gap-3 mb-4 p-3 rounded" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div
                    className="color-swatch-lg"
                    style={{
                      backgroundColor: target.lab_values
                        ? labToApproxHex(target.lab_values.L, target.lab_values.a, target.lab_values.b)
                        : '#e2e8f0',
                      border: '2px solid #e2e8f0',
                    }}
                  />
                  <div>
                    <div className="fw-semibold" style={{ fontSize: '1.0625rem' }}>{target.pantone_code}</div>
                    <div className="text-mono text-muted" style={{ fontSize: '0.8125rem' }}>
                      L* {target.lab_values?.L?.toFixed(2)} &nbsp; a* {target.lab_values?.a?.toFixed(2)} &nbsp; b* {target.lab_values?.b?.toFixed(2)}
                    </div>
                  </div>
                </div>
              )}

              {/* Ink Series */}
              <Form.Group className="mb-4">
                <Form.Label>Ink Series</Form.Label>
                <Form.Select
                  value={selectedSeries}
                  onChange={e => setSelectedSeries(e.target.value)}
                >
                  <option value="">Select an ink series...</option>
                  {series.map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                  ))}
                </Form.Select>
              </Form.Group>

              {/* Substrate */}
              <Form.Group className="mb-4">
                <Form.Label>Substrate Override</Form.Label>
                <Form.Select
                  value={selectedSubstrate}
                  onChange={e => setSelectedSubstrate(e.target.value)}
                >
                  <option value="">Use series default</option>
                  {substrates.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.name}{s.substrate_type ? ` (${s.substrate_type})` : ''}
                    </option>
                  ))}
                </Form.Select>
                <Form.Text>Leave as default unless you need a specific substrate</Form.Text>
              </Form.Group>

              {/* Generate Button */}
              <Button
                variant="primary"
                size="lg"
                className="w-100"
                onClick={handleFormulate}
                disabled={!selectedSeries || !selectedTarget || formulating}
              >
                {formulating ? (
                  <><Spinner animation="border" size="sm" className="me-2" /> Computing Formula...</>
                ) : (
                  'Generate Formula'
                )}
              </Button>
            </Card.Body>
          </Card>
        </Col>

        {/* Right Column - Result */}
        <Col lg={7}>
          {result ? (
            <Card>
              <Card.Header className="d-flex justify-content-between align-items-center">
                <strong>Formula Result</strong>
                <Link to={`/pantone/formulas/${result.id}`} className="btn btn-sm btn-outline-primary">
                  View Full Details
                </Link>
              </Card.Header>
              <Card.Body>
                {/* Color comparison */}
                <Row className="g-3 mb-4">
                  <Col xs={6}>
                    <div className="text-center p-3 rounded" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div
                        className="color-swatch-lg mx-auto mb-2"
                        style={{
                          backgroundColor: target
                            ? labToApproxHex(target.lab_values?.L, target.lab_values?.a, target.lab_values?.b)
                            : '#e2e8f0',
                          width: 64, height: 64, border: '2px solid #e2e8f0',
                        }}
                      />
                      <div className="fw-medium" style={{ fontSize: '0.8125rem' }}>Target</div>
                      <div className="text-mono text-muted" style={{ fontSize: '0.75rem' }}>
                        {target?.lab_values?.L?.toFixed(2)} / {target?.lab_values?.a?.toFixed(2)} / {target?.lab_values?.b?.toFixed(2)}
                      </div>
                    </div>
                  </Col>
                  <Col xs={6}>
                    <div className="text-center p-3 rounded" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div
                        className="color-swatch-lg mx-auto mb-2"
                        style={{
                          backgroundColor: result.predicted_lab
                            ? labToApproxHex(result.predicted_lab.L, result.predicted_lab.a, result.predicted_lab.b)
                            : '#e2e8f0',
                          width: 64, height: 64, border: '2px solid #e2e8f0',
                        }}
                      />
                      <div className="fw-medium" style={{ fontSize: '0.8125rem' }}>Predicted</div>
                      <div className="text-mono text-muted" style={{ fontSize: '0.75rem' }}>
                        {result.predicted_lab?.L?.toFixed(2)} / {result.predicted_lab?.a?.toFixed(2)} / {result.predicted_lab?.b?.toFixed(2)}
                      </div>
                    </div>
                  </Col>
                </Row>

                {/* Delta E */}
                <div className="text-center mb-4">
                  <span className={`delta-e-badge ${getDeltaEClass(result.delta_e_2000)}`} style={{ fontSize: '1rem', padding: '0.4rem 1rem' }}>
                    dE*00: {result.delta_e_2000?.toFixed(4)} — {getDeltaELabel(result.delta_e_2000)}
                  </span>
                </div>

                {/* Components table */}
                <Table className="formula-table">
                  <thead>
                    <tr>
                      <th>Base</th>
                      <th>Name</th>
                      <th className="text-end">Percentage</th>
                      <th className="text-end">g/kg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.components?.map((c, i) => (
                      <tr key={i}>
                        <td className="fw-semibold">{c.base_code}</td>
                        <td>{c.base_name}</td>
                        <td className="text-end text-mono">{c.percentage?.toFixed(2)}%</td>
                        <td className="text-end text-mono">{c.weight_grams?.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          ) : (
            <div className="empty-state" style={{ minHeight: 400, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div className="empty-icon" style={{ fontSize: '3rem' }}>&#127912;</div>
              <h6>Ready to Formulate</h6>
              <p>Select a Pantone target and ink series, then click Generate to compute an optimal ink formula.</p>
            </div>
          )}
        </Col>
      </Row>
    </div>
  );
}

export default PantoneFormulate;
