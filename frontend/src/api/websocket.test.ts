import { describe, expect, it } from 'vitest';
import { parseLiveEvent } from './websocket';

describe('WebSocket event mapping', () => {
  it.each([
    {
      type: 'activity_status',
      activitySessionId: 'a',
      profileId: 'p',
      activityType: 'BALANCE_HOLD',
      status: 'COUNTDOWN',
      countdown: 3,
      durationSeconds: 30,
      message: null,
    },
    {
      type: 'activity_live',
      activitySessionId: 'a',
      elapsed: 4,
      remaining: 26,
      score: 850,
      weight: 72,
      centerOfPressure: { x: 0, y: 0.1 },
      data: { centerRadius: 0.15 },
    },
    {
      type: 'activity_completed',
      activitySessionId: 'a',
      activity: {
        id: 'a',
        profileId: 'p',
        activityType: 'SYMMETRY',
        status: 'COMPLETED',
        score: 900,
        resultJson: { balancedPercent: 80 },
      },
    },
  ])('maps Training event $type through the existing socket', (event) =>
    expect(parseLiveEvent(JSON.stringify(event))).toEqual(event),
  );
  it.each([
    {
      type: 'activity_status',
      activitySessionId: 'a',
      profileId: 'p',
      activityType: 'UNKNOWN',
      status: 'ACTIVE',
      countdown: null,
      durationSeconds: 30,
    },
    {
      type: 'activity_status',
      activitySessionId: 'a',
      profileId: 'p',
      activityType: 'SYMMETRY',
      status: 'IDLE',
      countdown: null,
      durationSeconds: 30,
    },
    {
      type: 'activity_live',
      activitySessionId: 'a',
      elapsed: 1,
      remaining: 29,
      score: 800,
      weight: 72,
      centerOfPressure: { x: null, y: 0 },
      data: {},
    },
    {
      type: 'activity_completed',
      activitySessionId: 'a',
      activity: {
        id: 'wrong',
        profileId: 'p',
        activityType: 'BALANCE_HOLD',
        status: 'COMPLETED',
        score: 900,
        resultJson: {},
      },
    },
  ])('rejects malformed Training event $type', (event) =>
    expect(parseLiveEvent(JSON.stringify(event))).toBeNull(),
  );
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
