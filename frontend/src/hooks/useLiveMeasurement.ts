import { useEffect, useState } from 'react';
import { connectLiveMeasurements, type LiveEvent } from '../api/websocket';
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
      }, setConnected),
    [],
  );
  return { connected, board, sessionEvent, reading, completed, error };
}
