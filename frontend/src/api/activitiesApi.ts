import type { ActivitySession, ActivityType } from '../types/ActivitySession';
import { apiRequest } from './apiRequest';

export const activitiesApi = {
  start: (profileId: string, activityType: ActivityType) =>
    apiRequest<ActivitySession>('/activities', {
      method: 'POST',
      body: JSON.stringify({ profileId, activityType }),
    }),
  list: (profileId: string) =>
    apiRequest<ActivitySession[]>(`/activities?${new URLSearchParams({ profileId })}`),
  get: (id: string) => apiRequest<ActivitySession>(`/activities/${id}`),
  active: () => apiRequest<ActivitySession | null>('/activities/active'),
  cancel: (id: string) =>
    apiRequest<ActivitySession>(`/activities/${id}/cancel`, { method: 'POST' }),
};
