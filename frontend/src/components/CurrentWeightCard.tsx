import { ArrowUpRight, Check, Scale, X } from 'lucide-react';
import { formatDate, formatWeight } from '../api/weightStatistics';
import { useBoardReading } from '../hooks/useBoardReading';
import { useGraviaData } from '../hooks/useGraviaData';
import { useMeasurementSession } from '../hooks/useMeasurementSession';
import { isActivityActive } from '../types/ActivitySession';
import { MeasurementStatus } from './MeasurementStatus';
import { PressureMap } from './PressureMap';
import { Button } from './ui/Button';

export function CurrentWeightCard() {
  const { profile, profileId, live } = useGraviaData();
  const action = useMeasurementSession();
  const { latest, reading, status, active, showingLive } = useBoardReading();
  const belongsToProfile = live.sessionEvent?.profileId === profileId;
  const boardHint =
    live.board?.state === 'DISCONNECTING'
      ? 'Spegnimento Balance Board…'
      : live.board?.state === 'CONNECTING'
        ? 'Connessione alla Balance Board…'
        : 'Premi il pulsante Power sulla Balance Board.';
  const weight = showingLive
    ? (live.completed?.weight ?? live.reading?.weight ?? 0)
    : latest?.weight;
  return (
    <section className="card weight-card">
      <div className="card-heading">
        <h2>
          <span className="heading-icon">
            <Scale size={20} />
          </span>
          Peso attuale
        </h2>
        <span className="card-context">
          {showingLive && active ? 'Live' : latest ? 'Ultima pesata' : 'Pronto'}
        </span>
      </div>
      <div className="weight-overview">
        <div className="weight-reading">
          <div className="weight-value">
            {formatWeight(weight)}
            <span>kg</span>
          </div>
          <MeasurementStatus status={status} stability={live.reading?.stability || 0} />
          <div className="stability-meter">
            <div>
              <span>Stabilità della misura</span>
              <strong>{reading ? `${Math.round(reading.stability)}%` : '—'}</strong>
            </div>
            <meter
              className="reading-meter"
              aria-label="Stabilità della misura"
              min={0}
              max={100}
              value={Math.max(0, Math.min(100, reading?.stability ?? 0))}
              aria-valuetext={reading ? `${Math.round(reading.stability)}%` : 'Nessun dato'}
            />
          </div>
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
                disabled={
                  action.busy ||
                  isActivityActive(live.activityStatus?.status) ||
                  !profile ||
                  !live.connected ||
                  !live.board?.connected ||
                  live.board.calibrationActive
                }
                onClick={() => action.start(profileId)}
              >
                {action.busy ? 'Avvio in corso…' : 'Inizia misurazione'}
                <ArrowUpRight size={18} />
              </Button>
            )}
            <span>{active ? 'Sessione in corso' : 'Circa 10 secondi'}</span>
          </div>
        </div>
        <PressureMap reading={reading} live={showingLive && active} />
      </div>
      {(action.error || (belongsToProfile && live.error)) && (
        <p className="inline-error" role="alert">
          {action.error || live.error}
        </p>
      )}
      {live.board?.calibrationActive && (
        <p className="settings-note" role="status">
          Calibrazione in corso. Completa o annulla la calibrazione per iniziare una pesata.
        </p>
      )}
      {isActivityActive(live.activityStatus?.status) && (
        <p className="settings-note" role="status">
          Training in corso. Termina l’attività per iniziare una pesata.
        </p>
      )}
      <div className="weight-card-footer">
        <span role="status">
          <i className={`status-dot ${live.board?.connected ? '' : 'offline'}`} />
          {live.board?.connected
            ? 'Balance Board connessa'
            : live.connected && live.board?.mode === 'real'
              ? boardHint
              : 'Balance Board non connessa'}
        </span>
        <span className="demo-badge">
          {live.board?.mode === 'demo' ? 'DEMO' : live.board?.mode === 'real' ? 'REALE' : '…'}
        </span>
      </div>
    </section>
  );
}
