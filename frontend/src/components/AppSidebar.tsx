import {
  Activity,
  ArrowUpRight,
  Battery,
  ChartNoAxesCombined,
  CircleHelp,
  Gauge,
  History,
  LayoutDashboard,
  Scale,
  Settings2,
  Users,
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useGraviaData } from '../hooks/useGraviaData';

const navigation = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/history', label: 'Storico', icon: History },
  { to: '/statistics', label: 'Statistiche', icon: ChartNoAxesCombined },
  { to: '/training', label: 'Training', icon: Activity },
  { to: '/profiles', label: 'Profili', icon: Users },
  { to: '/settings', label: 'Impostazioni', icon: Settings2 },
];
export function AppSidebar() {
  const { live } = useGraviaData();
  return (
    <aside className="sidebar">
      <NavLink to="/" className="brand" aria-label="Gravia home">
        <span className="brand-mark">
          <Gauge size={40} strokeWidth={1.5} />
        </span>
        <span className="brand-copy">
          <b>Gravia</b>
          <small>Weight. Balance. Insight.</small>
        </span>
      </NavLink>
      <div className="sidebar-caption">IL TUO SPAZIO</div>
      <nav>
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Icon size={19} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="board-mini">
          <div className="board-mini-heading">
            <Scale size={22} />
            <div>
              <strong>Balance Board</strong>
              <span>
                <i className={`status-dot ${live.board?.connected ? '' : 'offline'}`} />
                {live.board?.mode === 'demo'
                  ? 'Modalità demo'
                  : live.board?.connected
                    ? 'Connessa'
                    : 'Non connessa'}
              </span>
            </div>
          </div>
          {live.board?.battery != null && (
            <div className="board-battery">
              <span>
                Batteria{' '}
                <b>
                  <Battery size={15} />
                  {live.board.battery}%
                </b>
              </span>
              <div className="meter-track">
                <span style={{ width: `${live.board.battery}%` }} />
              </div>
            </div>
          )}
          <p>
            {live.board?.mode === 'demo'
              ? 'Esplora Gravia senza hardware'
              : 'Wii Balance Board · Bluetooth'}
          </p>
        </div>
        <a href="/docs" target="_blank" rel="noreferrer" className="sidebar-help">
          <CircleHelp size={17} />
          Documentazione API
          <ArrowUpRight size={15} />
        </a>
        <p>
          Weight. Balance. Insight.
          <br />
          <span>Gravia v0.3</span>
        </p>
      </div>
    </aside>
  );
}
