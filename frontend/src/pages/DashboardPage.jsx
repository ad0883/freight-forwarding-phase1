import { AlertTriangle, Bell, CheckCircle2, Clock, DollarSign, Ship, Timer, WalletCards } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [dailySummary, setDailySummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [validationIssues, setValidationIssues] = useState(null);
  const [workflowControl, setWorkflowControl] = useState(null);
  const [error, setError] = useState('');

  async function load() {
    setError('');
    try {
      const [dashboardResponse, financialResponse] = await Promise.all([
        api.get('/shipments/dashboard'),
        api.get('/reports/dashboard-financials'),
      ]);
      setSummary(dashboardResponse.data);
      setFinancials(financialResponse.data);
      setAlerts(dashboardResponse.data.recent_alerts || []);
      api
        .get('/notifications/daily-summary')
        .then((response) => setDailySummary(response.data))
        .catch(() => setDailySummary(null));
      api
        .get('/validation-issues', { params: { status: 'open', limit: 5 } })
        .then((response) => setValidationIssues(response.data))
        .catch(() => setValidationIssues(null));
      Promise.all([
        api.get('/shipments', { params: { include_archived: false } }).catch(() => ({ data: [] })),
        api.get('/events', { params: { event_type: 'workflow.transition_requested', limit: 10 } }).catch(() => ({ data: [] })),
      ])
        .then(([shipmentsResponse, eventsResponse]) => {
          const flagged = (shipmentsResponse.data || []).filter((s) => s.manual_review_required);
          const blocked = (eventsResponse.data || []).filter((e) => {
            const meta = e.metadata_json || {};
            return meta.outcome === 'blocked' || meta.outcome === 'manual_review_required';
          });
          const missing = (shipmentsResponse.data || []).filter((s) => !s.workflow_state);
          setWorkflowControl({ flagged, blocked, missing });
        })
        .catch(() => setWorkflowControl(null));
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load dashboard');
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Operations</p>
            <h1>Dashboard</h1>
          </div>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  if (!summary || !financials) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Operations</p>
            <h1>Dashboard</h1>
          </div>
        </div>
        <LoadingState label="Loading dashboard..." />
      </div>
    );
  }

  const cards = [
    { label: 'Live Shipments', value: summary.live_shipments, icon: Ship },
    { label: 'Pending Tasks', value: summary.pending_tasks, icon: Clock },
    { label: 'Future Bookings', value: summary.future_bookings, icon: Timer },
    { label: 'Alerts Today', value: summary.alerts_today, icon: AlertTriangle },
    { label: 'Completed This Month', value: summary.completed_this_month, icon: CheckCircle2 },
  ];
  const formatMoney = (amount, currency = 'INR') =>
    `${currency} ${Number(amount || 0).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  const financeCards = [
    { label: 'Pending Receivables', value: formatMoney(financials.pending_receivables, financials.currency), icon: WalletCards, className: 'warning-card' },
    { label: 'Pending Payables', value: formatMoney(financials.pending_payables, financials.currency), icon: WalletCards, className: 'info-card' },
    { label: 'This Month Receivables', value: formatMoney(financials.this_month_receivables, financials.currency), icon: DollarSign, className: 'success-card' },
    { label: 'This Month Payables', value: formatMoney(financials.this_month_payables, financials.currency), icon: DollarSign, className: 'info-card' },
    {
      label: 'This Month Profit',
      value: formatMoney(financials.this_month_profit, financials.currency),
      icon: DollarSign,
      className: Number(financials.this_month_profit) < 0 ? 'critical-card' : 'success-card',
    },
  ];

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Dashboard</h1>
        </div>
        <Link className="primary-button" to="/shipments/new">
          New Shipment
        </Link>
      </div>

      <section className="metric-grid">
        {cards.map(({ label, value, icon: Icon }) => (
          <article className="metric-card" key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <div className="panel-header no-margin">
        <h2>Financial Summary</h2>
      </div>
      <section className="metric-grid finance-grid">
        {financeCards.map(({ label, value, icon: Icon, className }) => (
          <article className={`metric-card ${className}`} key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>
      {financials.multiple_currencies && (
        <p className="finance-note">Multiple currencies are present. Totals are not converted automatically.</p>
      )}

      {dailySummary && (
        <section className="panel">
          <div className="panel-header">
            <h2>Today's Operations Summary</h2>
            <Link to="/notifications">View notifications</Link>
          </div>
          <div className="dashboard-summary-strip">
            <div>
              <Bell size={18} />
              <span>Unread</span>
              <strong>{dailySummary.totals.unread_notifications}</strong>
            </div>
            <div>
              <AlertTriangle size={18} />
              <span>Overdue</span>
              <strong>{dailySummary.totals.overdue_tasks}</strong>
            </div>
            <div>
              <Timer size={18} />
              <span>Demurrage</span>
              <strong>{dailySummary.totals.demurrage_risks}</strong>
            </div>
            <div>
              <Clock size={18} />
              <span>BL Pending</span>
              <strong>{dailySummary.totals.pending_bl_approvals}</strong>
            </div>
          </div>
          <div className="notification-list compact">
            {(dailySummary.top_urgent_items || []).slice(0, 3).map((item, index) => (
              <article className="notification-row" key={`${item.title}-${index}`}>
                <span className={`badge priority-${item.priority}`}>{item.priority}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.message}</p>
                </div>
              </article>
            ))}
            {!dailySummary.top_urgent_items?.length && <p className="muted">No urgent notification items.</p>}
          </div>
        </section>
      )}

      {validationIssues !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Validation & Manual Review</h2>
            <Link to="/validation-issues">View all</Link>
          </div>
          {validationIssues.length === 0 ? (
            <p className="muted">No open validation issues.</p>
          ) : (
            <div className="notification-list compact">
              {validationIssues.map((issue) => (
                <article className="notification-row" key={issue.id}>
                  <span className={`badge priority-${issue.severity}`}>{issue.severity}</span>
                  <div>
                    <strong>{issue.rule_key}</strong>
                    <p>{issue.message}</p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {workflowControl !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Workflow Control</h2>
            <Link to="/events">Recent events</Link>
          </div>
          <div className="dashboard-summary-strip">
            <div>
              <span>Manual review</span>
              <strong>{workflowControl.flagged.length}</strong>
            </div>
            <div>
              <span>Recent blocked</span>
              <strong>{workflowControl.blocked.length}</strong>
            </div>
            <div>
              <span>No workflow state</span>
              <strong>{workflowControl.missing.length}</strong>
            </div>
          </div>
          {workflowControl.flagged.length > 0 ? (
            <div className="notification-list compact">
              {workflowControl.flagged.slice(0, 3).map((shipment) => (
                <article className="notification-row" key={shipment.id}>
                  <span className="badge priority-critical">manual review</span>
                  <div>
                    <strong>{shipment.shipment_code}</strong>
                    <p>{shipment.manual_review_reason || 'Manual review required'}</p>
                  </div>
                  <Link to={`/shipments/${shipment.id}`}>Open</Link>
                </article>
              ))}
            </div>
          ) : (
            <p className="muted">No shipments need manual workflow review.</p>
          )}
        </section>
      )}

      <section className="split-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Recent Shipments</h2>
            <Link to="/shipments">View all</Link>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Shipment ID</th>
                  <th>Type</th>
                  <th>Shipping Line</th>
                  <th>ETD</th>
                  <th>ETA</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {summary.shipments.map((shipment) => (
                  <tr key={shipment.id}>
                    <td>
                      <Link to={`/shipments/${shipment.id}`}>{shipment.shipment_code}</Link>
                    </td>
                    <td>{shipment.type}</td>
                    <td>{shipment.shipping_line || '-'}</td>
                    <td>{shipment.etd || '-'}</td>
                    <td>{shipment.eta || '-'}</td>
                    <td>
                      <span className={`badge status-${shipment.status}`}>{shipment.status}</span>
                    </td>
                  </tr>
                ))}
                {!summary.shipments.length && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', color: '#718096' }}>No shipments yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="page-stack">
          <div className="panel">
            <div className="panel-header">
              <h2>Pending Tasks</h2>
              <Link to="/tasks">View all</Link>
            </div>
            <div className="alert-list">
              {(summary.urgent_tasks || []).map((task) => (
                <article className="alert-item" key={task.id}>
                  <span className={`badge priority-${task.priority}`}>{task.priority}</span>
                  <strong>{task.title}</strong>
                  <p>Shipment #{task.shipment_id}{task.due_date ? ` · due ${task.due_date}` : ''}</p>
                </article>
              ))}
              {!(summary.urgent_tasks || []).length && <p className="muted">No pending tasks.</p>}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Recent Critical Alerts</h2>
            </div>
            <div className="alert-list">
              {alerts.map((alert) => (
                <article className="alert-item" key={alert.id}>
                  <span className={`badge priority-${alert.priority}`}>{alert.priority}</span>
                  <strong>{alert.title}</strong>
                  <p>{alert.message}</p>
                </article>
              ))}
              {!alerts.length && <p className="muted">No critical alerts.</p>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
