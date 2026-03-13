import React from 'react';
import { Card, Table, Badge } from 'react-bootstrap';

const RISK_COLORS = {
  low: 'success',
  moderate: 'warning',
  high: 'danger',
};

const ILLUMINANT_NAMES = {
  D50: 'D50 (Graphic Arts)',
  D65: 'D65 (Daylight)',
  A: 'A (Tungsten)',
};

const OBSERVER_LABELS = {
  '2': '2\u00b0',
  '10': '10\u00b0',
};

function MetamerismPanel({ metamerism }) {
  if (!metamerism || !metamerism.illuminants) return null;

  const observer = metamerism.observer || '2';
  const filter = metamerism.measurement_filter;

  return (
    <Card className="mt-3">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span>
          Multi-Illuminant Analysis
          <span className="text-muted ms-2 small">
            Observer: {OBSERVER_LABELS[observer] || observer}
            {filter && <> | Filter: {filter}</>}
          </span>
        </span>
        <Badge bg={RISK_COLORS[metamerism.metamerism_risk] || 'secondary'}>
          Metamerism Risk: {metamerism.metamerism_risk}
        </Badge>
      </Card.Header>
      <Card.Body className="p-0">
        <Table size="sm" className="mb-0">
          <thead>
            <tr>
              <th>Illuminant</th>
              <th>Target L*a*b*</th>
              <th>Predicted L*a*b*</th>
              <th>dE00</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(metamerism.illuminants).map(([ill, data]) => (
              <tr key={ill}>
                <td>{ILLUMINANT_NAMES[ill] || ill}</td>
                <td className="text-muted small">
                  {data.lab1.L.toFixed(1)}, {data.lab1.a.toFixed(1)}, {data.lab1.b.toFixed(1)}
                </td>
                <td className="text-muted small">
                  {data.lab2.L.toFixed(1)}, {data.lab2.a.toFixed(1)}, {data.lab2.b.toFixed(1)}
                </td>
                <td>
                  <Badge bg={data.delta_e_2000 <= 1 ? 'success' : data.delta_e_2000 <= 2 ? 'warning' : 'danger'}>
                    {data.delta_e_2000.toFixed(2)}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
        <div className="px-3 py-2 text-muted small">
          Max spread: {metamerism.max_spread.toFixed(2)} dE00
        </div>
      </Card.Body>
    </Card>
  );
}

export default MetamerismPanel;
