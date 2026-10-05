import { Layers, ScanLine } from 'lucide-react';
import { formatWeight } from '../api/weightStatistics';
import type { LiveMeasurement } from '../types/Measurement';

const sensors = [
  ['frontLeft', 'Anteriore sinistro'],
  ['frontRight', 'Anteriore destro'],
  ['rearLeft', 'Posteriore sinistro'],
  ['rearRight', 'Posteriore destro'],
] as const;

export function PressureSensorsCard({
  reading,
  live,
}: {
  reading: LiveMeasurement | null;
  live: boolean;
}) {
  return (
    <section className="card sensors-card" aria-label="Sensori di pressione">
      <div className="card-heading">
        <h2>
          <span className="heading-icon">
            <Layers size={20} />
          </span>
          Sensori di pressione
        </h2>
        <span className="card-context">
          {live ? 'Live' : reading ? 'Ultima pesata' : 'In attesa'}
        </span>
      </div>
      <div className="sensor-grid">
        {sensors.map(([key, label]) => {
          const value = reading?.sensors[key];
          const percent =
            reading && reading.weight > 0 && value !== undefined
              ? Math.max(0, Math.min(100, (value / reading.weight) * 100))
              : undefined;
          return (
            <div className="sensor-tile" key={key}>
              <span className="sensor-name">
                <ScanLine size={14} />
                {label}
              </span>
              <div className="sensor-value">
                <strong>
                  {formatWeight(value)} <small>kg</small>
                </strong>
                <span>{percent === undefined ? '—' : `${Math.round(percent)}%`}</span>
              </div>
              <meter
                className="reading-meter"
                aria-label={`Carico ${label.toLowerCase()}`}
                value={percent ?? 0}
                min={0}
                max={100}
                aria-valuetext={percent === undefined ? 'Nessun dato' : `${Math.round(percent)}%`}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
