import { ArrowRight, Play, Target } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { activitiesApi } from '../api/activitiesApi';
import { boardCalibrationApi } from '../api/boardCalibrationApi';
import { formatDate } from '../api/weightStatistics';
import { exercises } from '../components/training/activities';
import { Button } from '../components/ui/Button';
import { useActivitySession } from '../hooks/useActivitySession';
import { useGraviaData } from '../hooks/useGraviaData';
import {
  type ActivitySession,
  activityLabels,
  activityTypes,
  isActivityActive,
} from '../types/ActivitySession';

export function TrainingPage() {
  const { profileId, profile, live } = useGraviaData();
  const action = useActivitySession();
  const navigate = useNavigate();
  const [history, setHistory] = useState<ActivitySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uncalibrated, setUncalibrated] = useState(false);
  const [reload, setReload] = useState(0);
  // biome-ignore lint/correctness/useExhaustiveDependencies: activity events and explicit retry invalidate the REST history.
  useEffect(() => {
    let disposed = false;
    setHistory([]);
    setLoading(true);
    setError('');
    if (!profileId) {
      setLoading(false);
      return;
    }
    activitiesApi
      .list(profileId)
      .then((rows) => {
        if (!disposed) setHistory(rows);
      })
      .catch((error) => {
        if (!disposed)
          setError(error instanceof Error ? error.message : 'Storico non disponibile.');
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [profileId, live.activityStatus, live.activityCompleted, reload]);
  // biome-ignore lint/correctness/useExhaustiveDependencies: board changes and finishing calibration invalidate its saved status.
  useEffect(() => {
    let disposed = false;
    setUncalibrated(false);
    if (live.board?.mode === 'real')
      boardCalibrationApi
        .get()
        .then((status) => {
          if (!disposed) setUncalibrated(!status.configured);
        })
        .catch(() => {});
    return () => {
      disposed = true;
    };
  }, [live.board?.mode, live.board?.macAddress, live.board?.calibrationActive]);
  const active = isActivityActive(action.session?.status) ? action.session : null;
  return (
    <div className="training-page">
      <div className="page-title training-title">
        <div className="eyebrow">IL TUO EQUILIBRIO, OGNI GIORNO</div>
        <h1>Training</h1>
        <p>Tre piccoli esercizi per conoscere meglio il tuo appoggio e seguire i tuoi progressi.</p>
      </div>
      <div className="training-availability" role="status">
        <Target size={18} />
        <span>
          {!profile
            ? 'Crea un profilo per iniziare.'
            : !live.connected
              ? 'Collegamento a Gravia interrotto. Attendi la riconnessione.'
              : !live.board?.connected
                ? 'Accendi la Balance Board per iniziare'
                : action.occupied || active
                  ? 'La board è impegnata. Termina l’attività in corso oppure riprendi il Training.'
                  : live.board.mode === 'demo'
                    ? 'Modalità demo · Esplora gli esercizi con una pedana simulata.'
                    : `Pronto per iniziare, ${profile.name}.`}
        </span>
        {active && (
          <Link to={exercises[active.activityType].path}>
            Riprendi attività <ArrowRight size={14} />
          </Link>
        )}
      </div>
      {uncalibrated && (
        <p className="training-calibration">
          Calibrazione Gravia non configurata.{' '}
          <Link to="/settings">Configura la pedana nelle Impostazioni</Link> per personalizzare le
          letture.
        </p>
      )}
      {action.error && (
        <p className="inline-error" role="alert">
          {action.error}
        </p>
      )}
      <div className="training-grid">
        {activityTypes.map((type) => {
          const exercise = exercises[type];
          const Icon = exercise.icon;
          const scores = history
            .filter(
              (row) =>
                row.activityType === type && row.status === 'COMPLETED' && row.score !== null,
            )
            .map((row) => row.score as number);
          return (
            <section className="card training-exercise-card" key={type} aria-label={exercise.name}>
              <span className="training-exercise-icon">
                <Icon size={28} />
              </span>
              <div className="eyebrow">{exercise.subtitle}</div>
              <h2>{exercise.name}</h2>
              <p>{exercise.description}</p>
              <div className="training-card-meta">
                <span>{exercise.duration}</span>
                <span>
                  Record personale{' '}
                  <b>{loading ? '…' : scores.length ? `${Math.max(...scores)} pt` : '—'}</b>
                </span>
              </div>
              <Button
                disabled={!action.canStart}
                onClick={async () => {
                  const row = await action.start(type);
                  if (row) navigate(exercise.path);
                }}
              >
                <Play size={16} />
                Inizia {exercise.name}
              </Button>
            </section>
          );
        })}
      </div>
      <section className="card training-history">
        <div className="card-heading">
          <h2>Le tue ultime attività</h2>
          <span className="card-context">{profile?.name ?? 'Nessun profilo'}</span>
        </div>
        {error ? (
          <div className="inline-error" role="alert">
            {error}{' '}
            <Button variant="outline" onClick={() => setReload((value) => value + 1)}>
              Riprova
            </Button>
          </div>
        ) : loading ? (
          <p className="muted" role="status">
            Caricamento attività…
          </p>
        ) : !history.length ? (
          <div className="training-empty">
            <Target size={24} />
            <p>Il tuo percorso parte da qui.</p>
            <span>Completa un esercizio per ritrovare qui i tuoi risultati.</span>
          </div>
        ) : (
          <div className="training-history-list">
            {history.slice(0, 5).map((row) => (
              <div key={row.id} className="training-history-row">
                <div>
                  <strong>{exercises[row.activityType]?.name ?? row.activityType}</strong>
                  <span>{formatDate(row.createdAt)}</span>
                </div>
                <span
                  className={`training-history-status ${row.status === 'COMPLETED' ? 'completed' : ''}`}
                >
                  {activityLabels[row.status]}
                </span>
                <b>{row.status === 'COMPLETED' ? `${row.score} pt` : '—'}</b>
              </div>
            ))}
          </div>
        )}
      </section>
      <p className="training-footnote">
        Movimenti piccoli, piedi sempre in appoggio. I punteggi descrivono questo esercizio e ti
        aiutano a confrontare le tue sessioni.
      </p>
    </div>
  );
}
