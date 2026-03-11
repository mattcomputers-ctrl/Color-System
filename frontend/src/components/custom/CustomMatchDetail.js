import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, Table, Button, Spinner, Row, Col, Badge } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { customMatchAPI, exportAPI } from '../../services/api';
import { labToApproxHex, getDeltaEClass, getDeltaELabel, formatDate, downloadBlob } from '../../utils/helpers';

function CustomMatchDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    customMatchAPI.getJob(id)
      .then(res => setJob(res.data.job))
      .catch(() => toast.error('Failed to load match job'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleExportPdf = async () => {
    try {
      const res = await exportAPI.customMatchPdf(job.id);
      downloadBlob(new Blob([res.data]), `custom_match_${job.id}.pdf`);
    } catch (err) {
      toast.error('Failed to export PDF');
    }
  };

  if (loading) return <div className="text-center mt-5"><Spinner animation="border" /></div>;
  if (!job) return <p>Match job not found.</p>;

  return (
    <div>
      <div className="page-header">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-1">
            <li className="breadcrumb-item"><Link to="/custom-match">Match History</Link></li>
            <li className="breadcrumb-item active">{job.job_name || `Job #${job.id}`}</li>
          </ol>
        </nav>
        <div className="d-flex justify-content-between align-items-center">
          <h2>{job.job_name || `Custom Match #${job.id}`}</h2>
          <Button variant="outline-secondary" onClick={handleExportPdf}>Export PDF</Button>
        </div>
      </div>

      <Row className="mb-4">
        <Col md={4}>
          <Card>
            <Card.Header><strong>Job Details</strong></Card.Header>
            <Card.Body>
              <Table size="sm" borderless>
                <tbody>
                  <tr><td>Series</td><td>{job.series_name}</td></tr>
                  <tr><td>Customer</td><td>{job.customer_name || '—'}</td></tr>
                  <tr><td>Project</td><td>{job.project_name || '—'}</td></tr>
                  <tr><td>Source</td><td><Badge bg="light" text="dark">{job.target_source_type?.toUpperCase()}</Badge></td></tr>
                  <tr><td>Status</td><td><Badge bg={job.status === 'completed' ? 'success' : 'secondary'}>{job.status}</Badge></td></tr>
                  <tr><td>Created by</td><td>{job.created_by}</td></tr>
                  <tr><td>Date</td><td className="small">{formatDate(job.created_at)}</td></tr>
                </tbody>
              </Table>
              {job.notes && <p className="small text-muted">{job.notes}</p>}
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card>
            <Card.Header><strong>Target Color</strong></Card.Header>
            <Card.Body className="text-center">
              <div className="color-swatch mx-auto mb-3" style={{
                backgroundColor: job.target_lab
                  ? labToApproxHex(job.target_lab.L, job.target_lab.a, job.target_lab.b)
                  : '#ccc',
                width: 80, height: 80,
              }} />
              {job.target_lab && (
                <p>L*{job.target_lab.L?.toFixed(2)} a*{job.target_lab.a?.toFixed(2)} b*{job.target_lab.b?.toFixed(2)}</p>
              )}
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          {job.results?.[0] && (
            <Card>
              <Card.Header><strong>Best Match</strong></Card.Header>
              <Card.Body className="text-center">
                <div className="color-swatch mx-auto mb-3" style={{
                  backgroundColor: job.results[0].predicted_lab
                    ? labToApproxHex(job.results[0].predicted_lab.L, job.results[0].predicted_lab.a, job.results[0].predicted_lab.b)
                    : '#ccc',
                  width: 80, height: 80,
                }} />
                <span className={`delta-e-badge ${getDeltaEClass(job.results[0].delta_e_2000)}`}>
                  DE*00: {job.results[0].delta_e_2000?.toFixed(4)}
                </span>
                <br />
                <small className="text-muted">{getDeltaELabel(job.results[0].delta_e_2000)}</small>
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>

      {job.closest_pantone?.length > 0 && (
        <Card className="mb-4">
          <Card.Header><strong>Closest Pantone Colors</strong></Card.Header>
          <Card.Body className="p-0">
            <Table className="mb-0">
              <thead>
                <tr>
                  <th style={{ width: 40 }}></th>
                  <th>Pantone Code</th>
                  <th>Name</th>
                  <th>Library</th>
                  <th className="text-end">L*</th>
                  <th className="text-end">a*</th>
                  <th className="text-end">b*</th>
                  <th className="text-end">dE*00</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {job.closest_pantone.map((p, i) => (
                  <tr key={i}>
                    <td>
                      <div style={{
                        backgroundColor: labToApproxHex(p.lab.L, p.lab.a, p.lab.b),
                        width: 28, height: 28, borderRadius: 4, border: '1px solid #dee2e6',
                      }} />
                    </td>
                    <td><strong>{p.pantone_code}</strong></td>
                    <td className="small">{p.pantone_name}</td>
                    <td className="small text-muted">{p.library}</td>
                    <td className="text-end">{p.lab.L?.toFixed(2)}</td>
                    <td className="text-end">{p.lab.a?.toFixed(2)}</td>
                    <td className="text-end">{p.lab.b?.toFixed(2)}</td>
                    <td className="text-end">
                      <span className={`delta-e-badge ${getDeltaEClass(p.delta_e_2000)}`}>
                        {p.delta_e_2000?.toFixed(4)}
                      </span>
                    </td>
                    <td className="small text-muted">{getDeltaELabel(p.delta_e_2000)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card.Body>
        </Card>
      )}

      {job.results?.map((result, ri) => (
        <Card className="mb-3" key={result.id}>
          <Card.Header>
            <strong>Formula #{ri + 1}</strong>
            <span className={`ms-3 delta-e-badge ${getDeltaEClass(result.delta_e_2000)}`}>
              DE*00: {result.delta_e_2000?.toFixed(4)}
            </span>
          </Card.Header>
          <Card.Body className="p-0">
            <Table className="mb-0 formula-table">
              <thead><tr><th>Base Code</th><th>Base Name</th><th className="text-end">%</th><th className="text-end">g/kg</th></tr></thead>
              <tbody>
                {result.components?.map((c, ci) => (
                  <tr key={ci}>
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
      ))}
    </div>
  );
}

export default CustomMatchDetail;
