import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Table, Badge, Spinner } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { adminAPI } from '../../services/api';
import { formatDate, getDeltaEClass } from '../../utils/helpers';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminAPI.getDashboardStats()
      .then(res => setStats(res.data))
      .catch(err => console.error('Failed to load dashboard stats:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center mt-5"><Spinner animation="border" /></div>;
  }

  if (!stats) return <p>Failed to load dashboard data.</p>;

  const statCards = [
    { label: 'Ink Series', value: stats.total_series, link: '/series' },
    { label: 'Mixing Bases', value: stats.total_bases, link: '/series' },
    { label: 'Pantone Targets', value: stats.total_pantone_targets, link: '/pantone/targets' },
    { label: 'Pantone Formulas', value: stats.total_pantone_formulas, link: '/pantone/formulas' },
    { label: 'Custom Matches', value: stats.total_custom_matches, link: '/custom-match' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
      </div>

      <Row className="mb-4">
        {statCards.map((s, i) => (
          <Col key={i} md={true} className="mb-3">
            <Link to={s.link} className="text-decoration-none">
              <Card className="stat-card p-3">
                <div className="stat-value">{s.value}</div>
                <div className="stat-label">{s.label}</div>
              </Card>
            </Link>
          </Col>
        ))}
      </Row>

      <Row>
        <Col md={6} className="mb-4">
          <Card>
            <Card.Header><strong>Recent Pantone Formulas</strong></Card.Header>
            <Card.Body className="p-0">
              {stats.recent_formulas?.length > 0 ? (
                <Table hover className="mb-0">
                  <thead>
                    <tr><th>Target</th><th>Series</th><th>DE*00</th><th>Date</th></tr>
                  </thead>
                  <tbody>
                    {stats.recent_formulas.map(f => (
                      <tr key={f.id}>
                        <td>
                          <Link to={`/pantone/formulas/${f.id}`}>{f.target_code}</Link>
                        </td>
                        <td>{f.series_name}</td>
                        <td>
                          <span className={`delta-e-badge ${getDeltaEClass(f.delta_e_2000)}`}>
                            {f.delta_e_2000?.toFixed(2) ?? '—'}
                          </span>
                        </td>
                        <td className="text-muted small">{formatDate(f.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <p className="text-muted p-3 mb-0">No formulas generated yet.</p>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={6} className="mb-4">
          <Card>
            <Card.Header><strong>Recent Custom Matches</strong></Card.Header>
            <Card.Body className="p-0">
              {stats.recent_matches?.length > 0 ? (
                <Table hover className="mb-0">
                  <thead>
                    <tr><th>Job</th><th>Series</th><th>DE*00</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {stats.recent_matches.map(j => (
                      <tr key={j.id}>
                        <td>
                          <Link to={`/custom-match/${j.id}`}>
                            {j.job_name || `Job #${j.id}`}
                          </Link>
                        </td>
                        <td>{j.series_name}</td>
                        <td>
                          <span className={`delta-e-badge ${getDeltaEClass(j.best_delta_e)}`}>
                            {j.best_delta_e?.toFixed(2) ?? '—'}
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
                <p className="text-muted p-3 mb-0">No custom matches yet.</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Dashboard;
