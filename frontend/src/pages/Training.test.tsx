import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { activitiesApi } from '../api/activitiesApi';
import { boardCalibrationApi } from '../api/boardCalibrationApi';
import { useGraviaData as getMockData } from '../hooks/useGraviaData';
import type { ActivitySession, ActivityType } from '../types/ActivitySession';
import { TrainingExercisePage } from './TrainingExercisePage';
import { TrainingPage } from './TrainingPage';

vi.mock('../hooks/useGraviaData', () => ({ useGraviaData: vi.fn() }));
vi.mock('../api/activitiesApi', () => ({
  activitiesApi: { start: vi.fn(), list: vi.fn(), get: vi.fn(), active: vi.fn(), cancel: vi.fn() },
}));
vi.mock('../api/boardCalibrationApi', () => ({ boardCalibrationApi: { get: vi.fn() } }));

function row(
  activityType: ActivityType = 'BALANCE_HOLD',
  status: ActivitySession['status'] = 'WAITING_FOR_USER',
): ActivitySession {
  return {
    id: 'a1',
    profileId: 'p1',
    activityType,
    status,
    startedAt: '2026-10-05T12:00:00Z',
    completedAt: null,
    durationSeconds: 30,
    score: null,
    resultJson: null,
    errorMessage: null,
    createdAt: '2026-10-05T12:00:00Z',
  };
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getMockData).mockReturnValue({
    profiles: [],
    measurements: [],
    profileId: 'p1',
    profile: { id: 'p1', name: 'Ada', heightCm: 170, createdAt: '', updatedAt: '' },
    selectProfile: vi.fn(),
    refresh: vi.fn(),
    loading: false,
    error: '',
    live: {
      connected: true,
      board: {
        mode: 'demo',
        connected: true,
        battery: null,
        macAddress: null,
        lastError: null,
        lastSampleAt: null,
      },
      sessionEvent: null,
      reading: null,
      completed: null,
      error: '',
      activityStatus: null,
      activityReading: null,
      activityCompleted: null,
    },
  });
  vi.mocked(activitiesApi.active).mockResolvedValue(null);
  vi.mocked(activitiesApi.list).mockResolvedValue([]);
  vi.mocked(activitiesApi.start).mockResolvedValue(row());
  vi.mocked(activitiesApi.get).mockResolvedValue(row());
  vi.mocked(activitiesApi.cancel).mockResolvedValue(row('BALANCE_HOLD', 'CANCELLED'));
  vi.mocked(boardCalibrationApi.get).mockResolvedValue({
    configured: false,
    calibration: null,
    activeSession: null,
  });
});
function hub() {
  return render(
    <StrictMode>
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<TrainingPage />} />
          <Route
            path="/training/balance-hold"
            element={<TrainingExercisePage activityType="BALANCE_HOLD" />}
          />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
  );
}
function exercise(type: ActivityType = 'BALANCE_HOLD') {
  return render(
    <MemoryRouter>
      <TrainingExercisePage activityType={type} />
    </MemoryRouter>,
  );
}
function event(session: ActivitySession, countdown: number | null = null) {
  getMockData().live.activityStatus = {
    type: 'activity_status',
    activitySessionId: session.id,
    profileId: session.profileId,
    activityType: session.activityType,
    status: session.status,
    countdown,
    durationSeconds: session.durationSeconds,
    message: session.errorMessage,
  };
  vi.mocked(activitiesApi.get).mockResolvedValue(session);
}

describe('Training hub', () => {
  it('has three exercises and no fabricated record', async () => {
    hub();
    for (const name of ['Balance Hold', 'Weight Shift', 'Symmetry'])
      expect(screen.getByRole('region', { name })).toBeInTheDocument();
    expect(await screen.findByText('Il tuo percorso parte da qui.')).toBeInTheDocument();
    expect(screen.getAllByText('—')).toHaveLength(3);
  });
  it('blocks an offline board and shows a plain instruction', async () => {
    const data = getMockData();
    if (data.live.board) data.live.board.connected = false;
    hub();
    expect(await screen.findByText('Accendi la Balance Board per iniziare')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Inizia Balance Hold' })).toBeDisabled();
  });
  it('starts exactly once on explicit click and opens the exercise', async () => {
    vi.mocked(activitiesApi.start).mockImplementation(async () => {
      vi.mocked(activitiesApi.active).mockResolvedValue(row());
      return row();
    });
    hub();
    const button = screen.getByRole('button', { name: 'Inizia Balance Hold' });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    fireEvent.click(button);
    expect(await screen.findByText('Sali sulla Balance Board')).toBeInTheDocument();
    expect(activitiesApi.start).toHaveBeenCalledTimes(1);
    expect(activitiesApi.start).toHaveBeenCalledWith('p1', 'BALANCE_HOLD');
  });
  it('computes personal best from completed history and shows only five entries', async () => {
    const entries = Array.from({ length: 7 }, (_, i) => ({
      ...row(),
      id: `a${i}`,
      status: 'COMPLETED' as const,
      score: 600 + i,
      resultJson: { centeredPercent: 80 },
    }));
    vi.mocked(activitiesApi.list).mockResolvedValue(entries);
    hub();
    expect(await screen.findByText('606 pt')).toBeInTheDocument();
    expect(screen.getAllByText('Attività completata')).toHaveLength(5);
    expect(activitiesApi.list).toHaveBeenCalledWith('p1');
  });
  it('offers calibration without blocking the exercises', async () => {
    const data = getMockData();
    if (data.live.board) data.live.board.mode = 'real';
    hub();
    expect(
      await screen.findByRole('link', { name: 'Configura la pedana nelle Impostazioni' }),
    ).toHaveAttribute('href', '/settings');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Inizia Symmetry' })).toBeEnabled(),
    );
  });
  it.each(['measurement', 'calibration', 'training'])(
    'blocks starts while %s owns the board',
    async (owner) => {
      const data = getMockData();
      if (owner === 'measurement')
        data.live.sessionEvent = {
          type: 'session_status',
          sessionId: 'm1',
          profileId: 'p1',
          status: 'MEASURING',
          stability: 0,
          message: null,
        };
      if (owner === 'calibration' && data.live.board) data.live.board.calibrationActive = true;
      if (owner === 'training') event(row());
      hub();
      await screen.findByText('Il tuo percorso parte da qui.');
      expect(screen.getByRole('button', { name: 'Inizia Symmetry' })).toBeDisabled();
    },
  );
  it('reports REST failure and allows retry without inventing empty history', async () => {
    vi.mocked(activitiesApi.list).mockRejectedValue(new Error('Storico non disponibile'));
    hub();
    expect(await screen.findByRole('alert')).toHaveTextContent('Storico non disponibile');
    expect(screen.queryByText('Il tuo percorso parte da qui.')).not.toBeInTheDocument();
  });
});
describe('Training session', () => {
  it('shows a backend countdown', async () => {
    vi.mocked(activitiesApi.active).mockResolvedValue(row('BALANCE_HOLD', 'COUNTDOWN'));
    event(row('BALANCE_HOLD', 'COUNTDOWN'), 2);
    exercise();
    expect(await screen.findByText('2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Annulla attività' })).toBeEnabled();
  });
  it('shows live score and timer without calculating a frontend score', async () => {
    vi.mocked(activitiesApi.active).mockResolvedValue(row('BALANCE_HOLD', 'ACTIVE'));
    getMockData().live.activityReading = {
      type: 'activity_live',
      activitySessionId: 'a1',
      elapsed: 12,
      remaining: 18,
      score: 812,
      weight: 80,
      centerOfPressure: { x: 0.1, y: 0.1 },
      data: { centerRadius: 0.15 },
    };
    exercise();
    await waitFor(() =>
      expect(screen.getByLabelText('Tempo rimanente')).toHaveTextContent('00:18'),
    );
    expect(screen.getByLabelText('Punteggio')).toHaveTextContent('812');
  });
  it('shows symmetry percentages and accessible distribution', async () => {
    vi.mocked(activitiesApi.active).mockResolvedValue(row('SYMMETRY', 'ACTIVE'));
    getMockData().live.activityReading = {
      type: 'activity_live',
      activitySessionId: 'a1',
      elapsed: 12,
      remaining: 18,
      score: 800,
      weight: 80,
      centerOfPressure: { x: -0.08, y: 0 },
      data: { leftPercent: 54, rightPercent: 46 },
    };
    exercise('SYMMETRY');
    expect(await screen.findByText('54%')).toBeInTheDocument();
    expect(screen.getByText('46%')).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: 'Distribuzione a sinistra' })).toHaveAttribute(
      'value',
      '54',
    );
  });
  it('shows target direction, progress and reached feedback', async () => {
    vi.mocked(activitiesApi.active).mockResolvedValue(row('WEIGHT_SHIFT', 'ACTIVE'));
    getMockData().live.activityReading = {
      type: 'activity_live',
      activitySessionId: 'a1',
      elapsed: 12,
      remaining: 28,
      score: 380,
      weight: 80,
      centerOfPressure: { x: -0.45, y: 0 },
      data: {
        direction: 'LEFT',
        target: { x: -0.45, y: 0 },
        targetIndex: 4,
        totalTargets: 10,
        lastOutcome: 'REACHED',
      },
    };
    exercise('WEIGHT_SHIFT');
    expect(await screen.findByText('Sposta il peso: Sinistra')).toBeInTheDocument();
    expect(screen.getByLabelText('Progresso target')).toHaveTextContent('4 / 10');
    expect(screen.getByText('✓ Target raggiunto')).toBeInTheDocument();
  });
  it('renders saved aggregate results and a repeat action', async () => {
    getMockData().live.activityCompleted = {
      ...row('BALANCE_HOLD', 'COMPLETED'),
      score: 940,
      resultJson: { averageCenterDistance: 0.04, maxCenterDistance: 0.11, centeredPercent: 98 },
    };
    exercise();
    expect(await screen.findByRole('region', { name: 'Risultato Training' })).toHaveTextContent(
      '940',
    );
    expect(screen.getByText('98%')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Ripeti esercizio' })).toBeEnabled(),
    );
  });
  it('cancels without rendering a partial result', async () => {
    vi.mocked(activitiesApi.active).mockResolvedValue(row());
    exercise();
    fireEvent.click(await screen.findByRole('button', { name: 'Annulla attività' }));
    expect(await screen.findByText('Attività annullata')).toBeInTheDocument();
    expect(activitiesApi.cancel).toHaveBeenCalledWith('a1');
    expect(screen.queryByRole('region', { name: 'Risultato Training' })).not.toBeInTheDocument();
  });
  it('shows a disconnection error, hides stale readings and permits retry after reconnect', async () => {
    const session = row('BALANCE_HOLD', 'ACTIVE');
    vi.mocked(activitiesApi.active).mockResolvedValue(session);
    const view = exercise();
    await screen.findByRole('button', { name: 'Annulla attività' });
    const failed = {
      ...session,
      status: 'ERROR' as const,
      errorMessage: 'Balance Board disconnessa. L’attività è stata interrotta.',
    };
    event(failed);
    const data = getMockData();
    if (data.live.board) data.live.board.connected = false;
    await act(async () =>
      view.rerender(
        <MemoryRouter>
          <TrainingExercisePage activityType="BALANCE_HOLD" />
        </MemoryRouter>,
      ),
    );
    expect(await screen.findByText(failed.errorMessage)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ripeti esercizio' })).toBeDisabled();
    if (data.live.board) data.live.board.connected = true;
    view.rerender(
      <MemoryRouter>
        <TrainingExercisePage activityType="BALANCE_HOLD" />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Ripeti esercizio' })).toBeEnabled(),
    );
  });
});
