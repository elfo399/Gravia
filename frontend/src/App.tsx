import { Radio, RefreshCw } from 'lucide-react';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { AppSidebar } from './components/AppSidebar';
import { ProfileSelector } from './components/ProfileSelector';
import { Button } from './components/ui/Button';
import { GraviaDataProvider, useGraviaData } from './hooks/useGraviaData';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { ProfilesPage } from './pages/ProfilesPage';
import { SettingsPage } from './pages/SettingsPage';
import { StatisticsPage } from './pages/StatisticsPage';

function AppLayout() {
  const { loading, error, refresh, live } = useGraviaData();
  return (
    <div className="app-layout">
      <AppSidebar />
      <div className="main-shell">
        <header className="topbar">
          <Link to="/" className="mobile-brand" aria-label="Gravia home">
            GRAVIA<span>.</span>
          </Link>
          <div className="topbar-date">
            {new Date().toLocaleDateString('it-IT', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </div>
          <div className={`connection-status ${live.connected ? '' : 'offline'}`}>
            <Radio size={15} />
            {live.connected ? 'Live connesso' : 'Riconnessione realtime…'}
          </div>
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
      <GraviaDataProvider>
        <AppLayout />
      </GraviaDataProvider>
    </BrowserRouter>
  );
}
