import {
  Activity,
  ArrowUpRight,
  ChartNoAxesCombined,
  CircleHelp,
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
  { to: '/profiles', label: 'Profili', icon: Users },
  { to: '/settings', label: 'Impostazioni', icon: Settings2 },
];
export function AppSidebar() {
  const { live } = useGraviaData();
  return (
    <aside className="sidebar">
      <NavLink to="/" className="brand" aria-label="Gravia home">
        <span className="brand-mark">
          <Activity size={23} />
        </span>
        GRAVIA<span className="brand-dot">.</span>
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
        <a href="/docs" target="_blank" rel="noreferrer" className="sidebar-help">
          <CircleHelp size={17} />
          Documentazione API
          <ArrowUpRight size={15} />
        </a>
        <p>
          Weight. Balance. Insight.
          <br />
          <span>Gravia v0.2</span>
        </p>
      </div>
    </aside>
  );
}
