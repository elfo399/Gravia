import { useId } from 'react';
import type { LiveMeasurement } from '../types/Measurement';
import { pressurePosition } from './pressurePosition';

export function PressureMap({
  reading,
  live = false,
}: {
  reading: LiveMeasurement | null;
  live?: boolean;
}) {
  const id = useId().replace(/:/g, '');
  const center = reading
    ? pressurePosition(reading.centerOfPressure, { x: 190, y: 117 }, { x: 114, y: 65 })
    : null;
  const positions = [
    { key: 'frontLeft', x: 91, y: 66 },
    { key: 'frontRight', x: 289, y: 66 },
    { key: 'rearLeft', x: 82, y: 166 },
    { key: 'rearRight', x: 298, y: 166 },
  ] as const;
  return (
    <figure className="board-figure">
      <svg
        viewBox="0 0 380 240"
        role="img"
        aria-label="Mappa dei quattro sensori e centro di pressione"
      >
        <title>Distribuzione del peso sulla Balance Board</title>
        <defs>
          <linearGradient id={`${id}-edge`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--board-edge-light)" />
            <stop offset="1" stopColor="var(--board-edge-dark)" />
          </linearGradient>
          <linearGradient id={`${id}-body`} x1="0" y1="0" x2="0.35" y2="1">
            <stop offset="0" stopColor="var(--board-light)" />
            <stop offset="0.52" stopColor="var(--board-mid)" />
            <stop offset="1" stopColor="var(--board-light)" />
          </linearGradient>
          <radialGradient id={`${id}-glow`}>
            <stop offset="0" stopColor="#3b96ff" stopOpacity="0.6" />
            <stop offset="1" stopColor="#3b96ff" stopOpacity="0" />
          </radialGradient>
          <pattern id={`${id}-texture`} width="5" height="5" patternUnits="userSpaceOnUse">
            <path d="M0 5L5 0" stroke="var(--board-grid)" strokeWidth="0.5" opacity="0.4" />
          </pattern>
          <filter id={`${id}-shadow`} x="-20%" y="-25%" width="140%" height="160%">
            <feDropShadow dx="0" dy="9" stdDeviation="7" floodColor="#07152b" floodOpacity="0.24" />
          </filter>
        </defs>
        <g filter={`url(#${id}-shadow)`}>
          <path
            d="M59 32Q190 18 321 32Q343 36 336 66L342 187Q345 207 318 215Q190 230 62 215Q35 207 38 187L44 66Q37 36 59 32Z"
            fill={`url(#${id}-edge)`}
          />
          <path
            d="M61 25Q190 13 319 25Q339 29 330 59L337 178Q343 202 313 206Q190 220 67 206Q37 202 43 178L50 59Q41 29 61 25Z"
            fill={`url(#${id}-body)`}
            stroke="var(--board-border)"
            strokeWidth="2"
          />
          <path
            d="M74 37Q190 29 306 37Q318 38 314 58L322 176Q324 189 305 192Q190 205 75 192Q56 189 58 176L66 58Q62 38 74 37Z"
            fill={`url(#${id}-texture)`}
            stroke="var(--board-border)"
          />
          <path d="M190 33v170M63 117h254" stroke="var(--board-grid)" strokeWidth="1" />
          {positions.map(({ key, x, y }) => {
            const fraction =
              reading && reading.weight > 0 ? reading.sensors[key] / reading.weight : 0;
            return (
              <g key={key}>
                <title>
                  {key}: {reading ? `${reading.sensors[key].toFixed(1)} kg` : 'nessun dato'}
                </title>
                <circle
                  cx={x}
                  cy={y}
                  r={reading ? 24 + fraction * 40 : 24}
                  fill={`url(#${id}-glow)`}
                  opacity={reading ? 1 : 0.35}
                />
                <circle cx={x} cy={y} r="9" fill={reading ? '#3995fa' : 'var(--board-idle)'} />
              </g>
            );
          })}
          {reading && reading.weight > 0 && (
            <circle
              cx={center?.x}
              cy={center?.y}
              r="6"
              fill="var(--board-cop)"
              stroke="var(--board-light)"
              strokeWidth="2"
            />
          )}
        </g>
      </svg>
      <figcaption>
        <strong>Distribuzione del peso e centro di pressione</strong>
        <span>
          Vista dall’alto ·{' '}
          {live
            ? 'Lettura in tempo reale'
            : reading
              ? 'Ultima pesata del profilo'
              : 'In attesa di una misurazione'}
        </span>
      </figcaption>
    </figure>
  );
}
