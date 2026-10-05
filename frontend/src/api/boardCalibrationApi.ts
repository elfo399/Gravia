import type { BoardCalibrationStatus } from '../types/BoardCalibration';
import type { CalibrationSession } from '../types/CalibrationSession';
import { apiRequest } from './apiRequest';

const root = '/board/calibration';
const sessionPath = (id: string) => `${root}/session/${encodeURIComponent(id)}`;
const post = { method: 'POST' };
const timeout = () => AbortSignal.timeout(15000);

export const boardCalibrationApi = {
  get: () => apiRequest<BoardCalibrationStatus>(root, { signal: timeout() }),
  start: () => apiRequest<CalibrationSession>(`${root}/session`, { ...post, signal: timeout() }),
  session: (id: string) => apiRequest<CalibrationSession>(sessionPath(id), { signal: timeout() }),
  tare: (id: string) =>
    apiRequest<CalibrationSession>(`${sessionPath(id)}/tare`, { ...post, signal: timeout() }),
  reference: (id: string, referenceWeight: number) =>
    apiRequest<CalibrationSession>(`${sessionPath(id)}/reference`, {
      ...post,
      body: JSON.stringify({ referenceWeight }),
      signal: timeout(),
    }),
  verify: (id: string) =>
    apiRequest<CalibrationSession>(`${sessionPath(id)}/verify`, { ...post, signal: timeout() }),
  save: (id: string) =>
    apiRequest<BoardCalibrationStatus>(`${sessionPath(id)}/save`, { ...post, signal: timeout() }),
  cancel: (id: string) =>
    apiRequest<void>(sessionPath(id), { method: 'DELETE', signal: timeout() }),
  reset: () => apiRequest<BoardCalibrationStatus>(root, { method: 'DELETE', signal: timeout() }),
};
