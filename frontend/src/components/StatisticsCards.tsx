import { ArrowLeftRight, ChartNoAxesCombined, Ruler, ScanLine } from 'lucide-react';
import { calculateWeightStatistics, formatWeight } from '../api/weightStatistics';
import { useGraviaData } from '../hooks/useGraviaData';
export function StatisticsCards() {
  const { measurements, profile, profileId } = useGraviaData();
  const stats = calculateWeightStatistics(
    measurements.filter((item) => item.profileId === profileId),
    profile?.heightCm,
  );
  const cards = [
    {
      label: 'Variazione',
      value:
        stats.change === undefined
          ? '—'
          : `${stats.change > 0 ? '+' : ''}${formatWeight(stats.change)}`,
      unit: 'kg',
      detail: 'Rispetto alla pesata precedente',
      icon: ArrowLeftRight,
    },
    {
      label: 'Peso medio',
      value: formatWeight(stats.average),
      unit: 'kg',
      detail: 'Tutte le tue misurazioni',
      icon: ChartNoAxesCombined,
    },
    {
      label: 'Indice di massa corporea',
      value: formatWeight(stats.bmi),
      unit: 'BMI',
      detail: profile?.heightCm
        ? `Calcolato su ${profile.heightCm} cm`
        : 'Aggiungi l’altezza al profilo',
      icon: Ruler,
    },
    {
      label: 'Misurazioni',
      value: String(stats.count),
      unit: '',
      detail: 'Passi verso la consapevolezza',
      icon: ScanLine,
    },
  ];
  return (
    <div className="statistics-grid">
      {cards.map(({ label, value, unit, detail, icon: Icon }) => (
        <section className="card statistic-card" key={label}>
          <div className="stat-label">
            {label}
            <Icon size={17} />
          </div>
          <div className="stat-value">
            {value}
            <span>{unit}</span>
          </div>
          <p>{detail}</p>
        </section>
      ))}
    </div>
  );
}
