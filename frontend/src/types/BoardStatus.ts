export interface BoardStatus {
  mode: 'demo' | 'real';
  connected: boolean;
  macAddress: string | null;
  lastSampleAt: string | null;
  lastError: string | null;
  battery: number | null;
}
