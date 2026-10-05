export interface Sensors {
  frontLeft: number;
  frontRight: number;
  rearLeft: number;
  rearRight: number;
}
export interface Measurement extends Sensors {
  id: string;
  sessionId: string;
  profileId: string;
  weight: number;
  centerX: number;
  centerY: number;
  stability: number;
  measuredAt: string;
  createdAt: string;
  notes: string | null;
}
export interface LiveMeasurement {
  sessionId: string;
  weight: number;
  stability: number;
  sensors: Sensors;
  centerOfPressure: { x: number; y: number };
}
