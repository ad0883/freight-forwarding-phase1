import {
  Activity,
  Bot,
  BarChart3,
  ClipboardList,
  FileClock,
  LayoutDashboard,
  LogOut,
  Mail,
  Settings,
  Ship,
  ShieldCheck,
  Users,
  UserCog,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import api from '../api/client.js';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/shipments', label: 'Shipments', icon: Ship },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/tasks', label: 'Tasks', icon: ClipboardList },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/ai', label: 'AI Assistant', icon: Bot },
  { to: '/email', label: 'Email Automation', icon: Mail, writeRoleOnly: true },
  { to: '/users', label: 'Users', icon: UserCog, adminOnly: true },
  { to: '/audit-logs', label: 'Audit Logs', icon: FileClock, adminOnly: true },
  { to: '/status', label: 'Status', icon: Activity, adminOnly: true },
  { to: '/admin/tools', label: 'Admin Tools', icon: ShieldCheck, adminOnly: true },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

function canShowLink(link, currentUser, userLoading) {
  if (link.adminOnly) return currentUser?.role === 'ADMIN';
  if (link.writeRoleOnly) {
    if (!currentUser) return userLoading;
    return ['ADMIN', 'STAFF'].includes(currentUser.role);
  }
  return true;
}

function Layout() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(cachedUser);
  const [userLoading, setUserLoading] = useState(true);

  useEffect(() => {
    api
      .get('/auth/me')
      .then((response) => {
        setCurrentUser(response.data);
        localStorage.setItem('current_user', JSON.stringify(response.data));
      })
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('current_user');
        setCurrentUser(null);
        navigate('/login');
      })
      .finally(() => setUserLoading(false));
  }, [navigate]);

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
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
            .filter((link) => canShowLink(link, currentUser, userLoading))
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
