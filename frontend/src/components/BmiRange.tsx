import type { CSSProperties } from 'react';
import { formatWeight } from '../api/weightStatistics';

// Adult screening ranges: https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html
const ranges = [
  { label: 'Sottopeso', interval: '< 18,5', color: 'blue' },
  { label: 'Normopeso', interval: '18,5 – < 25', color: 'green' },
  { label: 'Sovrappeso', interval: '25 – < 30', color: 'amber' },
  { label: 'Obesità', interval: '≥ 30', color: 'red' },
] as const;

export function BmiRange({ value }: { value?: number }) {
  const valid = value !== undefined && Number.isFinite(value) && value > 0;
  const category = valid ? (value < 18.5 ? 0 : value < 25 ? 1 : value < 30 ? 2 : 3) : undefined;
  // The visible scale spans 10–40; values outside it stay at the corresponding end.
  const position = valid ? Math.max(0, Math.min(100, ((value - 10) / 30) * 100)) : 0;
  return (
    <figure className="bmi-range" aria-label="Range BMI per adulti">
      <div className="bmi-scale" aria-hidden="true">
        {ranges.map((range) => (
          <span key={range.color} className={`bmi-segment ${range.color}`} />
        ))}
        {valid && (
          <span
            className="bmi-marker"
            style={{ '--bmi-position': `${position}%` } as CSSProperties}
          />
        )}
      </div>
      <div className="bmi-range-labels">
        {ranges.map((range, index) => (
          <span key={range.label} className={index === category ? 'current' : ''}>
            <b>{range.interval}</b>
            {range.label}
          </span>
        ))}
      </div>
      <figcaption className="sr-only">
        {valid
          ? `BMI ${formatWeight(value)}: ${ranges[category ?? 0].label}. `
          : 'BMI non disponibile. '}
        Range di riferimento per adulti.
      </figcaption>
    </figure>
  );
}
