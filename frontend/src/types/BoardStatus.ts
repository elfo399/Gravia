export interface BoardStatus {
  mode: 'demo' | 'real';
  connected: boolean;
  state?: 'WAITING_FOR_POWER' | 'CONNECTING' | 'CONNECTED' | 'DISCONNECTING' | null;
  macAddress: string | null;
  lastSampleAt: string | null;
  lastError: string | null;
  battery: number | null;
}
