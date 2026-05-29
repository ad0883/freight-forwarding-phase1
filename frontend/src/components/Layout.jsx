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
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Satellite,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Ship,
  Sun,
  Truck,
  Users,
  UserCog,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import api from '../api/client.js';
import { RoleBadge } from './States.jsx';

/* ---------------------------------------------------------------
   S1 — Simplified, role-based, grouped sidebar navigation
   --------------------------------------------------------------- */

const dailyWorkLinks = [
  { to: '/today', label: 'Today', icon: Sun },
  { to: '/shipments', label: 'Shipments', icon: Ship },
  { to: '/validation-issues', label: 'Document Check', icon: FileText },
  { to: '/manual-review', label: 'Issues', icon: AlertTriangle },
];

const operationsLinks = [
  { to: '/customs', label: 'Customs', icon: ShieldCheck },
  { to: '/transport', label: 'Transport', icon: Truck },
  { to: '/finance', label: 'Finance', icon: CreditCard },
  { to: '/approvals', label: 'Approvals', icon: FileCheck },
];

const managementLinks = [
  { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
  { to: '/predictive', label: 'Risk Alerts', icon: BarChart3 },
  { to: '/ai', label: 'AI Assistant', icon: Bot },
];

const adminAdvancedLinks = [
  { to: '/enterprise', label: 'Enterprise', icon: ShieldCheck },
  { to: '/bot-governance', label: 'AI Control', icon: Bot },
  { to: '/tracking', label: 'Tracking Setup', icon: Satellite },
  { to: '/users', label: 'Users', icon: UserCog },
  { to: '/audit-logs', label: 'Audit Logs', icon: FileClock },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/admin/tools', label: 'Admin Tools', icon: ShieldCheck },
  { to: '/email', label: 'Email Automation', icon: Mail },
  { to: '/events', label: 'Events', icon: ClipboardList },
  { to: '/rules', label: 'Rules', icon: ShieldAlert },
  { to: '/status', label: 'System Status', icon: Activity },
];

/* Extra links available to STAFF but not in the primary groups */
const staffExtraLinks = [
  { to: '/tracking', label: 'Tracking Updates', icon: Satellite },
  { to: '/tasks', label: 'Tasks', icon: ClipboardList },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/email', label: 'Email Automation', icon: Mail },
];

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

function getVisibleGroups(role) {
  if (role === 'ADMIN') {
    return [
      { label: 'Daily Work', links: dailyWorkLinks },
      { label: 'Operations', links: operationsLinks },
      { label: 'Management', links: managementLinks },
      { label: 'More', links: [
        { to: '/tasks', label: 'Tasks', icon: ClipboardList },
        { to: '/parties', label: 'Parties', icon: Users },
        { to: '/reports', label: 'Reports', icon: BarChart3 },
        { to: '/', label: 'Dashboard', icon: LayoutDashboard },
        { to: '/notifications', label: 'Notifications', icon: Bell },
      ]},
      { label: 'Admin / Advanced', links: adminAdvancedLinks },
    ];
  }
  if (role === 'STAFF') {
    return [
      { label: 'Daily Work', links: dailyWorkLinks },
      { label: 'Operations', links: operationsLinks },
      { label: 'Management', links: managementLinks },
      { label: 'More', links: staffExtraLinks },
    ];
  }
  // VIEW_ONLY
  return [
    { label: 'Daily Work', links: [
      { to: '/today', label: 'Today', icon: Sun },
      { to: '/shipments', label: 'Shipments', icon: Ship },
    ]},
    { label: 'Management', links: [
      { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
      { to: '/predictive', label: 'Risk Alerts', icon: BarChart3 },
      { to: '/reports', label: 'Reports', icon: BarChart3 },
      { to: '/ai', label: 'AI Assistant', icon: Bot },
    ]},
  ];
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

  const role = currentUser?.role || (userLoading ? 'STAFF' : 'VIEW_ONLY');
  const groups = getVisibleGroups(role);

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
          {groups.map((group) => (
            <div key={group.label}>
              <span className="nav-section-label">{group.label}</span>
              {group.links.map(({ to, label, icon: Icon }) => (
                <NavLink key={`${to}-${label}`} to={to} end={to === '/'}>
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
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
