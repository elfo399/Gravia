import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useGraviaData } from '../hooks/useGraviaData';
import { useMeasurementSession } from '../hooks/useMeasurementSession';
import { CurrentWeightCard } from './CurrentWeightCard';

vi.mock('../hooks/useGraviaData', () => ({ useGraviaData: vi.fn() }));
vi.mock('../hooks/useMeasurementSession', () => ({ useMeasurementSession: vi.fn() }));

describe('starting a measurement', () => {
  it.each([false, true])('requires hardware availability: %s', (connected) => {
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
      expect(
        screen.getByText('Accendi la Balance Board e attendi la connessione.'),
      ).toBeInTheDocument();
      fireEvent.click(button);
      expect(start).not.toHaveBeenCalled();
    }
  });
});
