import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Table, Badge, Spinner } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { adminAPI } from '../../services/api';
import { formatDate, getDeltaEClass } from '../../utils/helpers';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    adminAPI.getDashboardStats()
      .then(res => setStats(res.data))
      .catch(err => {
        console.error('Failed to load dashboard stats:', err);
        setError(err.serverMessage || err.response?.data?.error || 'Failed to connect to server');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="page-spinner"><Spinner animation="border" variant="primary" /></div>;
  }

  if (!stats) return (
    <div className="empty-state">
      <div className="empty-icon">!</div>
      <h6>Unable to load dashboard</h6>
      <p>{error || 'Please check that the server is running and refresh the page.'}</p>
      <p className="text-muted" style={{ fontSize: '0.8125rem' }}>
        Check: <code>sudo systemctl status colorformulation</code> and <code>sudo systemctl status postgresql</code>
      </p>
    </div>
  );

  const statCards = [
    { label: 'Ink Series', value: stats.total_series, link: '/series', color: '#3b82f6', bg: '#eff6ff' },
    { label: 'Mixing Bases', value: stats.total_bases, link: '/series', color: '#8b5cf6', bg: '#f5f3ff' },
    { label: 'Pantone Targets', value: stats.total_pantone_targets, link: '/pantone/targets', color: '#f59e0b', bg: '#fffbeb' },
    { label: 'Formulas', value: stats.total_pantone_formulas, link: '/pantone/formulas', color: '#10b981', bg: '#ecfdf5' },
    { label: 'Custom Matches', value: stats.total_custom_matches, link: '/custom-match', color: '#ec4899', bg: '#fdf2f8' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
      </div>

      <Row className="g-3 mb-4">
        {statCards.map((s, i) => (
          <Col key={i} xs={6} lg={true}>
            <Link to={s.link} className="text-decoration-none">
              <Card className="stat-card">
                <div className="stat-icon" style={{ backgroundColor: s.bg, color: s.color }}>
                  {s.label.charAt(0)}
                </div>
                <div className="stat-value">{s.value}</div>
                <div className="stat-label">{s.label}</div>
              </Card>
            </Link>
          </Col>
        ))}
      </Row>

      <Row className="g-4">
        <Col lg={6}>
          <Card>
            <Card.Header className="d-flex justify-content-between align-items-center">
              <strong>Recent Formulas</strong>
              <Link to="/pantone/formulas" className="text-decoration-none" style={{ fontSize: '0.8125rem' }}>
                View all
              </Link>
            </Card.Header>
            <Card.Body className="p-0">
              {stats.recent_formulas?.length > 0 ? (
                <Table hover className="mb-0">
                  <thead>
                    <tr>
                      <th>Target</th>
                      <th>Series</th>
                      <th>dE*00</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_formulas.map(f => (
                      <tr key={f.id}>
                        <td>
                          <Link to={`/pantone/formulas/${f.id}`} className="fw-medium text-decoration-none">
                            {f.target_code}
                          </Link>
                        </td>
                        <td className="text-muted">{f.series_name}</td>
                        <td>
                          <span className={`delta-e-badge ${getDeltaEClass(f.delta_e_2000)}`}>
                            {f.delta_e_2000?.toFixed(2) ?? '--'}
                          </span>
                        </td>
                        <td className="text-muted">{formatDate(f.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <div className="empty-state">
                  <h6>No formulas yet</h6>
                  <p>Generate your first Pantone formula to see results here.</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={6}>
          <Card>
            <Card.Header className="d-flex justify-content-between align-items-center">
              <strong>Recent Matches</strong>
              <Link to="/custom-match" className="text-decoration-none" style={{ fontSize: '0.8125rem' }}>
                View all
              </Link>
            </Card.Header>
            <Card.Body className="p-0">
              {stats.recent_matches?.length > 0 ? (
                <Table hover className="mb-0">
                  <thead>
                    <tr>
                      <th>Job</th>
                      <th>Series</th>
                      <th>dE*00</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_matches.map(j => (
                      <tr key={j.id}>
                        <td>
                          <Link to={`/custom-match/${j.id}`} className="fw-medium text-decoration-none">
                            {j.job_name || `Job #${j.id}`}
                          </Link>
                        </td>
                        <td className="text-muted">{j.series_name}</td>
                        <td>
                          <span className={`delta-e-badge ${getDeltaEClass(j.best_delta_e)}`}>
                            {j.best_delta_e?.toFixed(2) ?? '--'}
                          </span>
                        </td>
                        <td>
                          <Badge bg={j.status === 'completed' ? 'success' : 'secondary'}>
                            {j.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <div className="empty-state">
                  <h6>No custom matches yet</h6>
                  <p>Create a new color match to see results here.</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Dashboard;
