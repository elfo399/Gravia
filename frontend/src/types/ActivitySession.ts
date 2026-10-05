export const activityTypes = ['BALANCE_HOLD', 'WEIGHT_SHIFT', 'SYMMETRY'] as const;
export type ActivityType = (typeof activityTypes)[number];
export const activityLabels = {
  WAITING_FOR_USER: 'Sali sulla Balance Board',
  COUNTDOWN: 'Preparati',
  ACTIVE: 'Attività in corso',
  COMPLETED: 'Attività completata',
  CANCELLED: 'Attività annullata',
  ERROR: 'Attività interrotta',
};
export type ActivityStatus = keyof typeof activityLabels;
export function isActivityActive(status?: ActivityStatus) {
  return status === 'WAITING_FOR_USER' || status === 'COUNTDOWN' || status === 'ACTIVE';
}
export interface ActivitySession {
  id: string;
  profileId: string;
  activityType: ActivityType;
  status: ActivityStatus;
  startedAt: string;
  completedAt: string | null;
  durationSeconds: number;
  score: number | null;
  resultJson: Record<string, number | null> | null;
  errorMessage: string | null;
  createdAt: string;
}
export interface ActivityStatusEvent {
  type: 'activity_status';
  activitySessionId: string;
  profileId: string;
  activityType: ActivityType;
  status: ActivityStatus;
  countdown: number | null;
  durationSeconds: number;
  message: string | null;
}
export interface ActivityReading {
  type: 'activity_live';
  activitySessionId: string;
  elapsed: number;
  remaining: number;
  score: number;
  weight: number;
  centerOfPressure: { x: number; y: number };
  data: {
    quality?: number;
    centerDistance?: number;
    centerRadius?: number;
    leftPercent?: number;
    rightPercent?: number;
    direction?: 'LEFT' | 'RIGHT' | 'FRONT' | 'REAR' | null;
    target?: { x: number; y: number } | null;
    targetIndex?: number;
    totalTargets?: number;
    targetsReached?: number;
    targetRadius?: number;
    lastOutcome?: 'REACHED' | 'MISSED' | null;
  };
}
