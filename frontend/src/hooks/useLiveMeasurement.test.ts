import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { connectLiveMeasurements, type LiveEvent } from '../api/websocket';
import { useLiveMeasurement } from './useLiveMeasurement';

vi.mock('../api/websocket', () => ({ connectLiveMeasurements: vi.fn() }));

describe('hardware and realtime connections', () => {
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
