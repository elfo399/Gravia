import type { ActivityReading } from '../../types/ActivitySession';
import { pressurePosition } from '../pressurePosition';
import { directions } from './activities';

export function BalanceTarget({
  reading,
  shift = false,
}: {
  reading: ActivityReading | null;
  shift?: boolean;
}) {
  const point = reading?.centerOfPressure;
  const position = point ? pressurePosition(point, { x: 150, y: 150 }, { x: 100, y: 100 }) : null;
  const target = shift ? reading?.data.target : { x: 0, y: 0 };
  const direction = shift ? reading?.data.direction : null;
  const radius = shift
    ? (reading?.data.targetRadius ?? 0.18)
    : (reading?.data.centerRadius ?? 0.15);
  return (
    <figure className="balance-target">
      <svg
        viewBox="0 0 300 300"
        role="img"
        aria-label={
          shift
            ? `Target: ${direction ? directions[direction] : 'in attesa'}`
            : 'Centro di pressione e zona centrale'
        }
      >
        <rect x="35" y="35" width="230" height="230" rx="42" className="target-board" />
        <circle cx="150" cy="150" r="85" className="target-guide" />
        <path d="M50 150H250M150 50V250" className="target-guide" />
        {shift &&
          Object.entries(directions).map(([key, label]) => (
            <text
              key={key}
              x={key === 'LEFT' ? 32 : key === 'RIGHT' ? 268 : 150}
              y={key === 'FRONT' ? 22 : key === 'REAR' ? 290 : 155}
              textAnchor="middle"
              className={direction === key ? 'target-label selected' : 'target-label'}
            >
              {label}
            </text>
          ))}
        {target && (
          <circle
            cx={150 + target.x * 100}
            cy={150 - target.y * 100}
            r={radius * 100}
            className="target-zone"
          />
        )}
        {point && <circle cx={position?.x} cy={position?.y} r="6" className="target-point" />}
      </svg>
      <figcaption>
        {point
          ? 'Il punto rappresenta il tuo centro di pressione'
          : 'Il punto apparirà quando inizierà l’attività'}
      </figcaption>
    </figure>
  );
}
