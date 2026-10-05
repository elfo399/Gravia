import type { MeasurementSession } from '../types/MeasurementSession';
import { apiRequest } from './apiRequest';
export const sessionsApi = {
  start: (profileId: string) =>
    apiRequest<MeasurementSession>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ profileId }),
    }),
  cancel: (id: string) =>
    apiRequest<MeasurementSession>(`/sessions/${id}/cancel`, { method: 'POST' }),
};
