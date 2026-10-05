import { useEffect, useState } from 'react';
import { connectLiveMeasurements, type LiveEvent } from '../api/websocket';
import type {
  ActivityReading,
  ActivitySession,
  ActivityStatusEvent,
} from '../types/ActivitySession';
import type { BoardStatus } from '../types/BoardStatus';
import type { LiveMeasurement, Measurement } from '../types/Measurement';

export function useLiveMeasurement() {
  const [connected, setConnected] = useState(false);
  const [board, setBoard] = useState<BoardStatus | null>(null);
  const [sessionEvent, setSessionEvent] = useState<Extract<
    LiveEvent,
    { type: 'session_status' }
  > | null>(null);
  const [reading, setReading] = useState<LiveMeasurement | null>(null);
  const [completed, setCompleted] = useState<Measurement | null>(null);
  const [error, setError] = useState('');
  const [activityStatus, setActivityStatus] = useState<ActivityStatusEvent | null>(null);
  const [activityReading, setActivityReading] = useState<ActivityReading | null>(null);
  const [activityCompleted, setActivityCompleted] = useState<ActivitySession | null>(null);
  useEffect(
    () =>
      connectLiveMeasurements((event) => {
        if (event.type === 'board_connected' || event.type === 'board_disconnected') {
          setBoard(event.board);
        }
        if (event.type === 'session_status') {
          setSessionEvent(event);
          if (event.status === 'WAITING_FOR_USER') {
            setError('');
            setReading(null);
            setCompleted(null);
          }
          if (event.status === 'ERROR') setError(event.message || 'Errore durante la misurazione.');
        }
        if (event.type === 'live_measurement') setReading(event);
        if (event.type === 'measurement_completed') setCompleted(event.measurement);
        if (event.type === 'error') setError(event.message);
        if (event.type === 'activity_status') {
          setActivityStatus(event);
          if (event.status === 'WAITING_FOR_USER') {
            setActivityReading(null);
            setActivityCompleted(null);
          }
          if (event.status === 'ERROR' || event.status === 'CANCELLED') setActivityReading(null);
        }
        if (event.type === 'activity_live') setActivityReading(event);
        if (event.type === 'activity_completed') setActivityCompleted(event.activity);
      }, setConnected),
    [],
  );
  return {
    connected,
    board,
    sessionEvent,
    reading,
    completed,
    error,
    activityStatus,
    activityReading,
    activityCompleted,
  };
}
