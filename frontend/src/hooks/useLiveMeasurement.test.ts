import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { connectLiveMeasurements, type LiveEvent } from '../api/websocket';
import { useLiveMeasurement } from './useLiveMeasurement';

vi.mock('../api/websocket', () => ({ connectLiveMeasurements: vi.fn() }));

describe('hardware and realtime connections', () => {
  it('keeps Training independent of weighing and clears stale Training on interruption', () => {
    vi.mocked(connectLiveMeasurements).mockClear();
    let receive: (event: LiveEvent) => void = () => {};
    vi.mocked(connectLiveMeasurements).mockImplementation((onEvent) => {
      receive = onEvent;
      return vi.fn();
    });
    const { result } = renderHook(useLiveMeasurement);
    const status = {
      type: 'activity_status' as const,
      activitySessionId: 'a',
      profileId: 'p',
      activityType: 'BALANCE_HOLD' as const,
      status: 'ACTIVE' as const,
      countdown: 0,
      durationSeconds: 30,
      message: null,
    };
    act(() => {
      receive(status);
      receive({
        type: 'activity_live',
        activitySessionId: 'a',
        elapsed: 1,
        remaining: 29,
        score: 820,
        weight: 80,
        centerOfPressure: { x: 0, y: 0 },
        data: { quality: 0.82 },
      });
    });
    expect(result.current.activityReading?.score).toBe(820);
    expect(result.current.reading).toBeNull();
    expect(result.current.sessionEvent).toBeNull();
    act(() => receive({ ...status, status: 'ERROR', message: 'Board disconnessa' }));
    expect(result.current.activityReading).toBeNull();
    expect(result.current.activityStatus?.message).toBe('Board disconnessa');
    expect(result.current.error).toBe('');
    expect(connectLiveMeasurements).toHaveBeenCalledTimes(1);
  });
  it('updates hardware independently and restores it after reconnect', () => {
    let receive: (event: LiveEvent) => void = () => {};
    let connection: (connected: boolean) => void = () => {};
    const stop = vi.fn();
    vi.mocked(connectLiveMeasurements).mockImplementation((onEvent, onConnection) => {
      receive = onEvent;
      connection = onConnection;
      return stop;
    });
    const { result, unmount } = renderHook(() => useLiveMeasurement());
    const board = {
      mode: 'real' as const,
      connected: false,
      macAddress: null,
      lastSampleAt: null,
      lastError: 'Spenta',
      battery: null,
    };
    act(() => {
      connection(true);
      receive({ type: 'board_disconnected', board });
    });
    expect(result.current.connected).toBe(true);
    expect(result.current.board?.connected).toBe(false);
    act(() =>
      receive({ type: 'board_connected', board: { ...board, connected: true, lastError: null } }),
    );
    expect(result.current.board?.connected).toBe(true);
    act(() => connection(false));
    expect(result.current.connected).toBe(false);
    expect(result.current.board?.connected).toBe(true);
    act(() => {
      connection(true);
      receive({ type: 'board_disconnected', board });
    });
    expect(result.current.board?.connected).toBe(false);
    unmount();
    expect(stop).toHaveBeenCalledOnce();
  });
});
