import type { Measurement } from '../types/Measurement';
import { apiRequest } from './apiRequest';
export const measurementsApi = {
  list: (profileId?: string, from?: string, to?: string) => {
    const query = new URLSearchParams();
    if (profileId) query.set('profileId', profileId);
    if (from) query.set('from', from);
    if (to) query.set('to', to);
    return apiRequest<Measurement[]>(`/measurements?${query}`);
  },
  update: (id: string, notes: string) =>
    apiRequest<Measurement>(`/measurements/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ notes }),
    }),
  delete: (id: string) => apiRequest<void>(`/measurements/${id}`, { method: 'DELETE' }),
};
