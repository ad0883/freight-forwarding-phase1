import {
  Bot,
  BarChart3,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Mail,
  PackagePlus,
  Ship,
  Users,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import api from '../api/client.js';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/shipments', label: 'Shipments', icon: Ship },
  { to: '/shipments/new', label: 'New Shipment', icon: PackagePlus },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/tasks', label: 'Tasks', icon: ClipboardList },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/ai', label: 'AI Assistant', icon: Bot },
  { to: '/email', label: 'Email Automation', icon: Mail, writeRoleOnly: true },
];

function Layout() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    api.get('/auth/me').then((response) => setCurrentUser(response.data)).catch(() => setCurrentUser(null));
  }, []);

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
          {links
            .filter((link) => !link.writeRoleOnly || ['ADMIN', 'STAFF'].includes(currentUser?.role))
            .map(({ to, label, icon: Icon }) => (
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
