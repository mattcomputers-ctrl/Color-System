import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Spinner, Row, Col, Table, Tabs, Tab } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useDropzone } from 'react-dropzone';
import { customMatchAPI, seriesAPI } from '../../services/api';
import { labToApproxHex, getDeltaEClass, getDeltaELabel } from '../../utils/helpers';

function CustomMatchNew() {
  const navigate = useNavigate();
  const [series, setSeries] = useState([]);
  const [selectedSeries, setSelectedSeries] = useState('');
  const [mode, setMode] = useState('lab');
  const [labForm, setLabForm] = useState({
    lab_l: '', lab_a: '', lab_b: '',
    job_name: '', customer_name: '', project_name: '', notes: '',
  });
  const [cxfFile, setCxfFile] = useState(null);
  const [cxfMeta, setCxfMeta] = useState({ job_name: '', customer_name: '', project_name: '', notes: '' });
  const [matching, setMatching] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    seriesAPI.list({ active_only: 'true' }).then(res => setSeries(res.data.series));
  }, []);

  const handleLabMatch = async (e) => {
    e.preventDefault();
    if (!selectedSeries) { toast.warn('Please select an ink series'); return; }
    setMatching(true);
    setResult(null);
    try {
      const res = await customMatchAPI.matchFromLab({
        series_id: parseInt(selectedSeries),
        lab_l: parseFloat(labForm.lab_l),
        lab_a: parseFloat(labForm.lab_a),
        lab_b: parseFloat(labForm.lab_b),
        job_name: labForm.job_name,
        customer_name: labForm.customer_name,
        project_name: labForm.project_name,
        notes: labForm.notes,
      });
      setResult(res.data.job);
      toast.success('Color match completed');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Match failed');
    } finally {
      setMatching(false);
    }
  };

  const handleCxfMatch = async () => {
    if (!selectedSeries) { toast.warn('Please select an ink series'); return; }
    if (!cxfFile) { toast.warn('Please upload a CXF file'); return; }
    setMatching(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', cxfFile);
      formData.append('series_id', selectedSeries);
      Object.entries(cxfMeta).forEach(([k, v]) => { if (v) formData.append(k, v); });
      const res = await customMatchAPI.matchFromCxf(formData);
      setResult(res.data.job);
      toast.success('Color match completed');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Match failed');
    } finally {
      setMatching(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: files => setCxfFile(files[0]),
    accept: { 'application/xml': ['.cxf', '.xml'] },
    maxFiles: 1,
  });

  const bestResult = result?.results?.[0];

  return (
    <div>
      <div className="page-header"><h2>New Custom Color Match</h2></div>

      <Row>
        <Col md={6}>
          <Card className="mb-4">
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>Ink Series</Form.Label>
                <Form.Select value={selectedSeries} onChange={e => setSelectedSeries(e.target.value)}>
                  <option value="">Select an ink series...</option>
                  {series.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </Form.Select>
              </Form.Group>

              <Tabs activeKey={mode} onSelect={setMode} className="mb-3">
                <Tab eventKey="lab" title="Enter LAB Values">
                  <Form onSubmit={handleLabMatch}>
                    <Row className="mb-3">
                      <Col>
                        <Form.Label>L*</Form.Label>
                        <Form.Control type="number" step="0.01" required
                          value={labForm.lab_l}
                          onChange={e => setLabForm({ ...labForm, lab_l: e.target.value })}
                        />
                      </Col>
                      <Col>
                        <Form.Label>a*</Form.Label>
                        <Form.Control type="number" step="0.01" required
                          value={labForm.lab_a}
                          onChange={e => setLabForm({ ...labForm, lab_a: e.target.value })}
                        />
                      </Col>
                      <Col>
                        <Form.Label>b*</Form.Label>
                        <Form.Control type="number" step="0.01" required
                          value={labForm.lab_b}
                          onChange={e => setLabForm({ ...labForm, lab_b: e.target.value })}
                        />
                      </Col>
                    </Row>
                    {labForm.lab_l && (
                      <div className="mb-3 d-flex align-items-center gap-2">
                        <span>Preview:</span>
                        <div className="color-swatch" style={{
                          backgroundColor: labToApproxHex(
                            parseFloat(labForm.lab_l) || 50,
                            parseFloat(labForm.lab_a) || 0,
                            parseFloat(labForm.lab_b) || 0
                          ),
                          width: 40, height: 40,
                        }} />
                      </div>
                    )}
                    <Form.Group className="mb-3">
                      <Form.Label>Job Name</Form.Label>
                      <Form.Control value={labForm.job_name}
                        onChange={e => setLabForm({ ...labForm, job_name: e.target.value })} />
                    </Form.Group>
                    <Row className="mb-3">
                      <Col>
                        <Form.Label>Customer</Form.Label>
                        <Form.Control value={labForm.customer_name}
                          onChange={e => setLabForm({ ...labForm, customer_name: e.target.value })} />
                      </Col>
                      <Col>
                        <Form.Label>Project</Form.Label>
                        <Form.Control value={labForm.project_name}
                          onChange={e => setLabForm({ ...labForm, project_name: e.target.value })} />
                      </Col>
                    </Row>
                    <Form.Group className="mb-3">
                      <Form.Label>Notes</Form.Label>
                      <Form.Control as="textarea" rows={2} value={labForm.notes}
                        onChange={e => setLabForm({ ...labForm, notes: e.target.value })} />
                    </Form.Group>
                    <Button type="submit" variant="primary" className="w-100" disabled={matching}>
                      {matching ? <><Spinner animation="border" size="sm" className="me-2" />Matching...</> : 'Find Match'}
                    </Button>
                  </Form>
                </Tab>

                <Tab eventKey="cxf" title="Upload CXF File">
                  <div {...getRootProps()} className={`border border-2 rounded p-4 text-center mb-3 ${isDragActive ? 'border-primary bg-light' : ''}`} style={{ cursor: 'pointer' }}>
                    <input {...getInputProps()} />
                    {cxfFile
                      ? <p className="mb-0">{cxfFile.name}</p>
                      : <p className="mb-0 text-muted">Drop CXF file here or click to select</p>
                    }
                  </div>
                  <Form.Group className="mb-3">
                    <Form.Label>Job Name</Form.Label>
                    <Form.Control value={cxfMeta.job_name}
                      onChange={e => setCxfMeta({ ...cxfMeta, job_name: e.target.value })} />
                  </Form.Group>
                  <Row className="mb-3">
                    <Col>
                      <Form.Label>Customer</Form.Label>
                      <Form.Control value={cxfMeta.customer_name}
                        onChange={e => setCxfMeta({ ...cxfMeta, customer_name: e.target.value })} />
                    </Col>
                    <Col>
                      <Form.Label>Project</Form.Label>
                      <Form.Control value={cxfMeta.project_name}
                        onChange={e => setCxfMeta({ ...cxfMeta, project_name: e.target.value })} />
                    </Col>
                  </Row>
                  <Button variant="primary" className="w-100" disabled={matching || !cxfFile} onClick={handleCxfMatch}>
                    {matching ? <><Spinner animation="border" size="sm" className="me-2" />Matching...</> : 'Find Match from CXF'}
                  </Button>
                </Tab>
              </Tabs>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          {result && bestResult && (
            <Card>
              <Card.Header className="d-flex justify-content-between">
                <strong>Best Match Result</strong>
                <Button size="sm" variant="outline-primary" onClick={() => navigate(`/custom-match/${result.id}`)}>
                  Full Details
                </Button>
              </Card.Header>
              <Card.Body>
                <div className="d-flex align-items-center gap-3 mb-3">
                  <div className="color-swatch" style={{
                    backgroundColor: bestResult.predicted_lab
                      ? labToApproxHex(bestResult.predicted_lab.L, bestResult.predicted_lab.a, bestResult.predicted_lab.b)
                      : '#ccc',
                    width: 48, height: 48,
                  }} />
                  <div>
                    <span className={`delta-e-badge ${getDeltaEClass(bestResult.delta_e_2000)}`}>
                      DE*00: {bestResult.delta_e_2000?.toFixed(4)} — {getDeltaELabel(bestResult.delta_e_2000)}
                    </span>
                  </div>
                </div>
                <Table size="sm" className="formula-table">
                  <thead><tr><th>Base</th><th>Name</th><th className="text-end">%</th><th className="text-end">g/kg</th></tr></thead>
                  <tbody>
                    {bestResult.components?.map((c, i) => (
                      <tr key={i}>
                        <td><strong>{c.base_code}</strong></td>
                        <td>{c.base_name}</td>
                        <td className="text-end">{c.percentage?.toFixed(2)}</td>
                        <td className="text-end">{c.weight_grams?.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
                {result.results?.length > 1 && (
                  <p className="text-muted small mt-2">
                    {result.results.length} alternative formulas available — view full details for all options.
                  </p>
                )}
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}

export default CustomMatchNew;
