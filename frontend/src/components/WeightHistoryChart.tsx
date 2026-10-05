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
import type { Measurement } from '../types/Measurement';
export function WeightHistoryChart({ measurements }: { measurements: Measurement[] }) {
  const [days, setDays] = useState(30);
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
          <h2>Ogni giorno, più consapevole</h2>
          <p>L’andamento del tuo peso nel tempo</p>
        </div>
        <fieldset className="period-selector" aria-label="Periodo del grafico">
          {[7, 30, 90].map((period) => (
            <button
              key={period}
              type="button"
              aria-pressed={days === period}
              className={days === period ? 'selected' : ''}
              onClick={() => setDays(period)}
            >
              {period} giorni
            </button>
          ))}
        </fieldset>
      </div>
      {readings.length ? (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={readings} margin={{ top: 20, right: 16, left: -20, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#edf1f5" />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#8793a6', fontSize: 12 }}
                minTickGap={35}
              />
              <YAxis
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#8793a6', fontSize: 12 }}
                tickFormatter={(value) => value.toFixed(1)}
              />
              <Tooltip
                formatter={(value) => [`${Number(value).toFixed(1)} kg`, 'Peso']}
                contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }}
              />
              <Area
                type="monotone"
                dataKey="weight"
                stroke="#2563eb"
                strokeWidth={2.5}
                fill="#eff6ff"
                dot={{ r: 4, fill: '#2563eb', stroke: 'white', strokeWidth: 2 }}
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
