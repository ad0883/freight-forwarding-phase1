import {
  Bell,
  Check,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import api from '../api/client.js';
import { RoleBadge } from './States.jsx';
import { getRoleMode, getModeLabel, getNavigationGroups } from '../utils/roleMode.js';
import { useFeatures } from '../context/FeatureContext.jsx';

/* ---------------------------------------------------------------
   S2 — Role-mode-based sidebar navigation
   Uses centralized config from utils/roleMode.js
   --------------------------------------------------------------- */

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
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
  const mode = getRoleMode(role);
  const groups = getNavigationGroups(mode);
  
  const { features = {} } = useFeatures();

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
          {groups.map((group) => {
            // Filter links based on feature keys
            const availableLinks = group.links.filter(link => {
              if (!link.featureKey) return true;
              return features[link.featureKey];
            });

            if (availableLinks.length === 0) return null;

            return (
              <div key={group.label}>
                <span className="nav-section-label">{group.label}</span>
                {availableLinks.map(({ to, label, icon: Icon }) => (
                  <NavLink key={`${to}-${label}`} to={to} end={to === '/'}>
                    <Icon size={18} />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            );
          })}
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
              <span className={`role-mode-badge mode-${mode}`}>{getModeLabel(mode)} Mode</span>
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
