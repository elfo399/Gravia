import { Check, Scale } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { apiRequest } from '../api/apiRequest';
import { boardCalibrationApi } from '../api/boardCalibrationApi';
import { useGraviaData } from '../hooks/useGraviaData';
import { isActivityActive } from '../types/ActivitySession';
import type { BoardCalibrationStatus } from '../types/BoardCalibration';
import type { CalibrationSession } from '../types/CalibrationSession';
import { activeStatuses, type MeasurementSession } from '../types/MeasurementSession';
import { BoardCalibrationDialog } from './BoardCalibrationDialog';
import { Button } from './ui/Button';

export function BoardCalibrationCard() {
  const { live } = useGraviaData();
  const [data, setData] = useState<BoardCalibrationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [session, setSession] = useState<CalibrationSession | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [activeMeasurement, setActiveMeasurement] = useState(false);
  const realtimeMeasurement =
    !!live.sessionEvent && activeStatuses.includes(live.sessionEvent.status);
  const refresh = useCallback(async () => {
    try {
      const [status, measurement] = await Promise.all([
        boardCalibrationApi.get(),
        apiRequest<MeasurementSession | null>('/sessions/active', {
          signal: AbortSignal.timeout(15000),
        }),
      ]);
      setData(status);
      setActiveMeasurement(measurement !== null);
      setError('');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Impossibile caricare la calibrazione.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    if (live.connected) void refresh();
  }, [live.connected, refresh]);
  const real = live.board?.mode === 'real';
  const available = !!live.board?.connected && live.connected;
  const occupied =
    isActivityActive(live.activityStatus?.status) ||
    activeMeasurement ||
    realtimeMeasurement ||
    !!data?.activeSession ||
    !!live.board?.calibrationActive;
  const disabled = loading || busy || !data || !!error || !real || !available || occupied;
  async function start() {
    if (pending.current || disabled) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      setSession(await boardCalibrationApi.start());
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Avvio non riuscito.');
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function reset() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      setData(await boardCalibrationApi.reset());
      setConfirmReset(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Ripristino non riuscito.');
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return (
    <section
      className="card settings-card calibration-card"
      aria-label="Calibrazione Balance Board"
    >
      <div className="card-heading">
        <h2>Calibrazione Balance Board</h2>
        <Scale size={20} />
      </div>
      {loading ? (
        <p className="settings-note" role="status">
          Caricamento calibrazione…
        </p>
      ) : (
        <>
          <div className="setting-row">
            <span>Calibrazione Gravia</span>
            <strong>{data?.configured ? 'Attiva' : 'Non configurata'}</strong>
          </div>
          {data?.calibration && (
            <>
              <div className="setting-row">
                <span>Ultima calibrazione</span>
                <strong>
                  {new Date(data.calibration.calibratedAt).toLocaleString('it-IT', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </strong>
              </div>
              <div className="setting-row">
                <span>Fattore di correzione</span>
                <strong>{data.calibration.weightScale.toFixed(4)}×</strong>
              </div>
            </>
          )}
        </>
      )}
      <p className="settings-note">
        Una tara e un peso conosciuto per adattare Gravia alla tua pedana.
      </p>
      {!real ? (
        <p className="settings-note">
          La calibrazione è disponibile soltanto con la Balance Board reale.
        </p>
      ) : !available ? (
        <p className="settings-note">Accendi la Balance Board prima di iniziare la calibrazione.</p>
      ) : occupied && !session ? (
        <p className="settings-note">
          Termina la misurazione o la calibrazione in corso prima di iniziare.
        </p>
      ) : null}
      {error && (
        <div className="inline-error" role="alert">
          {error}{' '}
          <Button variant="ghost" onClick={refresh}>
            Riprova
          </Button>
        </div>
      )}
      <div className="form-actions">
        <Button disabled={disabled} onClick={start}>
          {busy ? 'Attendi…' : 'Calibra Balance Board'}
        </Button>
        {data?.configured && (
          <Button
            variant="outline"
            disabled={busy || !real || !live.connected || occupied}
            onClick={() => setConfirmReset(true)}
          >
            Ripristina calibrazione
          </Button>
        )}
      </div>
      {confirmReset && (
        <fieldset className="calibration-reset" aria-label="Conferma ripristino">
          <p>Rimuovere la calibrazione Gravia e tornare alle letture originali?</p>
          <Button variant="destructive" disabled={busy} onClick={reset}>
            Conferma ripristino
          </Button>
          <Button variant="ghost" disabled={busy} onClick={() => setConfirmReset(false)}>
            Annulla
          </Button>
        </fieldset>
      )}
      {session && (
        <BoardCalibrationDialog
          initial={session}
          available={available}
          onClose={() => {
            setSession(null);
            void refresh();
          }}
          onSaved={(result) => {
            setData(result);
            setSession(null);
          }}
        />
      )}
      {data?.configured && (
        <p className="calibration-success">
          <Check size={15} /> Correzione applicata alle prossime pesate.
        </p>
      )}
    </section>
  );
}
