import { CheckCircle2 } from 'lucide-react';
import type { ActivitySession } from '../../types/ActivitySession';
import { exercises } from './activities';

export function TrainingResult({ session }: { session: ActivitySession }) {
  const result = session.resultJson ?? {};
  const metric = (key: string, digits = 0, suffix = '') =>
    result[key] == null
      ? '—'
      : `${Number(result[key]).toLocaleString('it-IT', { maximumFractionDigits: digits })}${suffix}`;
  const metrics =
    session.activityType === 'BALANCE_HOLD'
      ? [
          ['Tempo al centro', metric('centeredPercent', 0, '%')],
          ['Distanza media dal centro', metric('averageCenterDistance', 3)],
          ['Distanza massima', metric('maxCenterDistance', 3)],
        ]
      : session.activityType === 'SYMMETRY'
        ? [
            ['Media sinistra', metric('averageLeftPercent', 1, '%')],
            ['Media destra', metric('averageRightPercent', 1, '%')],
            ['Tempo in equilibrio', metric('balancedPercent', 0, '%')],
          ]
        : [
            ['Target raggiunti', `${metric('targetsReached')} / ${metric('targets')}`],
            ['Target mancati', metric('targetsMissed')],
            ['Reazione media', metric('averageReactionTime', 2, ' s')],
            ['Migliore reazione', metric('bestReactionTime', 2, ' s')],
          ];
  return (
    <section className="training-result" aria-label="Risultato Training">
      <CheckCircle2 className="result-check" size={32} />
      <h2>Un nuovo passo nel tuo equilibrio</h2>
      <p>Risultato salvato nel tuo storico Training.</p>
      <div className="training-final-score">
        {session.score}
        <span> / {exercises[session.activityType].maximum} punti</span>
      </div>
      <dl className="training-metrics">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="muted">
        Durata: {Math.round(session.durationSeconds)} secondi
        {session.activityType === 'BALANCE_HOLD' ? ' · Distanze normalizzate alla pedana' : ''}
      </p>
    </section>
  );
}
