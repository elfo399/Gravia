import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Measurement } from '../types/Measurement';
import { useBoardReading } from './useBoardReading';
import { useGraviaData } from './useGraviaData';

vi.mock('./useGraviaData', () => ({ useGraviaData: vi.fn() }));
const saved = {
  id: 'm1',
  profileId: 'p1',
  sessionId: 's1',
  weight: 72.4,
  stability: 98,
  frontLeft: 18.1,
  frontRight: 18.1,
  rearLeft: 18.1,
  rearRight: 18.1,
  centerX: 0,
  centerY: 0,
} as Measurement;
beforeEach(() => {
  vi.mocked(useGraviaData).mockReturnValue({
    profiles: [],
    measurements: [saved],
    profile: undefined,
    profileId: 'p1',
    selectProfile: vi.fn(),
    refresh: vi.fn(),
    loading: false,
    error: '',
    live: {
      connected: true,
      board: null,
      sessionEvent: null,
      reading: null,
      completed: null,
      error: '',
    },
  });
});
describe('dashboard sensor source', () => {
  it('shows the saved sensor distribution when no session is running', () => {
    const { result } = renderHook(useBoardReading);
    expect(result.current.showingLive).toBe(false);
    expect(result.current.reading?.weight).toBe(72.4);
    expect(result.current.reading?.sensors.frontLeft).toBe(18.1);
  });
  it('never shows another profile’s live pressure readings', () => {
    const data = useGraviaData();
    data.live.sessionEvent = {
      type: 'session_status',
      sessionId: 's2',
      profileId: 'p2',
      status: 'MEASURING',
      stability: 0,
      message: null,
    };
    data.live.reading = {
      sessionId: 's2',
      weight: 90,
      stability: 90,
      sensors: { frontLeft: 20, frontRight: 20, rearLeft: 25, rearRight: 25 },
      centerOfPressure: { x: 0, y: 0 },
    };
    const { result } = renderHook(useBoardReading);
    expect(result.current.reading?.weight).toBe(72.4);
    expect(result.current.showingLive).toBe(false);
  });
  it('uses the selected profile’s live readings during a measurement', () => {
    const data = useGraviaData();
    data.live.sessionEvent = {
      type: 'session_status',
      sessionId: 's2',
      profileId: 'p1',
      status: 'MEASURING',
      stability: 0,
      message: null,
    };
    data.live.reading = {
      sessionId: 's2',
      weight: 80,
      stability: 96,
      sensors: { frontLeft: 20, frontRight: 20, rearLeft: 20, rearRight: 20 },
      centerOfPressure: { x: 0, y: 0 },
    };
    const { result } = renderHook(useBoardReading);
    expect(result.current.reading?.weight).toBe(80);
    expect(result.current.showingLive).toBe(true);
  });
  it('has no invented readings for an empty profile', () => {
    useGraviaData().profileId = 'empty';
    const { result } = renderHook(useBoardReading);
    expect(result.current.reading).toBeNull();
  });
  it('does not resurrect a deleted completion', () => {
    const data = useGraviaData();
    data.live.sessionEvent = {
      type: 'session_status',
      sessionId: 'deleted',
      profileId: 'p1',
      status: 'COMPLETED',
      stability: 99,
      message: null,
    };
    data.live.completed = { ...saved, id: 'deleted', weight: 80 };
    const { result } = renderHook(useBoardReading);
    expect(result.current.status).toBeUndefined();
    expect(result.current.reading?.weight).toBe(72.4);
  });
});
