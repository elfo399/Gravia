import { formatWeight } from '../api/weightStatistics';
import { StatisticsCards } from '../components/StatisticsCards';
import { WeightHistoryChart } from '../components/WeightHistoryChart';
import { useGraviaData } from '../hooks/useGraviaData';
export function StatisticsPage() {
  const { measurements, profileId } = useGraviaData();
  const readings = measurements.filter((item) => item.profileId === profileId);
  return (
    <>
      <div className="page-title">
        <div className="eyebrow">UNO SGUARDO D’INSIEME</div>
        <h1>Le tue statistiche</h1>
        <p>Dai singoli momenti alle tendenze del tuo percorso.</p>
      </div>
      <StatisticsCards />
      <WeightHistoryChart measurements={readings} />
      <div className="statistics-details">
        <section className="card">
          <h2>Intervallo del peso</h2>
          <p className="detail-value">
            {readings.length
              ? `${formatWeight(Math.min(...readings.map((item) => item.weight)))} – ${formatWeight(Math.max(...readings.map((item) => item.weight)))}`
              : '—'}{' '}
            <span>kg</span>
          </p>
          <p className="muted">Valore minimo e massimo registrati</p>
        </section>
        <section className="card">
          <h2>Qualità delle misurazioni</h2>
          <p className="detail-value">
            {readings.length
              ? Math.round(
                  readings.reduce((sum, item) => sum + item.stability, 0) / readings.length,
                )
              : '—'}{' '}
            <span>%</span>
          </p>
          <p className="muted">Stabilità media delle pesate completate</p>
        </section>
      </div>
      <p className="dashboard-footnote">
        Il BMI è calcolato dal peso più recente e dall’altezza attuale del profilo.
      </p>
    </>
  );
}
