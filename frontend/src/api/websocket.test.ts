import { describe, expect, it } from 'vitest';
import { parseLiveEvent } from './websocket';

describe('WebSocket event mapping', () => {
  it.each([
    'bad json',
    '{}',
    '{"type":"unknown","sessionId":"s"}',
    '{"type":"session_status","sessionId":"s","status":"IDLE"}',
    '{"type":"board_connected","board":{"mode":"real","connected":false}}',
    '{"type":"board_disconnected","board":{"mode":"bad","connected":false}}',
    '{"type":"board_connected"}',
  ])('ignores malformed or unsupported payload %s', (payload) =>
    expect(parseLiveEvent(payload)).toBeNull(),
  );
  it.each([
    {
      type: 'session_status',
      sessionId: 's',
      profileId: 'p',
      status: 'STABILIZING',
      stability: 96,
    },
    {
      type: 'live_measurement',
      sessionId: 's',
      weight: 72.4,
      sensors: { frontLeft: 18, frontRight: 18, rearLeft: 18, rearRight: 18.4 },
      centerOfPressure: { x: 0, y: 0 },
    },
    { type: 'measurement_completed', sessionId: 's', measurement: { id: 'm', weight: 72.4 } },
    { type: 'error', sessionId: 's', message: 'Tempo scaduto' },
    {
      type: 'board_connected',
      board: {
        mode: 'real',
        connected: true,
        macAddress: 'AA:BB:CC:DD:EE:FF',
        lastSampleAt: null,
        lastError: null,
        battery: 75,
      },
    },
    {
      type: 'board_disconnected',
      board: {
        mode: 'real',
        connected: false,
        macAddress: 'AA:BB:CC:DD:EE:FF',
        lastSampleAt: null,
        lastError: 'Board spenta',
        battery: null,
      },
    },
  ])('maps $type', (event) => expect(parseLiveEvent(JSON.stringify(event))).toEqual(event));
});
