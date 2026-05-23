import {
  Bot,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  PackagePlus,
  Ship,
  Users,
} from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/shipments', label: 'Shipments', icon: Ship },
  { to: '/shipments/new', label: 'New Shipment', icon: PackagePlus },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/tasks', label: 'Tasks', icon: ClipboardList },
  { to: '/ai', label: 'Mock AI', icon: Bot },
];

function Layout() {
  const navigate = useNavigate();

  function logout() {
    localStorage.removeItem('access_token');
    navigate('/login');
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">FF</div>
          <div>
            <strong>Forwarding</strong>
            <span>Phase 1 Ops</span>
          </div>
        </div>
        <nav className="nav-links">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="sidebar-logout" type="button" onClick={logout} title="Logout">
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
