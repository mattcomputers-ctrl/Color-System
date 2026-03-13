import React from 'react';
import { Form, Row, Col } from 'react-bootstrap';

function ObserverFilterSelect({ observer, filter, onObserverChange, onFilterChange, compact = false }) {
  const colSize = compact ? 6 : 3;

  return (
    <Row className="mb-3 align-items-end">
      <Col md={colSize}>
        <Form.Group>
          <Form.Label className="small mb-1">Observer</Form.Label>
          <Form.Select size="sm" value={observer || '2'} onChange={e => onObserverChange(e.target.value)}>
            <option value="2">2° (CIE 1931)</option>
            <option value="10">10° (CIE 1964)</option>
          </Form.Select>
        </Form.Group>
      </Col>
      <Col md={colSize}>
        <Form.Group>
          <Form.Label className="small mb-1">Measurement Filter</Form.Label>
          <Form.Select size="sm" value={filter || ''} onChange={e => onFilterChange(e.target.value || null)}>
            <option value="">None</option>
            <option value="M0">M0 — No UV control</option>
            <option value="M1">M1 — D50 with UV (ISO 13655)</option>
            <option value="M2">M2 — UV excluded</option>
            <option value="M3">M3 — Polarized</option>
          </Form.Select>
        </Form.Group>
      </Col>
    </Row>
  );
}

export default ObserverFilterSelect;
