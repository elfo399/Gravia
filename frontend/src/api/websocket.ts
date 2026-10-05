import {
  type ActivityReading,
  type ActivitySession,
  type ActivityStatusEvent,
  activityLabels,
  activityTypes,
} from '../types/ActivitySession';
import type { BoardStatus } from '../types/BoardStatus';
import type { LiveMeasurement, Measurement } from '../types/Measurement';
import { type SessionStatus, sessionLabels } from '../types/MeasurementSession';

export type LiveEvent =
  | ActivityStatusEvent
  | ActivityReading
  | { type: 'activity_completed'; activitySessionId: string; activity: ActivitySession }
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
    if (typeof event?.activitySessionId === 'string') {
      if (
        event.type === 'activity_status' &&
        typeof event.profileId === 'string' &&
        activityTypes.includes(event.activityType) &&
        Object.hasOwn(activityLabels, event.status) &&
        (event.countdown === null || Number.isFinite(event.countdown)) &&
        Number.isFinite(event.durationSeconds)
      )
        return event;
      if (
        event.type === 'activity_live' &&
        [
          event.elapsed,
          event.remaining,
          event.score,
          event.weight,
          event.centerOfPressure?.x,
          event.centerOfPressure?.y,
        ].every(Number.isFinite) &&
        event.data &&
        typeof event.data === 'object'
      )
        return event;
      if (
        event.type === 'activity_completed' &&
        event.activity?.id === event.activitySessionId &&
        typeof event.activity.profileId === 'string' &&
        activityTypes.includes(event.activity.activityType) &&
        event.activity.status === 'COMPLETED' &&
        Number.isFinite(event.activity.score) &&
        event.activity.resultJson &&
        typeof event.activity.resultJson === 'object'
      )
        return event;
      return null;
    }
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
