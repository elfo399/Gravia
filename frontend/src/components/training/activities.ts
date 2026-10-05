import { Activity, Move, Target } from 'lucide-react';
import type { ActivityType } from '../../types/ActivitySession';

export const exercises = {
  BALANCE_HOLD: {
    name: 'Balance Hold',
    path: '/training/balance-hold',
    icon: Target,
    subtitle: 'Trova il tuo centro',
    duration: '30 secondi',
    maximum: 1000,
    description:
      'Mantieni il punto nel cerchio centrale. Piccoli movimenti, un equilibrio più consapevole.',
    instruction: 'Resta al centro e mantieni il punto dentro il cerchio.',
  },
  WEIGHT_SHIFT: {
    name: 'Weight Shift',
    path: '/training/weight-shift',
    icon: Move,
    subtitle: 'Segui il movimento',
    duration: '10 target · fino a 40 secondi',
    maximum: 1500,
    description: 'Sposta delicatamente il peso verso il target e mantienilo per un istante.',
    instruction: 'Sposta il peso verso il target, senza sollevare i piedi.',
  },
  SYMMETRY: {
    name: 'Symmetry',
    path: '/training/symmetry',
    icon: Activity,
    subtitle: 'Due lati, un equilibrio',
    duration: '30 secondi',
    maximum: 1000,
    description:
      'Distribuisci il peso tra sinistra e destra. Cerca un appoggio uniforme sui due piedi.',
    instruction: 'Distribuisci il peso sui due piedi. Obiettivo: 45–55% per lato.',
  },
} satisfies Record<
  ActivityType,
  {
    name: string;
    path: string;
    icon: typeof Target;
    subtitle: string;
    duration: string;
    maximum: number;
    description: string;
    instruction: string;
  }
>;
export const directions = { LEFT: 'Sinistra', RIGHT: 'Destra', FRONT: 'Avanti', REAR: 'Dietro' };
