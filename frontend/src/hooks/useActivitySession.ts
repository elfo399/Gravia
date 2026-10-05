import { useCallback, useEffect, useRef, useState } from 'react';
import { activitiesApi } from '../api/activitiesApi';
import {
  type ActivitySession,
  type ActivityType,
  isActivityActive,
} from '../types/ActivitySession';
import { activeStatuses } from '../types/MeasurementSession';
import { useGraviaData } from './useGraviaData';

export function useActivitySession(activityType?: ActivityType) {
  const { profileId, profile, live } = useGraviaData();
  const [session, setSession] = useState<ActivitySession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [restoring, setRestoring] = useState(true);
  const pending = useRef(false);
  const revision = useRef(0);
  const belongs = useCallback(
    (row: ActivitySession) =>
      row.profileId === profileId && (!activityType || row.activityType === activityType),
    [profileId, activityType],
  );
  // biome-ignore lint/correctness/useExhaustiveDependencies: reconnect must restore authoritative state even when profile stays the same.
  useEffect(() => {
    let disposed = false;
    const current = ++revision.current;
    setRestoring(true);
    setSession(null);
    setError('');
    activitiesApi
      .active()
      .then((row) => {
        if (!disposed && current === revision.current) setSession(row && belongs(row) ? row : null);
      })
      .catch((error) => {
        if (!disposed)
          setError(error instanceof Error ? error.message : 'Impossibile recuperare l’attività.');
      })
      .finally(() => {
        if (!disposed) setRestoring(false);
      });
    return () => {
      disposed = true;
    };
  }, [belongs, live.connected]);
  useEffect(() => {
    const event = live.activityStatus;
    if (
      !event ||
      event.profileId !== profileId ||
      (activityType && event.activityType !== activityType)
    )
      return;
    const current = ++revision.current;
    let disposed = false;
    activitiesApi
      .get(event.activitySessionId)
      .then((row) => {
        if (!disposed && current === revision.current) setSession(row);
      })
      .catch((error) => {
        if (!disposed)
          setError(error instanceof Error ? error.message : 'Impossibile aggiornare l’attività.');
      });
    return () => {
      disposed = true;
    };
  }, [live.activityStatus, profileId, activityType]);
  useEffect(() => {
    if (live.activityCompleted && belongs(live.activityCompleted)) {
      ++revision.current;
      setSession(live.activityCompleted);
    }
  }, [live.activityCompleted, belongs]);
  const occupied =
    isActivityActive(live.activityStatus?.status) ||
    (!!live.sessionEvent && activeStatuses.includes(live.sessionEvent.status)) ||
    !!live.board?.calibrationActive;
  const canStart =
    !!profile &&
    live.connected &&
    !!live.board?.connected &&
    !occupied &&
    !busy &&
    !restoring &&
    !isActivityActive(session?.status);
  async function start(kind: ActivityType) {
    if (pending.current || !canStart) return null;
    pending.current = true;
    setBusy(true);
    setError('');
    ++revision.current;
    try {
      const row = await activitiesApi.start(profileId, kind);
      setSession(row);
      return row;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Avvio non riuscito.');
      return null;
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function cancel() {
    if (!session || pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    ++revision.current;
    try {
      setSession(await activitiesApi.cancel(session.id));
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Annullamento non riuscito.');
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  const statusEvent =
    live.activityStatus?.activitySessionId === session?.id ? live.activityStatus : null;
  const status = statusEvent?.status ?? session?.status;
  const reading =
    live.activityReading?.activitySessionId === session?.id && status === 'ACTIVE'
      ? live.activityReading
      : null;
  return {
    session,
    status,
    countdown: statusEvent?.countdown,
    reading,
    busy,
    restoring,
    error,
    start,
    cancel,
    canStart,
    occupied,
  };
}
