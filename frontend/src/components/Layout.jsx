import {
  Activity,
  AlertTriangle,
  Bot,
  BarChart3,
  Bell,
  Check,
  ClipboardList,
  CreditCard,
  FileCheck,
  FileClock,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Satellite,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Ship,
  Truck,
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
  { to: '/control-tower', label: 'Control Tower', icon: Activity },
  { to: '/shipments', label: 'Shipments', icon: Ship },
  { to: '/customs', label: 'Customs', icon: ShieldCheck, writeRoleOnly: true },
  { to: '/transport', label: 'Transport', icon: Truck },
  { to: '/tracking', label: 'Tracking', icon: Satellite },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/tasks', label: 'Tasks', icon: ClipboardList },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/finance', label: 'Finance', icon: CreditCard },
  { to: '/ai', label: 'AI Assistant', icon: Bot },
  { to: '/email', label: 'Email Automation', icon: Mail, writeRoleOnly: true },
];

const adminLinks = [
  { to: '/users', label: 'Users', icon: UserCog, adminOnly: true },
  { to: '/audit-logs', label: 'Audit Logs', icon: FileClock, adminOnly: true },
  { to: '/status', label: 'Status', icon: Activity, adminOnly: true },
  { to: '/admin/tools', label: 'Admin Tools', icon: ShieldCheck, adminOnly: true },
];

const operationalBrainLinks = [
  { to: '/predictive', label: 'Predictive', icon: BarChart3 },
  { to: '/manual-review', label: 'Manual Review', icon: AlertTriangle },
  { to: '/approvals', label: 'Approvals', icon: FileCheck },
  { to: '/bot-governance', label: 'Bot Governance', icon: Bot },
  { to: '/events', label: 'Events', icon: ScrollText, writeRoleOnly: true },
  { to: '/validation-issues', label: 'Validation Issues', icon: ShieldAlert, writeRoleOnly: true },
  { to: '/rules', label: 'Rules', icon: GitBranch, writeRoleOnly: true },
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
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [recentNotifications, setRecentNotifications] = useState([]);

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

  useEffect(() => {
    if (!currentUser) return undefined;
    let alive = true;
    async function loadNotifications() {
      try {
        const [countResponse, notificationsResponse] = await Promise.all([
          api.get('/notifications/unread-count'),
          api.get('/notifications', { params: { status: 'unread', limit: 5 } }),
        ]);
        if (!alive) return;
        setUnreadCount(countResponse.data.unread_count || 0);
        setRecentNotifications(notificationsResponse.data || []);
      } catch {
        if (!alive) return;
        setUnreadCount(0);
        setRecentNotifications([]);
      }
    }
    loadNotifications();
    const interval = window.setInterval(loadNotifications, 60000);
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [currentUser, location.pathname]);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    navigate('/login');
  }

  async function openNotification(notification) {
    if (['ADMIN', 'STAFF'].includes(currentUser?.role)) {
      try {
        await api.patch(`/notifications/${notification.id}/read`);
      } catch {
        // Keep navigation responsive even if the read marker fails.
      }
    }
    setNotificationOpen(false);
    navigate(notification.action_url || '/notifications');
  }

  const visibleAdminLinks = adminLinks.filter((link) => canShowLink(link, currentUser, userLoading));
  const visibleOperationalBrainLinks = operationalBrainLinks.filter((link) =>
    canShowLink(link, currentUser, userLoading)
  );

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
          {visibleOperationalBrainLinks.length > 0 && (
            <>
              <span className="nav-section-label">Operational Brain</span>
              {visibleOperationalBrainLinks.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to}>
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </>
          )}
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
            <div className="notification-bell-wrap">
              <button
                className="notification-bell"
                type="button"
                onClick={() => setNotificationOpen((value) => !value)}
                title="Notifications"
              >
                <Bell size={18} />
                <span>Notifications</span>
                {unreadCount > 0 && <strong>{unreadCount > 99 ? '99+' : unreadCount}</strong>}
              </button>
              {notificationOpen && (
                <div className="notification-popover">
                  <div className="panel-header">
                    <h2>Unread</h2>
                    <button className="icon-button" type="button" onClick={() => navigate('/notifications')} title="Open notifications">
                      <Check size={16} />
                    </button>
                  </div>
                  <div className="notification-popover-list">
                    {recentNotifications.map((notification) => (
                      <button
                        type="button"
                        key={notification.id}
                        onClick={() => openNotification(notification)}
                      >
                        <span className={`badge priority-${notification.priority}`}>{notification.priority}</span>
                        <strong>{notification.title}</strong>
                        <p>{notification.message}</p>
                      </button>
                    ))}
                    {!recentNotifications.length && <p className="muted">No unread notifications.</p>}
                  </div>
                  <button className="secondary-button" type="button" onClick={() => navigate('/notifications')}>
                    View all
                  </button>
                </div>
              )}
            </div>
          )}
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
