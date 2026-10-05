import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGraviaData } from '../hooks/useGraviaData';
import { useMeasurementSession } from '../hooks/useMeasurementSession';
import { CurrentWeightCard } from './CurrentWeightCard';

vi.mock('../hooks/useGraviaData', () => ({ useGraviaData: vi.fn() }));
vi.mock('../hooks/useMeasurementSession', () => ({ useMeasurementSession: vi.fn() }));

function mockBoard(connected: boolean) {
  const start = vi.fn();
  vi.mocked(useMeasurementSession).mockReturnValue({
    start,
    cancel: vi.fn(),
    busy: false,
    error: '',
  });
  vi.mocked(useGraviaData).mockReturnValue({
    profile: { id: 'p', name: 'Ada', heightCm: 170, createdAt: '', updatedAt: '' },
    profileId: 'p',
    measurements: [],
    profiles: [],
    selectProfile: vi.fn(),
    refresh: vi.fn(),
    loading: false,
    error: '',
    live: {
      connected: true,
      board: {
        mode: 'real',
        connected,
        macAddress: null,
        lastSampleAt: null,
        lastError: null,
        battery: null,
      },
      sessionEvent: null,
      reading: null,
      completed: null,
      error: '',
    },
  });
  return start;
}

describe('starting a measurement', () => {
  beforeEach(() => mockBoard(false));
  it.each([false, true])('requires hardware availability: %s', (connected) => {
    const start = mockBoard(connected);
    render(<CurrentWeightCard />);
    const button = screen.getByRole('button', { name: 'Inizia misurazione' });
    expect(
      screen.getByText(connected ? 'Balance Board connessa' : 'Balance Board non connessa'),
    ).toBeInTheDocument();
    if (connected) {
      expect(button).toBeEnabled();
      fireEvent.click(button);
      expect(start).toHaveBeenCalledWith('p');
    } else {
      expect(button).toBeDisabled();
      expect(screen.getByText('Premi il pulsante Power sulla Balance Board.')).toBeInTheDocument();
      fireEvent.click(button);
      expect(start).not.toHaveBeenCalled();
    }
  });
  it.each([
    ['CONNECTING', 'Connessione alla Balance Board…'],
    ['DISCONNECTING', 'Spegnimento Balance Board…'],
    ['WAITING_FOR_POWER', 'Premi il pulsante Power sulla Balance Board.'],
  ] as const)('shows the board lifecycle: %s', (state, message) => {
    const data = useGraviaData();
    if (!data.live.board) throw new Error('Missing test board');
    vi.mocked(useGraviaData).mockReturnValue({
      ...data,
      live: { ...data.live, board: { ...data.live.board, connected: false, state } },
    });
    render(<CurrentWeightCard />);
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Inizia misurazione' })).toBeDisabled();
  });
});
