import { ArrowUpRight, Check, Scale, X } from 'lucide-react';
import { formatDate, formatWeight } from '../api/weightStatistics';
import { useGraviaData } from '../hooks/useGraviaData';
import { useMeasurementSession } from '../hooks/useMeasurementSession';
import { activeStatuses } from '../types/MeasurementSession';
import { MeasurementStatus } from './MeasurementStatus';
import { Button } from './ui/Button';

export function CurrentWeightCard() {
  const { profile, profileId, measurements, live } = useGraviaData();
  const action = useMeasurementSession();
  const latest = measurements.find((item) => item.profileId === profileId);
  const belongsToProfile = live.sessionEvent?.profileId === profileId;
  const sessionStatus = belongsToProfile ? live.sessionEvent?.status : undefined;
  const status =
    sessionStatus === 'COMPLETED' &&
    live.completed &&
    !measurements.some((item) => item.id === live.completed?.id)
      ? undefined
      : sessionStatus;
  const active = !!live.sessionEvent && activeStatuses.includes(live.sessionEvent.status);
  const showingLive = belongsToProfile && (active || status === 'COMPLETED');
  const weight = showingLive
    ? (live.completed?.weight ?? live.reading?.weight ?? 0)
    : latest?.weight;
  return (
    <section className="card weight-card">
      <div className="card-heading">
        <div className="eyebrow">IL TUO PESO</div>
        <span className="soft-icon">
          <Scale size={20} />
        </span>
      </div>
      <div className="weight-value">
        {formatWeight(weight)}
        <span>kg</span>
      </div>
      <MeasurementStatus status={status} stability={live.reading?.stability || 0} />
      <div className="weight-meta">
        {status === 'COMPLETED' ? (
          <>
            <Check size={14} /> Salvata automaticamente nel tuo storico
          </>
        ) : active ? (
          'Respira normalmente e distribuisci il peso sui due piedi.'
        ) : latest ? (
          `Ultima misurazione · ${formatDate(latest.measuredAt)}`
        ) : (
          'Un piccolo gesto. Una nuova prospettiva.'
        )}
      </div>
      <div className="weight-actions">
        {active ? (
          <Button
            variant="outline"
            disabled={action.busy}
            onClick={() => live.sessionEvent && action.cancel(live.sessionEvent.sessionId)}
          >
            <X size={17} />
            Annulla misurazione
          </Button>
        ) : (
          <Button
            disabled={action.busy || !profile || !live.connected || !live.board?.connected}
            onClick={() => action.start(profileId)}
          >
            {action.busy ? 'Avvio in corso…' : 'Inizia misurazione'}
            <ArrowUpRight size={18} />
          </Button>
        )}
        <span>{active ? 'Sessione in corso' : 'Circa 10 secondi'}</span>
      </div>
      {(action.error || (belongsToProfile && live.error)) && (
        <p className="inline-error" role="alert">
          {action.error || live.error}
        </p>
      )}
      {live.connected && live.board?.mode === 'real' && !live.board.connected && (
        <p className="inline-error" role="status">
          Accendi la Balance Board e attendi la connessione.
        </p>
      )}
      <div className="weight-card-footer">
        <span>
          <i className={`status-dot ${live.board?.connected ? '' : 'offline'}`} />
          {live.board?.connected ? 'Balance Board connessa' : 'Balance Board non connessa'}
        </span>
        <span className="demo-badge">
          {live.board?.mode === 'demo' ? 'DEMO' : live.board?.mode === 'real' ? 'REALE' : '…'}
        </span>
      </div>
    </section>
  );
}
