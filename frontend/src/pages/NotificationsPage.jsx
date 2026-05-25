import {
  Bell,
  Check,
  Clock3,
  Filter,
  Play,
  RefreshCcw,
  Search,
  Settings2,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const emptyFilters = {
  status: '',
  category: '',
  priority: '',
  search: '',
};

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

function formatMoney(amount, currency = 'INR') {
  return `${currency} ${Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function NotificationsPage() {
  const navigate = useNavigate();
  const [currentUser] = useState(cachedUser);
  const [notifications, setNotifications] = useState([]);
  const [summary, setSummary] = useState(null);
  const [rules, setRules] = useState([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [loading, setLoading] = useState(true);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState('');

  const canRunChecks = ['ADMIN', 'STAFF'].includes(currentUser?.role);
  const canEditRules = currentUser?.role === 'ADMIN';

  async function load() {
    setError('');
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, value]) => value !== '')
      );
      const [notificationResponse, summaryResponse] = await Promise.all([
        api.get('/notifications', { params: { ...params, limit: 100 } }),
        api.get('/notifications/daily-summary'),
      ]);
      setNotifications(notificationResponse.data);
      setSummary(summaryResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load notifications');
    } finally {
      setLoading(false);
    }
  }

  async function loadRules() {
    if (!canEditRules) return;
    setRulesLoading(true);
    try {
      const response = await api.get('/notifications/rules');
      setRules(response.data);
    } finally {
      setRulesLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filters.status, filters.category, filters.priority]);

  useEffect(() => {
    if (canEditRules) {
      loadRules();
    }
  }, [canEditRules]);

  async function searchSubmit(event) {
    event.preventDefault();
    await load();
  }

  async function updateNotification(id, action) {
    setActionMessage('');
    await api.patch(`/notifications/${id}/${action}`);
    await load();
  }

  async function markAllRead() {
    setActionMessage('');
    const response = await api.post('/notifications/mark-all-read');
    setActionMessage(`${response.data.updated} notification(s) marked read.`);
    await load();
  }

  async function runChecks() {
    setActionMessage('');
    const response = await api.post('/notifications/run-checks');
    setActionMessage(`${response.data.created} notification(s) created.`);
    await Promise.all([load(), loadRules()]);
  }

  async function updateRule(ruleId, patch) {
    const response = await api.patch(`/notifications/rules/${ruleId}`, patch);
    setRules((items) => items.map((item) => (item.id === ruleId ? response.data : item)));
  }

  function openNotification(notification) {
    if (notification.status === 'unread') {
      api.patch(`/notifications/${notification.id}/read`).catch(() => {});
    }
    navigate(notification.action_url || '/notifications');
  }

  const summaryCards = useMemo(() => {
    if (!summary) return [];
    const totals = summary.totals;
    return [
      ['Unread', totals.unread_notifications],
      ['Overdue Tasks', totals.overdue_tasks],
      ['Demurrage Risks', totals.demurrage_risks],
      ['BL Pending', totals.pending_bl_approvals],
      ['Gmail Reviews', totals.pending_gmail_suggestions],
    ];
  }, [summary]);

  if (error) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Operations</p>
            <h1>Notifications</h1>
          </div>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Notifications</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCcw size={16} />
            Refresh
          </button>
          {canRunChecks && (
            <button className="secondary-button" type="button" onClick={markAllRead}>
              <Check size={16} />
              Mark all read
            </button>
          )}
          {canRunChecks && (
            <button className="primary-button" type="button" onClick={runChecks}>
              <Play size={16} />
              Run checks
            </button>
          )}
        </div>
      </div>

      {actionMessage && <p className="success-text">{actionMessage}</p>}

      <section className="panel">
        <div className="panel-header">
          <h2>Today's Operations Summary</h2>
          {summary && <span className="muted">Generated {new Date(summary.generated_at).toLocaleString()}</span>}
        </div>
        {!summary ? (
          <LoadingState label="Loading summary..." />
        ) : (
          <>
            <div className="summary-grid">
              {summaryCards.map(([label, value]) => (
                <div className="summary-tile" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
              <div className="summary-tile wide">
                <span>Pending Receivables</span>
                <strong>{formatMoney(summary.totals.pending_receivables_total, summary.totals.currency)}</strong>
              </div>
              <div className="summary-tile wide">
                <span>Pending Payables</span>
                <strong>{formatMoney(summary.totals.pending_payables_total, summary.totals.currency)}</strong>
              </div>
            </div>
            <div className="notification-list compact">
              {(summary.top_urgent_items || []).map((item, index) => (
                <article className="notification-row" key={`${item.title}-${index}`}>
                  <span className={`badge priority-${item.priority}`}>{item.priority}</span>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.message}</p>
                  </div>
                  {item.action_url && <Link to={item.action_url}>Open</Link>}
                </article>
              ))}
              {!summary.top_urgent_items?.length && <p className="muted">No urgent notification items.</p>}
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Notification Center</h2>
        </div>
        <form className="toolbar filter-toolbar notification-filters" onSubmit={searchSubmit}>
          <div className="search-box">
            <Search size={16} />
            <input
              value={filters.search}
              onChange={(event) => setFilters((value) => ({ ...value, search: event.target.value }))}
              placeholder="Search notifications"
            />
          </div>
          <select
            value={filters.status}
            onChange={(event) => setFilters((value) => ({ ...value, status: event.target.value }))}
            title="Status"
          >
            <option value="">All statuses</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
            <option value="dismissed">Dismissed</option>
          </select>
          <select
            value={filters.category}
            onChange={(event) => setFilters((value) => ({ ...value, category: event.target.value }))}
            title="Category"
          >
            <option value="">All categories</option>
            {['task', 'shipment', 'document', 'bl', 'demurrage', 'finance', 'gmail', 'ai', 'system'].map((item) => (
              <option value={item} key={item}>{item}</option>
            ))}
          </select>
          <select
            value={filters.priority}
            onChange={(event) => setFilters((value) => ({ ...value, priority: event.target.value }))}
            title="Priority"
          >
            <option value="">All priorities</option>
            {['critical', 'warning', 'info', 'none'].map((item) => (
              <option value={item} key={item}>{item}</option>
            ))}
          </select>
          <button className="secondary-button" type="submit">
            <Filter size={16} />
            Apply
          </button>
        </form>
        {loading ? (
          <LoadingState label="Loading notifications..." />
        ) : (
          <div className="notification-list">
            {notifications.map((notification) => (
              <article className="notification-row" key={notification.id}>
                <button
                  className="notification-main"
                  type="button"
                  onClick={() => openNotification(notification)}
                >
                  <Bell size={18} />
                  <div>
                    <div className="row-actions">
                      <strong>{notification.title}</strong>
                      <span className={`badge priority-${notification.priority}`}>{notification.priority}</span>
                      <span className={`badge notification-${notification.status}`}>{notification.status}</span>
                      <span className="badge">{notification.category}</span>
                    </div>
                    <p>{notification.message}</p>
                    <span className="muted">
                      <Clock3 size={13} /> {new Date(notification.created_at).toLocaleString()}
                    </span>
                  </div>
                </button>
                {canRunChecks && (
                  <div className="row-actions">
                    {notification.status === 'unread' ? (
                      <button className="secondary-button" type="button" onClick={() => updateNotification(notification.id, 'read')}>
                        <Check size={15} />
                        Read
                      </button>
                    ) : (
                      <button className="secondary-button" type="button" onClick={() => updateNotification(notification.id, 'unread')}>
                        <RefreshCcw size={15} />
                        Unread
                      </button>
                    )}
                    <button className="secondary-button" type="button" onClick={() => updateNotification(notification.id, 'dismiss')}>
                      <X size={15} />
                      Dismiss
                    </button>
                  </div>
                )}
              </article>
            ))}
            {!notifications.length && <EmptyState title="No notifications" detail="Nothing matches the current filters." />}
          </div>
        )}
      </section>

      {canEditRules && (
        <section className="panel">
          <div className="panel-header">
            <h2>Notification Rules</h2>
            <Settings2 size={18} />
          </div>
          {rulesLoading ? (
            <LoadingState label="Loading rules..." />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Threshold</th>
                    <th>Enabled</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id}>
                      <td>
                        <strong>{rule.name}</strong>
                        <p className="muted">{rule.description}</p>
                      </td>
                      <td><span className="badge">{rule.category}</span></td>
                      <td>
                        <select value={rule.priority} onChange={(event) => updateRule(rule.id, { priority: event.target.value })}>
                          {['critical', 'warning', 'info', 'none'].map((item) => (
                            <option key={item} value={item}>{item}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          type="number"
                          min="0"
                          max="365"
                          value={rule.threshold_days ?? ''}
                          onChange={(event) => updateRule(rule.id, {
                            threshold_days: event.target.value === '' ? null : Number(event.target.value),
                          })}
                        />
                      </td>
                      <td>
                        <label className="compact-toggle">
                          <input
                            type="checkbox"
                            checked={rule.is_enabled}
                            onChange={(event) => updateRule(rule.id, { is_enabled: event.target.checked })}
                          />
                          Enabled
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default NotificationsPage;
