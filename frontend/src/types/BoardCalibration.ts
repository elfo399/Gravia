import type { CalibrationSession } from './CalibrationSession';

export interface BoardCalibration {
  boardMac: string;
  weightScale: number;
  referenceWeight: number;
  calibratedAt: string;
  measuredWeightBefore: number;
  measuredWeightAfter: number;
}

export interface BoardCalibrationStatus {
  configured: boolean;
  calibration: BoardCalibration | null;
  activeSession: CalibrationSession | null;
}
