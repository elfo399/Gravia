export type SessionStatus =
  | 'WAITING_FOR_USER'
  | 'MEASURING'
  | 'STABILIZING'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'ERROR';
export interface MeasurementSession {
  id: string;
  profileId: string;
  status: SessionStatus;
  startedAt: string;
  endedAt: string | null;
  errorMessage: string | null;
}
export const activeStatuses: SessionStatus[] = ['WAITING_FOR_USER', 'MEASURING', 'STABILIZING'];
export const sessionLabels: Record<SessionStatus, string> = {
  WAITING_FOR_USER: 'Sali sulla bilancia',
  MEASURING: 'Misurazione in corso',
  STABILIZING: 'Resta fermo',
  COMPLETED: 'Misurazione completata',
  CANCELLED: 'Misurazione annullata',
  ERROR: 'Misurazione interrotta',
};
