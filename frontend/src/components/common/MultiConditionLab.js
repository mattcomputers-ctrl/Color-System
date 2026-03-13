import React from 'react';
import { Card, Table } from 'react-bootstrap';
import { labToApproxHex } from '../../utils/helpers';

function MultiConditionLab({ conditions, title }) {
  if (!conditions || conditions.length === 0) return null;

  return (
    <Card className="mt-3">
      <Card.Header><strong>{title || 'Multi-Condition LAB Values'}</strong></Card.Header>
      <Card.Body className="p-0">
        <Table size="sm" className="mb-0">
          <thead>
            <tr>
              <th style={{ width: 28 }}></th>
              <th>Illuminant</th>
              <th>Observer</th>
              <th>Filter</th>
              <th className="text-end">L*</th>
              <th className="text-end">a*</th>
              <th className="text-end">b*</th>
            </tr>
          </thead>
          <tbody>
            {conditions.map((c, i) => (
              <tr key={i}>
                <td>
                  <div style={{
                    backgroundColor: labToApproxHex(c.lab.L, c.lab.a, c.lab.b),
                    width: 20, height: 20, borderRadius: 3, border: '1px solid #dee2e6',
                  }} />
                </td>
                <td>{c.illuminant}</td>
                <td>{c.observer_label || `${c.observer}\u00b0`}</td>
                <td className="text-muted">{c.filter || '\u2014'}</td>
                <td className="text-end">{c.lab.L.toFixed(2)}</td>
                <td className="text-end">{c.lab.a.toFixed(2)}</td>
                <td className="text-end">{c.lab.b.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card.Body>
    </Card>
  );
}

export default MultiConditionLab;
