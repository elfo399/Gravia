import { ArrowRight, Clock3, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate, formatWeight } from '../api/weightStatistics';
import { CurrentWeightCard } from '../components/CurrentWeightCard';
import { BmiCard, DashboardSummary } from '../components/DashboardSummary';
import { PressureSensorsCard } from '../components/PressureSensorsCard';
import { WeightHistoryChart } from '../components/WeightHistoryChart';
import { useBoardReading } from '../hooks/useBoardReading';
import { useGraviaData } from '../hooks/useGraviaData';
export function DashboardPage() {
  const { profile, profileId, measurements } = useGraviaData();
  const { reading, showingLive, active } = useBoardReading();
  const readings = measurements.filter((item) => item.profileId === profileId);
  return (
    <div className="dashboard-page">
      <h1 className="sr-only">Dashboard di {profile?.name || 'Gravia'}</h1>
      <div className="dashboard-grid">
        <CurrentWeightCard />
        <PressureSensorsCard reading={reading} live={showingLive && active} />
        <WeightHistoryChart measurements={readings} />
        <section className="card recent-card">
          <div className="card-heading">
            <h2>
              <span className="heading-icon">
                <Clock3 size={20} />
              </span>
              Ultime misurazioni
            </h2>
            <Link to="/history" className="view-all" aria-label="Apri storico">
              Vedi tutto <ArrowRight size={15} />
            </Link>
          </div>
          {readings.length ? (
            <div className="table-scroll recent-table">
              <table>
                <thead>
                  <tr>
                    <th>Data e ora</th>
                    <th>Peso (kg)</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {readings.slice(0, 6).map((item) => (
                    <tr key={item.id}>
                      <td>{formatDate(item.measuredAt)}</td>
                      <td>
                        <strong>{formatWeight(item.weight)}</strong>
                      </td>
                      <td>
                        <span title={item.notes || undefined}>{item.notes || '—'}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="recent-empty">
              <Sparkles size={25} />
              <h3>Un nuovo inizio</h3>
              <p>Le tue pesate appariranno qui, una alla volta.</p>
            </div>
          )}
        </section>
        <DashboardSummary />
        <BmiCard />
      </div>
    </div>
  );
}
