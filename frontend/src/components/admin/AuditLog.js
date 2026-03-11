import React, { useState, useEffect } from 'react';
import { Card, Table, Spinner, Button, Form, Row, Col } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { adminAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';

function AuditLog() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [actionFilter, setActionFilter] = useState('');

  const loadLog = async () => {
    setLoading(true);
    try {
      const params = { page, per_page: 50 };
      if (actionFilter) params.action = actionFilter;
      const res = await adminAPI.getAuditLog(params);
      setEntries(res.data.entries);
      setTotalPages(res.data.pages);
    } catch (err) {
      toast.error('Failed to load audit log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadLog(); }, [page, actionFilter]);

  return (
    <div>
      <div className="page-header"><h2>Audit Log</h2></div>

      <Card className="mb-3">
        <Card.Body>
          <Row>
            <Col md={4}>
              <Form.Select value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(1); }}>
                <option value="">All Actions</option>
                <option value="login">Login</option>
                <option value="create_series">Create Series</option>
                <option value="create_base">Create Base</option>
                <option value="upload_cxf">Upload CXF</option>
                <option value="generate_pantone_formula">Generate Formula</option>
                <option value="approve_pantone_formula">Approve Formula</option>
                <option value="custom_match_lab">Custom Match (LAB)</option>
                <option value="custom_match_cxf">Custom Match (CXF)</option>
                <option value="create_user">Create User</option>
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
              <thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead>
              <tbody>
                {entries.map(e => (
                  <tr key={e.id}>
                    <td className="small">{formatDate(e.created_at)}</td>
                    <td>{e.user || '—'}</td>
                    <td><code>{e.action}</code></td>
                    <td>{e.entity_type ? `${e.entity_type} #${e.entity_id || ''}` : '—'}</td>
                    <td className="small text-muted">
                      {e.details ? JSON.stringify(e.details).substring(0, 100) : '—'}
                    </td>
                  </tr>
                ))}
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

export default AuditLog;
