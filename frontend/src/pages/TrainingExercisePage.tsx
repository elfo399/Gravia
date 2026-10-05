import { ArrowLeft, Play, RotateCcw, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { directions, exercises } from '../components/training/activities';
import { BalanceTarget } from '../components/training/BalanceTarget';
import { SymmetryMeter } from '../components/training/SymmetryMeter';
import { TrainingResult } from '../components/training/TrainingResult';
import { Button } from '../components/ui/Button';
import { useActivitySession } from '../hooks/useActivitySession';
import { useGraviaData } from '../hooks/useGraviaData';
import { type ActivityType, activityLabels, isActivityActive } from '../types/ActivitySession';

export function TrainingExercisePage({ activityType }: { activityType: ActivityType }) {
  const { live } = useGraviaData();
  const action = useActivitySession(activityType);
  const exercise = exercises[activityType];
  const Icon = exercise.icon;
  const active = isActivityActive(action.status);
  const finished =
    action.status === 'COMPLETED' && action.session?.status === 'COMPLETED' ? action.session : null;
  const remaining = action.reading?.remaining ?? (activityType === 'WEIGHT_SHIFT' ? 40 : 30);
  const seconds = Math.max(0, Math.ceil(remaining));
  const timer = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
  const direction = action.reading?.data.direction;
  return (
    <div className="training-page exercise-page">
      <Link to="/training" className="training-back">
        <ArrowLeft size={16} />
        Training
      </Link>
      <div className="page-title training-title">
        <div className="eyebrow">{exercise.subtitle}</div>
        <h1>{exercise.name}</h1>
        <p>{exercise.instruction}</p>
      </div>
      <section className="card training-stage">
        <div className="card-heading">
          <h2>
            <span className="heading-icon">
              <Icon size={20} />
            </span>
            {exercise.name}
          </h2>
          <span className="demo-badge">{live.board?.mode === 'demo' ? 'DEMO' : 'REALE'}</span>
        </div>
        {action.restoring ? (
          <p role="status" className="training-wait">
            Recupero attività…
          </p>
        ) : finished ? (
          <TrainingResult session={finished} />
        ) : (
          <>
            <div className="training-session-status" role="status" aria-live="polite">
              {action.status === 'COUNTDOWN' ? (
                <>
                  <strong className="training-countdown">{action.countdown ?? 3}</strong>
                  <span>Preparati. L’attività sta per iniziare.</span>
                </>
              ) : (
                <>
                  <strong>
                    {action.status
                      ? activityLabels[action.status]
                      : 'Un momento per il tuo equilibrio'}
                  </strong>
                  <span>
                    {action.status === 'WAITING_FOR_USER'
                      ? 'Sali sulla pedana e resta fermo. Partiamo dopo 3 secondi.'
                      : action.status === 'ACTIVE'
                        ? activityType === 'WEIGHT_SHIFT' && direction
                          ? `Sposta il peso: ${directions[direction]}`
                          : 'VIA · Mantieni un appoggio comodo e regolare.'
                        : (action.session?.errorMessage ?? exercise.description)}
                  </span>
                </>
              )}
            </div>
            <div className="training-live-layout">
              {activityType === 'SYMMETRY' ? (
                <SymmetryMeter reading={action.reading} />
              ) : (
                <BalanceTarget reading={action.reading} shift={activityType === 'WEIGHT_SHIFT'} />
              )}
              <div className="training-live-numbers">
                <div>
                  <span>Tempo rimanente</span>
                  <output className="training-timer" aria-label="Tempo rimanente" aria-live="off">
                    {timer}
                  </output>
                </div>
                {activityType === 'WEIGHT_SHIFT' && (
                  <div>
                    <span>Target</span>
                    <output aria-label="Progresso target" aria-live="off">
                      {action.reading?.data.targetIndex ?? '—'} <small>/ 10</small>
                    </output>
                  </div>
                )}
                <div>
                  <span>Punteggio</span>
                  <output aria-label="Punteggio" aria-live="off">
                    {action.reading?.score ?? '—'} <small>pt</small>
                  </output>
                </div>
                <p className="training-feedback" role="status">
                  {action.reading?.data.lastOutcome === 'REACHED'
                    ? '✓ Target raggiunto'
                    : action.reading?.data.lastOutcome === 'MISSED'
                      ? 'Target mancato · Prova il prossimo'
                      : activityType === 'SYMMETRY'
                        ? 'Cerca un appoggio uniforme'
                        : activityType === 'WEIGHT_SHIFT'
                          ? 'Resta nel target per 0,4 secondi'
                          : 'Resta nella zona centrale'}
                </p>
              </div>
            </div>
          </>
        )}
        {action.error && (
          <p className="inline-error" role="alert">
            {action.error}
          </p>
        )}
        <div className="training-stage-actions">
          {active ? (
            <Button variant="outline" disabled={action.busy} onClick={() => action.cancel()}>
              <X size={16} />
              Annulla attività
            </Button>
          ) : (
            <Button disabled={!action.canStart} onClick={() => action.start(activityType)}>
              {action.session ? <RotateCcw size={16} /> : <Play size={16} />}{' '}
              {action.session ? 'Ripeti esercizio' : 'Inizia attività'}
            </Button>
          )}
          <Link to="/training">
            Torna al Training <ArrowLeft size={14} />
          </Link>
        </div>
        {!active && !finished && !live.board?.connected && (
          <p className="training-offline" role="status">
            Accendi la Balance Board per iniziare
          </p>
        )}
        {!active && !action.canStart && action.occupied && (
          <p className="training-offline" role="status">
            Termina la pesata, la calibrazione o il Training in corso per iniziare.
          </p>
        )}
      </section>
    </div>
  );
}
