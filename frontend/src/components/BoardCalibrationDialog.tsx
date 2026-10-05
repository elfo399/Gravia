import { Check, LoaderCircle, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { boardCalibrationApi } from '../api/boardCalibrationApi';
import type { BoardCalibrationStatus } from '../types/BoardCalibration';
import type { CalibrationSession } from '../types/CalibrationSession';
import { Button } from './ui/Button';

interface Props {
  initial: CalibrationSession;
  available: boolean;
  onClose: () => void;
  onSaved: (status: BoardCalibrationStatus) => void;
}

export function BoardCalibrationDialog({ initial, available, onClose, onSaved }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closing = useRef(false);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  const [session, setSession] = useState(initial);
  const [reference, setReference] = useState('20.00');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [interrupted, setInterrupted] = useState(false);
  const step = session.stage === 'TARE' ? 1 : session.stage === 'REFERENCE' ? 2 : 3;
  const referenceNumber = Number(reference);
  const validReference =
    reference.trim() !== '' &&
    Number.isFinite(referenceNumber) &&
    referenceNumber > 0 &&
    referenceNumber <= 150;
  const disabled = busy || interrupted || !available;

  useEffect(() => {
    mounted.current = true;
    dialog.current?.showModal();
    return () => {
      mounted.current = false;
      queueMicrotask(() => {
        // StrictMode replays mount effects; only a real navigation cancels.
        if (!mounted.current && !closing.current) {
          closing.current = true;
          void boardCalibrationApi.cancel(initial.id).catch(() => {});
        }
      });
    };
  }, [initial.id]);
  useEffect(() => {
    if (!available) {
      setInterrupted(true);
      setError('Calibrazione interrotta perché la Balance Board si è disconnessa.');
      void boardCalibrationApi.cancel(initial.id).catch(() => {});
    }
  }, [available, initial.id]);
  useEffect(() => {
    if (interrupted) return;
    const timer = window.setInterval(() => {
      void boardCalibrationApi.session(initial.id).catch((error) => {
        if (!closing.current) {
          setInterrupted(true);
          setError(error.message);
        }
      });
    }, 2000);
    return () => window.clearInterval(timer);
  }, [initial.id, interrupted]);

  async function acquire(action: () => Promise<CalibrationSession>) {
    if (inFlight.current || disabled) return;
    inFlight.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await action();
      if (!closing.current) setSession(result);
    } catch (error) {
      if (!closing.current)
        setError(error instanceof Error ? error.message : 'Acquisizione non riuscita.');
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function close() {
    if (closing.current) return;
    closing.current = true;
    try {
      await boardCalibrationApi.cancel(session.id);
    } catch {
      /* Expired/disconnected sessions are already discarded by the backend. */
    }
    onClose();
  }
  function verify() {
    if (inFlight.current || disabled) return;
    setSession((previous) => ({
      ...previous,
      valid: null,
      measuredWeightAfter: null,
      absoluteError: null,
      percentageError: null,
    }));
    void acquire(() => boardCalibrationApi.verify(session.id));
  }
  async function save() {
    if (inFlight.current || disabled || session.valid !== true) return;
    inFlight.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await boardCalibrationApi.save(session.id);
      closing.current = true;
      onSaved(result);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Salvataggio non riuscito.');
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      className="calibration-dialog"
      aria-labelledby="calibration-title"
      onCancel={(event) => {
        event.preventDefault();
        void close();
      }}
    >
      <div className="calibration-dialog-heading">
        <div>
          <div className="eyebrow">STEP {step} DI 3</div>
          <h2 id="calibration-title">
            {step === 1 ? 'Tara' : step === 2 ? 'Peso di riferimento' : 'Verifica calibrazione'}
          </h2>
        </div>
        <Button variant="ghost" aria-label="Chiudi calibrazione" onClick={close}>
          <X size={20} />
        </Button>
      </div>
      <ol className="calibration-steps" aria-label="Passaggi della calibrazione">
        {['Tara', 'Peso noto', 'Verifica'].map((title, index) => (
          <li
            key={title}
            aria-current={step === index + 1 ? 'step' : undefined}
            className={step >= index + 1 ? 'current' : ''}
          >
            <span>{index + 1}</span>
            {title}
          </li>
        ))}
      </ol>
      {step === 1 && (
        <>
          <p>Lascia la Balance Board completamente vuota su una superficie rigida e piana.</p>
          <p className="settings-note">
            Acquisiremo diversi campioni per circa 4 secondi. Non toccare la pedana.
          </p>
          <Button
            disabled={disabled}
            onClick={() => acquire(() => boardCalibrationApi.tare(session.id))}
          >
            Esegui tara
          </Button>
        </>
      )}
      {step === 2 && (
        <>
          <p className="calibration-success">
            <Check size={16} /> Tara completata
          </p>
          <p>Posiziona un peso conosciuto al centro della Balance Board.</p>
          <div className="form-fields">
            <label>
              Peso noto (kg)
              <input
                type="number"
                min="0.01"
                max="150"
                step="0.01"
                value={reference}
                disabled={busy || interrupted}
                onChange={(event) => setReference(event.target.value)}
              />
            </label>
          </div>
          {!validReference && (
            <p className="inline-error">Inserisci un peso maggiore di zero, fino a 150 kg.</p>
          )}
          <p className="settings-note">
            Per una calibrazione migliore usa un peso stabile e conosciuto, ad esempio un peso da
            palestra. Raccomandiamo almeno 5 kg.
          </p>
          <Button
            disabled={disabled || !validReference}
            onClick={() =>
              acquire(() => boardCalibrationApi.reference(session.id, referenceNumber))
            }
          >
            Avvia calibrazione
          </Button>
        </>
      )}
      {step === 3 && (
        <>
          <p>
            Lascia lo stesso peso al centro della pedana. Una nuova lettura verifica la correzione.
          </p>
          <div className="calibration-results">
            {[
              ['Peso di riferimento', session.referenceWeight],
              ['Prima della calibrazione', session.measuredWeightBefore],
              ['Dopo calibrazione', session.measuredWeightAfter],
            ].map(([label, value]) => (
              <div className="setting-row" key={label}>
                <span>{label}</span>
                <strong>
                  {typeof value === 'number' ? `${value.toFixed(2)} kg` : 'Da verificare'}
                </strong>
              </div>
            ))}
            {session.absoluteError !== null && (
              <div className="setting-row">
                <span>Errore</span>
                <strong>
                  {session.absoluteError >= 0 ? '+' : ''}
                  {session.absoluteError.toFixed(2)} kg · {session.percentageError?.toFixed(2)}%
                </strong>
              </div>
            )}
          </div>
          {session.valid !== null && (
            <p className={session.valid ? 'calibration-success' : 'inline-error'} role="status">
              {session.valid
                ? '✓ Calibrazione valida'
                : 'Calibrazione poco affidabile. Controlla il peso e riprova la verifica.'}
            </p>
          )}
          <div className="form-actions">
            <Button variant="outline" disabled={disabled} onClick={verify}>
              {session.valid === null ? 'Verifica peso' : 'Ripeti verifica'}
            </Button>
            <Button disabled={disabled || session.valid !== true} onClick={save}>
              Salva calibrazione
            </Button>
          </div>
        </>
      )}
      {busy && (
        <p className="calibration-progress" role="status">
          <LoaderCircle className="spin" size={17} /> Acquisizione in corso…
        </p>
      )}
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <p className="settings-note">
        La calibrazione Gravia non modifica la calibrazione interna della Wii Balance Board.
        Chiudendo prima del salvataggio, i nuovi dati vengono scartati.
      </p>
    </dialog>
  );
}
