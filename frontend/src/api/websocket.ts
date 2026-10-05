import type { BoardStatus } from '../types/BoardStatus';
import type { LiveMeasurement, Measurement } from '../types/Measurement';
import { type SessionStatus, sessionLabels } from '../types/MeasurementSession';

export type LiveEvent =
  | { type: 'board_connected' | 'board_disconnected'; board: BoardStatus }
  | ({ type: 'live_measurement' } & LiveMeasurement)
  | {
      type: 'session_status';
      sessionId: string;
      profileId: string;
      status: SessionStatus;
      stability: number;
      message: string | null;
    }
  | { type: 'measurement_completed'; sessionId: string; measurement: Measurement }
  | { type: 'error'; sessionId: string; message: string };

export function parseLiveEvent(payload: string): LiveEvent | null {
  try {
    const event = JSON.parse(payload);
    if (event.type === 'board_connected' || event.type === 'board_disconnected') {
      if (
        (event.board?.mode === 'demo' || event.board?.mode === 'real') &&
        typeof event.board.connected === 'boolean' &&
        event.board.connected === (event.type === 'board_connected')
      )
        return event;
      return null;
    }
    if (typeof event.sessionId !== 'string') return null;
    if (event.type === 'session_status' && event.status in sessionLabels) return event;
    if (
      event.type === 'live_measurement' &&
      typeof event.weight === 'number' &&
      event.sensors &&
      event.centerOfPressure
    )
      return event;
    if (event.type === 'measurement_completed' && typeof event.measurement?.id === 'string')
      return event;
    if (event.type === 'error' && typeof event.message === 'string') return event;
    return null;
  } catch {
    return null;
  }
}

export function connectLiveMeasurements(
  onEvent: (event: LiveEvent) => void,
  onConnection: (connected: boolean) => void,
) {
  let socket: WebSocket;
  let stopped = false;
  let retries = 0;
  let timer: ReturnType<typeof setTimeout>;
  function connect() {
    socket = new WebSocket(
      `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/live`,
    );
    socket.onopen = () => {
      if (stopped) {
        socket.close();
        return;
      }
      retries = 0;
      onConnection(true);
    };
    socket.onmessage = (message) => {
      const event = parseLiveEvent(message.data);
      if (event) onEvent(event);
    };
    socket.onerror = () => socket.close();
    socket.onclose = () => {
      if (stopped) return;
      onConnection(false);
      if (!stopped) timer = setTimeout(connect, Math.min(1000 * 2 ** retries++, 10000));
    };
  }
  connect();
  return () => {
    stopped = true;
    clearTimeout(timer);
    if (socket.readyState === WebSocket.OPEN) socket.close();
  };
}
