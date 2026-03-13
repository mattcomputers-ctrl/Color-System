import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const WAVELENGTHS = Array.from({ length: 43 }, (_, i) => 360 + i * 10);

function SpectralChart({ spectra, height = 300 }) {
  if (!spectra || spectra.length === 0) return null;

  const data = WAVELENGTHS.map((wl, i) => {
    const point = { wavelength: wl };
    spectra.forEach((s) => {
      if (s.values && s.values[i] !== undefined) {
        point[s.label] = parseFloat((s.values[i] * 100).toFixed(2));
      }
    });
    return point;
  });

  const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#9333ea', '#ea580c', '#0891b2'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="wavelength"
          label={{ value: 'Wavelength (nm)', position: 'insideBottom', offset: -5 }}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          label={{ value: 'Reflectance (%)', angle: -90, position: 'insideLeft', offset: 5 }}
          tick={{ fontSize: 11 }}
          domain={[0, 100]}
        />
        <Tooltip
          formatter={(value) => [`${value}%`, undefined]}
          labelFormatter={(wl) => `${wl} nm`}
        />
        {spectra.length > 1 && <Legend />}
        {spectra.map((s, idx) => (
          <Line
            key={s.label}
            type="monotone"
            dataKey={s.label}
            stroke={s.color || COLORS[idx % COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export default SpectralChart;
