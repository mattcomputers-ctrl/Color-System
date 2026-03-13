import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, Table, Button, Spinner, Row, Col, Badge } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { pantoneAPI, exportAPI } from '../../services/api';
import { labToApproxHex, getDeltaEClass, getDeltaELabel, formatDate, downloadBlob } from '../../utils/helpers';
import SpectralChart from '../common/SpectralChart';
import MetamerismPanel from '../common/MetamerismPanel';
import ObserverFilterSelect from '../common/ObserverFilterSelect';
import MultiConditionLab from '../common/MultiConditionLab';

function FormulaDetail() {
  const { id } = useParams();
  const [formula, setFormula] = useState(null);
  const [loading, setLoading] = useState(true);
  const [observer, setObserver] = useState('2');
  const [filter, setFilter] = useState(null);

  const fetchFormula = useCallback((obs, flt) => {
    const params = {};
    if (obs && obs !== '2') params.observer = obs;
    if (flt) params.filter = flt;
    return pantoneAPI.getFormula(id, { params })
      .then(res => setFormula(res.data.formula))
      .catch(() => toast.error('Failed to load formula'));
  }, [id]);

  useEffect(() => {
    fetchFormula(observer, filter)
      .finally(() => setLoading(false));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleObserverChange = (value) => {
    setObserver(value);
    fetchFormula(value, filter);
  };

  const handleFilterChange = (value) => {
    setFilter(value);
    fetchFormula(observer, value);
  };

  const handleApprove = async () => {
    try {
      const res = await pantoneAPI.approveFormula(formula.id);
      setFormula({ ...formula, ...res.data.formula });
      toast.success('Formula approved');
    } catch (err) {
      toast.error('Failed to approve formula');
    }
  };

  const handleExportPdf = async () => {
    try {
      const res = await exportAPI.pantoneFormulaPdf(formula.id);
      const target = formula.target || {};
      downloadBlob(new Blob([res.data]), `formula_${target.pantone_code || id}.pdf`);
    } catch (err) {
      toast.error('Failed to export PDF');
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;
  if (!formula) return <p>Formula not found.</p>;

  const target = formula.target || {};

  return (
    <div>
      <div className="page-header">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-1">
            <li className="breadcrumb-item"><Link to="/pantone/formulas">Formulas</Link></li>
            <li className="breadcrumb-item active">{target.pantone_code}</li>
          </ol>
        </nav>
        <div className="d-flex justify-content-between align-items-center">
          <h2>Formula: {target.pantone_code}</h2>
          <div>
            <Button variant="outline-secondary" className="me-2" onClick={handleExportPdf}>
              Export PDF
            </Button>
            {formula.status === 'generated' && (
              <Button variant="success" onClick={handleApprove}>Approve</Button>
            )}
          </div>
        </div>
      </div>

      <Row>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header><strong>Target</strong></Card.Header>
            <Card.Body>
              <div className="d-flex align-items-center gap-3 mb-3">
                <div className="color-swatch" style={{
                  backgroundColor: target.lab_values
                    ? labToApproxHex(target.lab_values.L, target.lab_values.a, target.lab_values.b)
                    : '#ccc',
                  width: 64, height: 64,
                }} />
                <div>
                  <strong>{target.pantone_code}</strong>
                  <br />
                  <small>{target.pantone_name}</small>
                </div>
              </div>
              {target.lab_values && (
                <Table size="sm" borderless>
                  <tbody>
                    <tr><td>L*</td><td className="text-end">{target.lab_values.L?.toFixed(2)}</td></tr>
                    <tr><td>a*</td><td className="text-end">{target.lab_values.a?.toFixed(2)}</td></tr>
                    <tr><td>b*</td><td className="text-end">{target.lab_values.b?.toFixed(2)}</td></tr>
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card className="mb-4">
            <Card.Header><strong>Predicted Result</strong></Card.Header>
            <Card.Body>
              <div className="d-flex align-items-center gap-3 mb-3">
                <div className="color-swatch" style={{
                  backgroundColor: formula.predicted_lab
                    ? labToApproxHex(formula.predicted_lab.L, formula.predicted_lab.a, formula.predicted_lab.b)
                    : '#ccc',
                  width: 64, height: 64,
                }} />
                <div>
                  <span className={`delta-e-badge ${getDeltaEClass(formula.delta_e_2000)}`}>
                    DE*00: {formula.delta_e_2000?.toFixed(4)}
                  </span>
                  <br />
                  <small className="text-muted">{getDeltaELabel(formula.delta_e_2000)}</small>
                </div>
              </div>
              {formula.predicted_lab && (
                <Table size="sm" borderless>
                  <tbody>
                    <tr><td>L*</td><td className="text-end">{formula.predicted_lab.L?.toFixed(2)}</td></tr>
                    <tr><td>a*</td><td className="text-end">{formula.predicted_lab.a?.toFixed(2)}</td></tr>
                    <tr><td>b*</td><td className="text-end">{formula.predicted_lab.b?.toFixed(2)}</td></tr>
                    <tr><td>DE*76</td><td className="text-end">{formula.delta_e_76?.toFixed(4)}</td></tr>
                    <tr><td>DE*00</td><td className="text-end">{formula.delta_e_2000?.toFixed(4)}</td></tr>
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card className="mb-4">
            <Card.Header><strong>Details</strong></Card.Header>
            <Card.Body>
              <Table size="sm" borderless>
                <tbody>
                  <tr><td>Series</td><td>{formula.series_name}</td></tr>
                  <tr><td>Version</td><td>v{formula.version}</td></tr>
                  <tr>
                    <td>Status</td>
                    <td><Badge className={`status-${formula.status}`}>{formula.status}</Badge></td>
                  </tr>
                  <tr><td>Generated by</td><td>{formula.generated_by || '—'}</td></tr>
                  <tr><td>Approved by</td><td>{formula.approved_by || '—'}</td></tr>
                  <tr><td>Generated</td><td className="small">{formatDate(formula.created_at)}</td></tr>
                  {formula.approved_at && (
                    <tr><td>Approved</td><td className="small">{formatDate(formula.approved_at)}</td></tr>
                  )}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card className="mb-4">
        <Card.Header><strong>Viewing Conditions</strong></Card.Header>
        <Card.Body>
          <ObserverFilterSelect
            observer={observer}
            filter={filter}
            onObserverChange={handleObserverChange}
            onFilterChange={handleFilterChange}
          />
        </Card.Body>
      </Card>

      {formula.multi_condition_lab && (
        <MultiConditionLab conditions={formula.multi_condition_lab} title="Multi-Condition LAB Values" />
      )}

      {/* Spectral Comparison Chart */}
      {(formula.predicted_spectral || target.spectral_reflectance) && (
        <Card className="mb-4">
          <Card.Header><strong>Spectral Reflectance</strong></Card.Header>
          <Card.Body>
            <SpectralChart
              spectra={[
                ...(target.spectral_reflectance ? [{ label: 'Target', values: target.spectral_reflectance, color: '#2563eb' }] : []),
                ...(formula.predicted_spectral ? [{ label: 'Predicted', values: formula.predicted_spectral, color: '#dc2626' }] : []),
              ]}
              height={300}
            />
          </Card.Body>
        </Card>
      )}

      {/* Metamerism Analysis */}
      {formula.metamerism && <MetamerismPanel metamerism={formula.metamerism} />}

      <Card className="mt-3">
        <Card.Header><strong>Formula Components</strong></Card.Header>
        <Card.Body className="p-0">
          <Table className="mb-0 formula-table">
            <thead>
              <tr>
                <th>Base Code</th><th>Base Name</th>
                <th className="text-end">Percentage (%)</th>
                <th className="text-end">Weight (g/kg)</th>
              </tr>
            </thead>
            <tbody>
              {formula.components?.map((c, i) => (
                <tr key={i}>
                  <td><strong>{c.base_code}</strong></td>
                  <td>{c.base_name}</td>
                  <td className="text-end">{c.percentage?.toFixed(2)}</td>
                  <td className="text-end">{c.weight_grams?.toFixed(1)}</td>
                </tr>
              ))}
              <tr className="fw-bold">
                <td colSpan={2}>Total</td>
                <td className="text-end">
                  {formula.components?.reduce((s, c) => s + (c.percentage || 0), 0).toFixed(2)}
                </td>
                <td className="text-end">
                  {formula.components?.reduce((s, c) => s + (c.weight_grams || 0), 0).toFixed(1)}
                </td>
              </tr>
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  );
}

export default FormulaDetail;
