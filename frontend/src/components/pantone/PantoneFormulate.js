import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Spinner, Row, Col, Alert, Table } from 'react-bootstrap';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { pantoneAPI, seriesAPI } from '../../services/api';
import { labToApproxHex, getDeltaEClass, getDeltaELabel } from '../../utils/helpers';

function PantoneFormulate() {
  const navigate = useNavigate();
  const [series, setSeries] = useState([]);
  const [targets, setTargets] = useState([]);
  const [selectedSeries, setSelectedSeries] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('');
  const [targetSearch, setTargetSearch] = useState('');
  const [formulating, setFormulating] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    seriesAPI.list({ active_only: 'true' }).then(res => setSeries(res.data.series));
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
      const res = await pantoneAPI.formulate(parseInt(selectedTarget), parseInt(selectedSeries));
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
      </div>

      <Row>
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header><strong>Select Target & Series</strong></Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>Search Pantone Target</Form.Label>
                <Form.Control
                  value={targetSearch}
                  onChange={e => setTargetSearch(e.target.value)}
                  placeholder="Type a Pantone code (e.g., 185 C)..."
                />
                {targets.length > 0 && (
                  <Form.Select
                    className="mt-2"
                    value={selectedTarget}
                    onChange={e => setSelectedTarget(e.target.value)}
                    size="sm"
                  >
                    <option value="">Select a target...</option>
                    {targets.map(t => (
                      <option key={t.id} value={t.id}>
                        {t.pantone_code} — L*{t.lab_values?.L?.toFixed(1)} a*{t.lab_values?.a?.toFixed(1)} b*{t.lab_values?.b?.toFixed(1)}
                      </option>
                    ))}
                  </Form.Select>
                )}
              </Form.Group>

              <Form.Group className="mb-3">
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

              {target && (
                <div className="d-flex align-items-center gap-3 mb-3 p-3 bg-light rounded">
                  <div className="color-swatch" style={{
                    backgroundColor: target.lab_values
                      ? labToApproxHex(target.lab_values.L, target.lab_values.a, target.lab_values.b)
                      : '#ccc',
                    width: 48, height: 48,
                  }} />
                  <div>
                    <strong>{target.pantone_code}</strong>
                    <br />
                    <small className="text-muted">
                      L*{target.lab_values?.L?.toFixed(2)} a*{target.lab_values?.a?.toFixed(2)} b*{target.lab_values?.b?.toFixed(2)}
                    </small>
                  </div>
                </div>
              )}

              <Button
                variant="primary" className="w-100"
                onClick={handleFormulate}
                disabled={!selectedSeries || !selectedTarget || formulating}
              >
                {formulating ? (
                  <><Spinner animation="border" size="sm" className="me-2" /> Formulating...</>
                ) : (
                  'Generate Formula'
                )}
              </Button>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          {result && (
            <Card>
              <Card.Header className="d-flex justify-content-between align-items-center">
                <strong>Formula Result</strong>
                <Link to={`/pantone/formulas/${result.id}`} className="btn btn-sm btn-outline-primary">
                  View Full Details
                </Link>
              </Card.Header>
              <Card.Body>
                <div className="d-flex align-items-center gap-3 mb-3">
                  <div className="color-swatch" style={{
                    backgroundColor: result.predicted_lab
                      ? labToApproxHex(result.predicted_lab.L, result.predicted_lab.a, result.predicted_lab.b)
                      : '#ccc',
                    width: 48, height: 48,
                  }} />
                  <div>
                    <span className={`delta-e-badge ${getDeltaEClass(result.delta_e_2000)}`}>
                      DE*00: {result.delta_e_2000?.toFixed(4)} — {getDeltaELabel(result.delta_e_2000)}
                    </span>
                    <br />
                    <small className="text-muted">
                      Predicted: L*{result.predicted_lab?.L?.toFixed(2)} a*{result.predicted_lab?.a?.toFixed(2)} b*{result.predicted_lab?.b?.toFixed(2)}
                    </small>
                  </div>
                </div>

                <Table size="sm" className="formula-table">
                  <thead>
                    <tr><th>Base</th><th>Name</th><th className="text-end">%</th><th className="text-end">g/kg</th></tr>
                  </thead>
                  <tbody>
                    {result.components?.map((c, i) => (
                      <tr key={i}>
                        <td><strong>{c.base_code}</strong></td>
                        <td>{c.base_name}</td>
                        <td className="text-end">{c.percentage?.toFixed(2)}</td>
                        <td className="text-end">{c.weight_grams?.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}

export default PantoneFormulate;
