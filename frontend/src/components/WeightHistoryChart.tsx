import { ChartNoAxesCombined } from 'lucide-react';
import { useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from '../hooks/useTheme';
import type { Measurement } from '../types/Measurement';
export function WeightHistoryChart({ measurements }: { measurements: Measurement[] }) {
  const [days, setDays] = useState(7);
  const { resolved } = useTheme();
  const dark = resolved === 'dark';
  const since = Date.now() - days * 86400000;
  const readings = measurements
    .filter((item) => new Date(item.measuredAt).getTime() >= since)
    .slice()
    .reverse()
    .map((item) => ({
      ...item,
      date: new Date(item.measuredAt).toLocaleDateString('it-IT', {
        day: 'numeric',
        month: 'short',
      }),
    }));
  return (
    <section className="card chart-card">
      <div className="card-heading">
        <div>
          <h2>
            <span className="heading-icon">
              <ChartNoAxesCombined size={20} />
            </span>
            Andamento del peso
          </h2>
        </div>
        <fieldset className="period-selector" aria-label="Periodo del grafico">
          {[7, 30, 90, 365].map((period) => (
            <button
              key={period}
              type="button"
              aria-pressed={days === period}
              className={days === period ? 'selected' : ''}
              onClick={() => setDays(period)}
            >
              {period === 90 ? '3 mesi' : period === 365 ? '1 anno' : `${period} giorni`}
            </button>
          ))}
        </fieldset>
      </div>
      {readings.length ? (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={readings} margin={{ top: 20, right: 16, left: -20, bottom: 0 }}>
              <CartesianGrid stroke={dark ? '#29374c' : '#e8eef7'} strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: dark ? '#a7b6cc' : '#657b9b', fontSize: 11 }}
                minTickGap={35}
              />
              <YAxis
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                axisLine={false}
                tickLine={false}
                tick={{ fill: dark ? '#a7b6cc' : '#657b9b', fontSize: 11 }}
                tickFormatter={(value) => value.toFixed(1)}
              />
              <Tooltip
                formatter={(value) => [`${Number(value).toFixed(1)} kg`, 'Peso']}
                contentStyle={{
                  borderRadius: 12,
                  border: '1px solid var(--border)',
                  background: 'var(--surface)',
                  color: 'var(--text)',
                }}
                itemStyle={{ color: 'var(--accent)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
              <Area
                type="monotone"
                dataKey="weight"
                stroke={dark ? '#6da6ff' : '#287bff'}
                strokeWidth={2.5}
                fill={dark ? '#1a3455' : '#dfedff'}
                dot={{
                  r: 4,
                  fill: dark ? '#6da6ff' : '#287bff',
                  stroke: dark ? '#172235' : 'white',
                  strokeWidth: 2,
                }}
                activeDot={{ r: 6 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-chart">
          <span className="empty-chart-line" />
          <strong>Il tuo percorso inizia qui</strong>
          <p>Completa una misurazione per vedere il tuo andamento.</p>
        </div>
      )}
      <div className="chart-footer">
        <span>
          <i className="legend-dot blue" />
          Peso in chilogrammi
        </span>
        <span>{readings.length} misurazioni nel periodo</span>
      </div>
    </section>
  );
}
