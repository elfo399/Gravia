import type { ActivityReading } from '../../types/ActivitySession';

export function SymmetryMeter({ reading }: { reading: ActivityReading | null }) {
  const left = reading?.data.leftPercent;
  const right = reading?.data.rightPercent;
  const format = (value?: number) => (value == null ? '—' : `${Math.round(value)}%`);
  return (
    <div className="symmetry-meter">
      <div className="symmetry-values">
        <div>
          <span>Sinistra</span>
          <strong>{format(left)}</strong>
        </div>
        <div>
          <span>Destra</span>
          <strong>{format(right)}</strong>
        </div>
      </div>
      <meter
        className="training-accessible-meter"
        aria-label="Distribuzione a sinistra"
        min={0}
        max={100}
        value={left ?? 50}
        aria-valuetext={
          left == null
            ? 'In attesa di letture'
            : `${Math.round(left)}% sinistra, ${Math.round(right ?? 0)}% destra`
        }
      />
      <div className="symmetry-track" aria-hidden="true">
        <span style={{ width: `${left ?? 50}%` }} />
        <i />
      </div>
      <div className="symmetry-scale">
        <span>0%</span>
        <b>50 / 50</b>
        <span>100%</span>
      </div>
      <p>
        Zona di equilibrio: <strong>45–55%</strong> per lato
      </p>
    </div>
  );
}
