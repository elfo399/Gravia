import { Crosshair } from 'lucide-react';
import type { LiveMeasurement } from '../types/Measurement';
export function PressureMap({ reading }: { reading: LiveMeasurement | null }) {
  const sensors = reading?.sensors;
  const total = reading?.weight || 0;
  const positions = [
    { key: 'frontLeft', x: 72, y: 60 },
    { key: 'frontRight', x: 268, y: 60 },
    { key: 'rearLeft', x: 72, y: 168 },
    { key: 'rearRight', x: 268, y: 168 },
  ] as const;
  return (
    <section className="card pressure-card">
      <div className="card-heading">
        <div>
          <h2>Il tuo equilibrio</h2>
          <p>Distribuzione del peso in tempo reale</p>
        </div>
        <Crosshair size={20} className="muted" />
      </div>
      <svg
        viewBox="0 0 340 228"
        role="img"
        aria-label="Mappa dei quattro sensori e centro di pressione"
      >
        <title>Mappa di pressione Balance Board</title>
        <text x="170" y="18" textAnchor="middle" className="board-direction">
          FRONTE
        </text>
        <rect
          x="30"
          y="30"
          width="280"
          height="168"
          rx="28"
          fill="#f5f8fc"
          stroke="#e2e8f0"
          strokeWidth="2"
        />
        <path d="M170 42v144M43 114h254" stroke="#dbe3ed" strokeDasharray="4 5" />
        {positions.map(({ key, x, y }) => (
          <g key={key}>
            <title>
              {key}: {sensors ? `${sensors[key].toFixed(1)} kg` : 'nessun carico'}
            </title>
            <circle
              cx={x}
              cy={y}
              r={total ? 15 + ((sensors?.[key] || 0) / total) * 25 : 18}
              fill="#dbeafe"
            />
            <circle cx={x} cy={y} r="7" fill={total ? '#3b82f6' : '#b8c9e2'} />
            <text x={x} y={y + 34} textAnchor="middle" className="sensor-label">
              {sensors ? `${sensors[key].toFixed(1)} kg` : '—'}
            </text>
          </g>
        ))}
        <circle
          cx={170 + (reading?.centerOfPressure.x || 0) * 120}
          cy={114 - (reading?.centerOfPressure.y || 0) * 65}
          r="9"
          fill="#172b4d"
          stroke="white"
          strokeWidth="3"
        />
        <text x="170" y="222" textAnchor="middle" className="board-direction">
          RETRO
        </text>
      </svg>
      <div className="pressure-legend">
        <span>
          <i className="legend-dot blue" />
          Carico sui sensori
        </span>
        <span>
          <i className="legend-dot dark" />
          Centro di pressione
        </span>
      </div>
      <div className="pressure-summary">
        <span>
          Sinistra{' '}
          <strong>
            {total && sensors
              ? Math.round(((sensors.frontLeft + sensors.rearLeft) / total) * 100)
              : '—'}
            {total ? '%' : ''}
          </strong>
        </span>
        <span>
          Destra{' '}
          <strong>
            {total && sensors
              ? Math.round(((sensors.frontRight + sensors.rearRight) / total) * 100)
              : '—'}
            {total ? '%' : ''}
          </strong>
        </span>
      </div>
    </section>
  );
}
