import { CalendarDays, Radio, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { AppSidebar } from './components/AppSidebar';
import { ProfileSelector } from './components/ProfileSelector';
import { ThemeToggle } from './components/ThemeControls';
import { Button } from './components/ui/Button';
import { GraviaDataProvider, useGraviaData } from './hooks/useGraviaData';
import { ThemeProvider } from './hooks/useTheme';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { ProfilesPage } from './pages/ProfilesPage';
import { SettingsPage } from './pages/SettingsPage';
import { StatisticsPage } from './pages/StatisticsPage';

function HeaderDate() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="topbar-date">
      <CalendarDays size={20} />
      <time dateTime={now.toISOString()}>
        <span>
          {now.toLocaleDateString('it-IT', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric',
          })}
        </span>
        <strong>{now.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}</strong>
      </time>
    </div>
  );
}

function AppLayout() {
  const { loading, error, refresh, live } = useGraviaData();
  return (
    <div className="app-layout">
      <AppSidebar />
      <div className="main-shell">
        <header className="topbar">
          <Link to="/" className="mobile-brand" aria-label="Gravia home">
            Gravia
          </Link>
          <div className="topbar-intro">
            <strong>Il tuo spazio quotidiano</strong>
            <span>Peso, equilibrio e progressi.</span>
          </div>
          <HeaderDate />
          <div className={`connection-status ${live.connected ? '' : 'offline'}`}>
            <Radio size={15} />
            {live.connected ? 'Live connesso' : 'Riconnessione realtime…'}
          </div>
          <ThemeToggle />
          <ProfileSelector />
        </header>
        <main>
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <Button variant="outline" onClick={() => refresh()}>
                <RefreshCw size={16} />
                Riprova
              </Button>
            </div>
          )}
          {!live.connected && !loading && (
            <div className="connection-banner" role="status">
              Il realtime è disconnesso. Gravia sta provando a riconnettersi.
            </div>
          )}
          {loading ? (
            <div className="loading-layout" role="status" aria-label="Caricamento dashboard">
              <div />
              <div />
              <div />
            </div>
          ) : (
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/statistics" element={<StatisticsPage />} />
              <Route path="/profiles" element={<ProfilesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route
                path="*"
                element={
                  <div className="card empty-state">
                    <h1>Pagina non trovata</h1>
                    <Link to="/">Torna alla dashboard</Link>
                  </div>
                }
              />
            </Routes>
          )}
        </main>
      </div>
    </div>
  );
}
export function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <GraviaDataProvider>
          <AppLayout />
        </GraviaDataProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
