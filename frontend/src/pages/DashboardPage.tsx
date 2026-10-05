import { ArrowRight, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate, formatWeight } from '../api/weightStatistics';
import { CurrentWeightCard } from '../components/CurrentWeightCard';
import { PressureMap } from '../components/PressureMap';
import { StatisticsCards } from '../components/StatisticsCards';
import { WeightHistoryChart } from '../components/WeightHistoryChart';
import { useGraviaData } from '../hooks/useGraviaData';
export function DashboardPage() {
  const { profile, profileId, measurements, live } = useGraviaData();
  const readings = measurements.filter((item) => item.profileId === profileId);
  return (
    <>
      <div className="page-title">
        <div className="eyebrow">IL TUO BENESSERE, IN PROSPETTIVA</div>
        <h1>
          Ciao, {profile?.name || 'benvenuto'}
          <span className="greeting-dot">.</span>
        </h1>
        <p>Prenditi un momento per te. Al resto pensa Gravia.</p>
      </div>
      <div className="dashboard-main">
        <CurrentWeightCard />
        <PressureMap reading={live.sessionEvent?.profileId === profileId ? live.reading : null} />
      </div>
      <StatisticsCards />
      <div className="dashboard-bottom">
        <WeightHistoryChart measurements={readings} />
        <section className="card recent-card">
          <div className="card-heading">
            <h2>Ultime misurazioni</h2>
            <Link to="/history" aria-label="Apri storico">
              <ArrowRight size={19} />
            </Link>
          </div>
          {readings.length ? (
            readings.slice(0, 3).map((item) => (
              <div className="recent-reading" key={item.id}>
                <div>
                  <strong>
                    {formatWeight(item.weight)} <span>kg</span>
                  </strong>
                  <p>{formatDate(item.measuredAt)}</p>
                </div>
                <span className="stability-badge">{Math.round(item.stability)}%</span>
              </div>
            ))
          ) : (
            <div className="recent-empty">
              <Sparkles size={25} />
              <h3>Un nuovo inizio</h3>
              <p>Le tue pesate appariranno qui, una alla volta.</p>
            </div>
          )}
          <div className="insight-note">
            <span>BUONO A SAPERSI</span>
            <p>Misurati alla stessa ora per confrontare meglio i tuoi progressi.</p>
          </div>
        </section>
      </div>
      <p className="dashboard-footnote">
        Un numero racconta un momento. Il tuo percorso racconta molto di più.
      </p>
    </>
  );
}
