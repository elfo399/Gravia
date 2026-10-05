import {
  ArrowDown,
  ArrowLeftRight,
  ArrowUp,
  ChartColumn,
  Info,
  Sigma,
  UserRound,
} from 'lucide-react';
import { useState } from 'react';
import { calculateWeightStatistics, formatWeight } from '../api/weightStatistics';
import { useGraviaData } from '../hooks/useGraviaData';
import { BmiRange } from './BmiRange';

export function DashboardSummary() {
  const { measurements, profileId } = useGraviaData();
  const [days, setDays] = useState(7);
  const readings = measurements.filter(
    (item) =>
      item.profileId === profileId &&
      Date.now() - new Date(item.measuredAt).getTime() <= days * 86400000,
  );
  const stats = calculateWeightStatistics(readings);
  const weights = readings.map((item) => item.weight);
  const change =
    readings.length >= 2 ? readings[0].weight - readings[readings.length - 1].weight : undefined;
  const cells = [
    {
      label: 'Peso medio',
      value: stats.average,
      detail: `Negli ultimi ${days} giorni`,
      icon: Sigma,
    },
    {
      label: 'Peso minimo',
      value: weights.length ? Math.min(...weights) : undefined,
      detail: 'Nel periodo selezionato',
      icon: ArrowDown,
    },
    {
      label: 'Peso massimo',
      value: weights.length ? Math.max(...weights) : undefined,
      detail: 'Nel periodo selezionato',
      icon: ArrowUp,
    },
    {
      label: 'Variazione',
      value: change,
      detail: 'Dalla prima all’ultima pesata',
      icon: ArrowLeftRight,
    },
  ];
  return (
    <section className="card summary-card">
      <div className="card-heading">
        <h2>
          <span className="heading-icon">
            <ChartColumn size={20} />
          </span>
          Statistiche
        </h2>
        <select
          aria-label="Periodo delle statistiche"
          className="summary-period"
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
        >
          {[7, 30, 90, 365].map((period) => (
            <option key={period} value={period}>
              {period === 365 ? 'Ultimo anno' : `Ultimi ${period} giorni`}
            </option>
          ))}
        </select>
      </div>
      <div className="summary-grid">
        {cells.map(({ label, value, detail, icon: Icon }) => (
          <div className="summary-tile" key={label}>
            <span>
              <Icon size={17} />
              {label}
            </span>
            <strong>
              {label === 'Variazione' && value !== undefined && value > 0 ? '+' : ''}
              {formatWeight(value)} <small>kg</small>
            </strong>
            <p>{detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function BmiCard() {
  const { measurements, profileId, profile } = useGraviaData();
  const stats = calculateWeightStatistics(
    measurements.filter((item) => item.profileId === profileId),
    profile?.heightCm,
  );
  return (
    <section className="card bmi-card">
      <div className="card-heading">
        <h2>
          <span className="heading-icon">
            <UserRound size={20} />
          </span>
          Indice di massa corporea
        </h2>
        <Info
          size={17}
          className="muted"
          aria-label="Calcolato dal peso più recente e dall’altezza del profilo"
        />
      </div>
      <div className="bmi-overview">
        <strong>
          {formatWeight(stats.bmi)}
          <span>BMI</span>
        </strong>
        <span className="bmi-caption">
          Peso e altezza,
          <br />
          in un solo indicatore.
        </span>
      </div>
      <div className="bmi-details">
        <span>
          Altezza <b>{profile?.heightCm ? `${profile.heightCm} cm` : '—'}</b>
        </span>
        <span>
          Ultimo peso <b>{formatWeight(stats.current)} kg</b>
        </span>
      </div>
      <BmiRange value={stats.bmi} />
    </section>
  );
}
