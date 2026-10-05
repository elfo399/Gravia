import type { Profile } from '../types/Profile';
import { apiRequest } from './apiRequest';
export const profilesApi = {
  list: () => apiRequest<Profile[]>('/profiles'),
  create: (name: string, heightCm: number | null) =>
    apiRequest<Profile>('/profiles', { method: 'POST', body: JSON.stringify({ name, heightCm }) }),
  update: (id: string, name: string, heightCm: number | null) =>
    apiRequest<Profile>(`/profiles/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ name, heightCm }),
    }),
  delete: (id: string) => apiRequest<void>(`/profiles/${id}`, { method: 'DELETE' }),
};
