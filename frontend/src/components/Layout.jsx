import {
  Activity,
  Bot,
  BarChart3,
  ClipboardList,
  FileClock,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Settings,
  Ship,
  ShieldCheck,
  Users,
  UserCog,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import api from '../api/client.js';
import { RoleBadge } from './States.jsx';

const mainLinks = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/shipments', label: 'Shipments', icon: Ship },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/tasks', label: 'Tasks', icon: ClipboardList },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/ai', label: 'AI Assistant', icon: Bot },
  { to: '/email', label: 'Email Automation', icon: Mail, writeRoleOnly: true },
];

const adminLinks = [
  { to: '/users', label: 'Users', icon: UserCog, adminOnly: true },
  { to: '/audit-logs', label: 'Audit Logs', icon: FileClock, adminOnly: true },
  { to: '/status', label: 'Status', icon: Activity, adminOnly: true },
  { to: '/admin/tools', label: 'Admin Tools', icon: ShieldCheck, adminOnly: true },
];

const bottomLinks = [
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
  const location = useLocation();
  const [currentUser, setCurrentUser] = useState(cachedUser);
  const [userLoading, setUserLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    navigate('/login');
  }

  const visibleAdminLinks = adminLinks.filter((link) => canShowLink(link, currentUser, userLoading));

  return (
    <div className="app-shell">
      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">LM</div>
          <div>
            <strong>Logistics Manager</strong>
            <span>Freight Operations</span>
          </div>
        </div>
        <nav className="nav-links">
          {mainLinks
            .filter((link) => canShowLink(link, currentUser, userLoading))
            .map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'}>
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            ))}
          {visibleAdminLinks.length > 0 && (
            <>
              <span className="nav-section-label">Administration</span>
              {visibleAdminLinks.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to}>
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </>
          )}
          {bottomLinks.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {currentUser && (
            <div className="sidebar-user">
              <div className="sidebar-user-info">
                <span className="sidebar-user-name">{currentUser.name}</span>
                <span className="sidebar-user-role">{currentUser.role}</span>
              </div>
              <RoleBadge role={currentUser.role} />
            </div>
          )}
          <button className="sidebar-logout" type="button" onClick={logout} title="Logout">
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
      <button
        className="mobile-menu-toggle"
        type="button"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        title={sidebarOpen ? 'Close menu' : 'Open menu'}
      >
        {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
      </button>
    </div>
  );
}

export default Layout;
