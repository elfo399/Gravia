import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from '../api/apiRequest';
import { boardCalibrationApi } from '../api/boardCalibrationApi';
import { useGraviaData } from '../hooks/useGraviaData';
import type { BoardCalibrationStatus } from '../types/BoardCalibration';
import type { CalibrationSession } from '../types/CalibrationSession';
import { BoardCalibrationCard } from './BoardCalibrationCard';
import { BoardCalibrationDialog } from './BoardCalibrationDialog';

vi.mock('../hooks/useGraviaData', () => ({ useGraviaData: vi.fn() }));
vi.mock('../api/apiRequest', () => ({ apiRequest: vi.fn() }));
vi.mock('../api/boardCalibrationApi', () => ({
  boardCalibrationApi: Object.fromEntries(
    ['get', 'start', 'session', 'tare', 'reference', 'verify', 'save', 'cancel', 'reset'].map(
      (name) => [name, vi.fn()],
    ),
  ),
}));

const initial: CalibrationSession = {
  id: 'cal-1',
  stage: 'TARE',
  busy: false,
  referenceWeight: null,
  weightScale: null,
  measuredWeightBefore: null,
  measuredWeightAfter: null,
  absoluteError: null,
  percentageError: null,
  valid: null,
};
const reference: CalibrationSession = {
  ...initial,
  stage: 'VERIFY',
  referenceWeight: 20,
  weightScale: 1.01,
  measuredWeightBefore: 19.8,
};
const verified: CalibrationSession = {
  ...reference,
  measuredWeightAfter: 20.04,
  absoluteError: 0.04,
  percentageError: 0.2,
  valid: true,
};
const empty: BoardCalibrationStatus = { configured: false, calibration: null, activeSession: null };
const saved: BoardCalibrationStatus = {
  configured: true,
  activeSession: null,
  calibration: {
    boardMac: '00:24:44:6C:0D:A2',
    weightScale: 1.0032,
    referenceWeight: 20,
    calibratedAt: '2026-10-05T14:30:00Z',
    measuredWeightBefore: 19.9,
    measuredWeightAfter: 20.04,
  },
};

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
});
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiRequest).mockResolvedValue(null);
  vi.mocked(boardCalibrationApi.get).mockResolvedValue(empty);
  vi.mocked(boardCalibrationApi.start).mockResolvedValue(initial);
  vi.mocked(boardCalibrationApi.session).mockResolvedValue(initial);
  vi.mocked(boardCalibrationApi.tare).mockResolvedValue({ ...initial, stage: 'REFERENCE' });
  vi.mocked(boardCalibrationApi.reference).mockResolvedValue(reference);
  vi.mocked(boardCalibrationApi.verify).mockResolvedValue(verified);
  vi.mocked(boardCalibrationApi.save).mockResolvedValue(saved);
  vi.mocked(boardCalibrationApi.cancel).mockResolvedValue(undefined);
  vi.mocked(boardCalibrationApi.reset).mockResolvedValue(empty);
  vi.mocked(useGraviaData).mockReturnValue({
    profiles: [],
    measurements: [],
    profile: undefined,
    profileId: '',
    loading: false,
    error: '',
    selectProfile: vi.fn(),
    refresh: vi.fn(),
    live: {
      connected: true,
      reading: null,
      completed: null,
      sessionEvent: null,
      error: '',
      board: {
        mode: 'real',
        connected: true,
        macAddress: null,
        lastSampleAt: null,
        lastError: null,
        battery: null,
      },
    },
  });
});

describe('calibration settings', () => {
  it('shows unconfigured status and enables the wizard', async () => {
    render(<BoardCalibrationCard />);
    expect(await screen.findByText('Non configurata')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calibra Balance Board' })).toBeEnabled();
  });
  it('shows the saved factor and last calibration', async () => {
    vi.mocked(boardCalibrationApi.get).mockResolvedValue(saved);
    render(<BoardCalibrationCard />);
    expect(await screen.findByText('Attiva')).toBeInTheDocument();
    expect(screen.getByText('1.0032×')).toBeInTheDocument();
    expect(screen.getByText('Ultima calibrazione')).toBeInTheDocument();
  });
  it.each(['offline', 'demo', 'realtime', 'measurement', 'calibration'])(
    'disables calibration when unavailable: %s',
    async (kind) => {
      const data = useGraviaData();
      if (!data.live.board) throw new Error('Missing board');
      if (kind === 'offline') data.live.board.connected = false;
      if (kind === 'demo') data.live.board.mode = 'demo';
      if (kind === 'realtime') data.live.connected = false;
      if (kind === 'measurement') vi.mocked(apiRequest).mockResolvedValue({ id: 'm' });
      if (kind === 'calibration')
        vi.mocked(boardCalibrationApi.get).mockResolvedValue({
          ...empty,
          activeSession: initial,
        });
      render(<BoardCalibrationCard />);
      await screen.findByText('Non configurata');
      expect(screen.getByRole('button', { name: 'Calibra Balance Board' })).toBeDisabled();
      if (kind === 'offline')
        expect(screen.getByText(/Accendi la Balance Board/)).toBeInTheDocument();
    },
  );
  it('asks for confirmation before resetting and restores the empty status', async () => {
    vi.mocked(boardCalibrationApi.get).mockResolvedValue(saved);
    render(<BoardCalibrationCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Ripristina calibrazione' }));
    expect(boardCalibrationApi.reset).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Conferma ripristino' }));
    expect(await screen.findByText('Non configurata')).toBeInTheDocument();
    expect(boardCalibrationApi.reset).toHaveBeenCalledOnce();
  });
});

describe('calibration wizard', () => {
  it('completes all three steps and saves only after independent verification', async () => {
    render(<BoardCalibrationCard />);
    await screen.findByText('Non configurata');
    fireEvent.click(screen.getByRole('button', { name: 'Calibra Balance Board' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Esegui tara' }));
    expect(await screen.findByText('Tara completata')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Avvia calibrazione' }));
    const save = await screen.findByRole('button', { name: 'Salva calibrazione' });
    expect(save).toBeDisabled();
    expect(boardCalibrationApi.save).not.toHaveBeenCalled();
    expect(boardCalibrationApi.reference).toHaveBeenCalledWith('cal-1', 20);
    fireEvent.click(screen.getByRole('button', { name: 'Verifica peso' }));
    await screen.findByText('✓ Calibrazione valida');
    expect(save).toBeEnabled();
    expect(screen.getByText('20.04 kg')).toBeInTheDocument();
    fireEvent.click(save);
    expect(await screen.findByText('Attiva')).toBeInTheDocument();
    expect(boardCalibrationApi.save).toHaveBeenCalledWith('cal-1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
  it.each(['0', '-1', '151', ''])('rejects invalid reference input %s', (weight) => {
    render(
      <BoardCalibrationDialog
        initial={{ ...initial, stage: 'REFERENCE' }}
        available
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText('Peso noto (kg)'), { target: { value: weight } });
    expect(screen.getByRole('button', { name: 'Avvia calibrazione' })).toBeDisabled();
    expect(boardCalibrationApi.reference).not.toHaveBeenCalled();
  });
  it('shows an acquisition error and allows a retry', async () => {
    vi.mocked(boardCalibrationApi.tare).mockRejectedValueOnce(
      new Error('Il peso non è abbastanza stabile.'),
    );
    render(
      <BoardCalibrationDialog initial={initial} available onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Esegui tara' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('stabile');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Esegui tara' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Esegui tara' }));
    expect(await screen.findByText('Tara completata')).toBeInTheDocument();
  });
  it('does not save an unreliable calibration', () => {
    render(
      <BoardCalibrationDialog
        initial={{ ...verified, valid: false }}
        available
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    expect(screen.getByText(/Calibrazione poco affidabile/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Salva calibrazione' })).toBeDisabled();
  });
  it('invalidates a successful verification if the retry fails', async () => {
    vi.mocked(boardCalibrationApi.verify).mockRejectedValueOnce(new Error('Peso instabile.'));
    render(
      <BoardCalibrationDialog initial={verified} available onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Ripeti verifica' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('instabile');
    expect(screen.getByRole('button', { name: 'Salva calibrazione' })).toBeDisabled();
    expect(boardCalibrationApi.save).not.toHaveBeenCalled();
  });
  it('cancels on close and never saves temporary results', async () => {
    const close = vi.fn();
    render(
      <BoardCalibrationDialog initial={reference} available onClose={close} onSaved={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Chiudi calibrazione' }));
    await waitFor(() => expect(close).toHaveBeenCalledOnce());
    expect(boardCalibrationApi.cancel).toHaveBeenCalledWith('cal-1');
    expect(boardCalibrationApi.save).not.toHaveBeenCalled();
  });
  it('survives StrictMode and cancels only on real navigation', async () => {
    const { unmount } = render(
      <StrictMode>
        <BoardCalibrationDialog initial={initial} available onClose={vi.fn()} onSaved={vi.fn()} />
      </StrictMode>,
    );
    await act(async () => {});
    expect(boardCalibrationApi.cancel).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Esegui tara' }));
    expect(await screen.findByText('Tara completata')).toBeInTheDocument();
    unmount();
    await waitFor(() => expect(boardCalibrationApi.cancel).toHaveBeenCalledWith('cal-1'));
  });
  it('blocks duplicate acquisition while a request is pending', async () => {
    let resolve: (result: CalibrationSession) => void = () => {};
    vi.mocked(boardCalibrationApi.tare).mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    render(
      <BoardCalibrationDialog initial={initial} available onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    const button = screen.getByRole('button', { name: 'Esegui tara' });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(boardCalibrationApi.tare).toHaveBeenCalledOnce();
    expect(screen.getByText('Acquisizione in corso…')).toBeInTheDocument();
    await act(async () => {
      resolve({ ...initial, stage: 'REFERENCE' });
    });
  });
  it('interrupts on disconnect and prevents saving', async () => {
    const props = { initial: verified, onClose: vi.fn(), onSaved: vi.fn() };
    const { rerender } = render(<BoardCalibrationDialog {...props} available />);
    rerender(<BoardCalibrationDialog {...props} available={false} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('disconnessa');
    expect(screen.getByRole('button', { name: 'Salva calibrazione' })).toBeDisabled();
    expect(boardCalibrationApi.save).not.toHaveBeenCalled();
  });
});
