import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Form, Spinner, Badge, InputGroup, Row, Col } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { customMatchAPI, seriesAPI } from '../../services/api';
import { getDeltaEClass, formatDate, labToApproxHex } from '../../utils/helpers';

function CustomMatchList() {
  const [jobs, setJobs] = useState([]);
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [seriesFilter, setSeriesFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    seriesAPI.list({ active_only: 'true' }).then(res => setSeries(res.data.series));
  }, []);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const params = { search, page, per_page: 25 };
      if (seriesFilter) params.series_id = seriesFilter;
      const res = await customMatchAPI.listJobs(params);
      setJobs(res.data.jobs);
      setTotalPages(res.data.pages);
    } catch (err) {
      toast.error('Failed to load match jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadJobs(); }, [search, seriesFilter, page]);

  return (
    <div>
      <div className="page-header d-flex justify-content-between align-items-center">
        <div>
          <h2>Custom Match History</h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>Previous color matching jobs and results</p>
        </div>
        <Link to="/custom-match/new" className="btn btn-primary">+ New Match</Link>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <Row>
            <Col md={8}>
              <InputGroup>
                <Form.Control placeholder="Search by job name, customer, or project..."
                  value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
              </InputGroup>
            </Col>
            <Col md={4}>
              <Form.Select value={seriesFilter} onChange={e => { setSeriesFilter(e.target.value); setPage(1); }}>
                <option value="">All Series</option>
                {series.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
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
            <Table hover className="mb-0">
              <thead>
                <tr>
                  <th>Color</th><th>Job Name</th><th>Customer</th><th>Series</th>
                  <th>Source</th><th>DE*00</th><th>Status</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(j => (
                  <tr key={j.id}>
                    <td>
                      <div className="color-swatch" style={{
                        backgroundColor: j.target_lab
                          ? labToApproxHex(j.target_lab.L, j.target_lab.a, j.target_lab.b)
                          : '#ccc'
                      }} />
                    </td>
                    <td><Link to={`/custom-match/${j.id}`}><strong>{j.job_name || `Job #${j.id}`}</strong></Link></td>
                    <td>{j.customer_name || '—'}</td>
                    <td>{j.series_name}</td>
                    <td><Badge bg="light" text="dark">{j.target_source_type?.toUpperCase()}</Badge></td>
                    <td>
                      <span className={`delta-e-badge ${getDeltaEClass(j.best_delta_e)}`}>
                        {j.best_delta_e?.toFixed(2) ?? '—'}
                      </span>
                    </td>
                    <td>
                      <Badge bg={j.status === 'completed' ? 'success' : j.status === 'failed' ? 'danger' : 'secondary'}>
                        {j.status}
                      </Badge>
                    </td>
                    <td className="text-muted small">{formatDate(j.created_at)}</td>
                  </tr>
                ))}
                {jobs.length === 0 && (
                  <tr><td colSpan="8" className="text-center text-muted p-4">No match jobs found.</td></tr>
                )}
              </tbody>
            </Table>
          )}
        </Card.Body>
        {totalPages > 1 && (
          <Card.Footer className="d-flex justify-content-between">
            <Button variant="outline-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
            <span className="align-self-center">Page {page} of {totalPages}</span>
            <Button variant="outline-secondary" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
          </Card.Footer>
        )}
      </Card>
    </div>
  );
}

export default CustomMatchList;
