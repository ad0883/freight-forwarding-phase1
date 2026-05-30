import { AlertTriangle, Bell, CheckCircle2, Clock, DollarSign, FileText, Ship, Timer, UploadCloud, WalletCards } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';
import { getRoleMode, getRoleHelperPrefix } from '../utils/roleMode.js';

function DashboardPage() {
  const currentUser = (() => { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } })();
  const mode = getRoleMode(currentUser?.role);
  const [summary, setSummary] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [dailySummary, setDailySummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [validationIssues, setValidationIssues] = useState(null);
  const [workflowControl, setWorkflowControl] = useState(null);
  const [containerRisk, setContainerRisk] = useState(null);
  const [documentSummary, setDocumentSummary] = useState(null);
  const [documentIntelligence, setDocumentIntelligence] = useState(null);
  const [financeOverview, setFinanceOverview] = useState(null);
  const [exceptionSummary, setExceptionSummary] = useState(null);
  const [approvalSummary, setApprovalSummary] = useState(null);
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
      api
        .get('/containers/risk', { params: { limit: 5 } })
        .then((response) => setContainerRisk(response.data))
        .catch(() => setContainerRisk(null));
      api
        .get('/document-versions/dashboard-summary', { timeout: 8000 })
        .then((response) => setDocumentSummary(response.data))
        .catch(() => setDocumentSummary(null));
      api
        .get('/document-intelligence/dashboard-summary')
        .then((response) => setDocumentIntelligence(response.data))
        .catch(() => setDocumentIntelligence(null));
      api
        .get('/finance/overview')
        .then((response) => setFinanceOverview(response.data))
        .catch(() => setFinanceOverview(null));
      api
        .get('/exceptions/summary')
        .then((response) => setExceptionSummary(response.data))
        .catch(() => setExceptionSummary(null));
      api
        .get('/approvals/summary')
        .then((response) => setApprovalSummary(response.data))
        .catch(() => setApprovalSummary(null));
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
      <p className="page-helper">{getRoleHelperPrefix(mode)}Full operational metrics. For daily action items, use the Today page.</p>
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

      {documentSummary !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Document Review</h2>
            <Link to="/shipments">Open shipments</Link>
          </div>
          <div className="dashboard-summary-strip">
            <div>
              <UploadCloud size={18} />
              <span>Pending review</span>
              <strong>{documentSummary.pending_review_count}</strong>
            </div>
            <div>
              <FileText size={18} />
              <span>Missing required</span>
              <strong>{documentSummary.missing_required_count}</strong>
            </div>
            <div>
              <FileText size={18} />
              <span>Recent uploads</span>
              <strong>{documentSummary.recent_uploads.length}</strong>
            </div>
          </div>
          <div className="notification-list compact">
            {(documentSummary.pending_review || []).slice(0, 3).map((version) => (
              <article className="notification-row" key={version.id}>
                <span className="badge priority-warning">review</span>
                <div>
                  <strong>{version.document_type} v{version.version_no}</strong>
                  <p>{version.shipment_code || `Shipment #${version.shipment_id}`} · {version.file?.sanitized_filename || 'uploaded file'}</p>
                </div>
                <Link to={`/shipments/${version.shipment_id}`}>Open</Link>
              </article>
            ))}
            {!documentSummary.pending_review?.length && <p className="muted">No document versions pending review.</p>}
          </div>
        </section>
      )}

      {documentIntelligence !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Document Intelligence Review</h2>
            <Link to="/validation-issues">Open validation</Link>
          </div>
          <div className="dashboard-summary-strip">
            <div>
              <FileText size={18} />
              <span>Pending suggestions</span>
              <strong>{documentIntelligence.pending_suggestions}</strong>
            </div>
            <div>
              <AlertTriangle size={18} />
              <span>Critical mismatches</span>
              <strong>{documentIntelligence.critical_mismatches}</strong>
            </div>
            <div>
              <UploadCloud size={18} />
              <span>Low confidence</span>
              <strong>{documentIntelligence.low_confidence_extractions}</strong>
            </div>
          </div>
          <div className="notification-list compact">
            {(documentIntelligence.critical_items || []).slice(0, 3).map((item) => (
              <article className="notification-row" key={item.id}>
                <span className={`badge priority-${item.severity}`}>{item.severity}</span>
                <div>
                  <strong>{item.rule_key}</strong>
                  <p>{item.message}</p>
                </div>
                {item.shipment_id && <Link to={`/shipments/${item.shipment_id}`}>Open</Link>}
              </article>
            ))}
            {!documentIntelligence.critical_items?.length && <p className="muted">No critical document mismatches.</p>}
          </div>
        </section>
      )}

      {financeOverview !== null && (
        <>
          <div className="panel-header no-margin">
            <h2>Finance &amp; Credit Control</h2>
            <Link to="/finance">Open finance</Link>
          </div>
          <section className="metric-grid finance-grid">
            <article
              className={`metric-card ${
                Number(financeOverview.receivable_overdue) > 0 ? 'critical-card' : 'info-card'
              }`}
            >
              <WalletCards size={20} />
              <span>Receivable Overdue</span>
              <strong>
                {formatMoney(financeOverview.receivable_overdue, financeOverview.currency)}
              </strong>
            </article>
            <article
              className={`metric-card ${
                Number(financeOverview.payable_overdue) > 0 ? 'warning-card' : 'info-card'
              }`}
            >
              <DollarSign size={20} />
              <span>Payable Overdue</span>
              <strong>
                {formatMoney(financeOverview.payable_overdue, financeOverview.currency)}
              </strong>
            </article>
            <article
              className={`metric-card ${
                financeOverview.active_holds > 0 ? 'critical-card' : 'success-card'
              }`}
            >
              <AlertTriangle size={20} />
              <span>Active Credit Holds</span>
              <strong>{financeOverview.active_holds}</strong>
            </article>
            <article
              className={`metric-card ${
                financeOverview.open_risks > 0 ? 'warning-card' : 'success-card'
              }`}
            >
              <Bell size={20} />
              <span>Open Finance Risks</span>
              <strong>{financeOverview.open_risks}</strong>
            </article>
            <article
              className={`metric-card ${
                Number(financeOverview.unallocated_payments) > 0 ? 'info-card' : 'success-card'
              }`}
            >
              <DollarSign size={20} />
              <span>Unallocated Payments</span>
              <strong>
                {formatMoney(financeOverview.unallocated_payments, financeOverview.currency)}
              </strong>
            </article>
            <article
              className={`metric-card ${
                financeOverview.negative_margin_shipments > 0 ? 'critical-card' : 'success-card'
              }`}
            >
              <AlertTriangle size={20} />
              <span>Negative-Margin Shipments</span>
              <strong>{financeOverview.negative_margin_shipments}</strong>
            </article>
          </section>
        </>
      )}

      {exceptionSummary !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Manual Review Queue</h2>
            <Link to="/manual-review">Open review center</Link>
          </div>
          <div className="dashboard-summary-strip">
            <div>
              <AlertTriangle size={18} />
              <span>Open Exceptions</span>
              <strong>{exceptionSummary.total_open}</strong>
            </div>
            <div>
              <AlertTriangle size={18} />
              <span>Critical</span>
              <strong>{exceptionSummary.total_critical}</strong>
            </div>
            <div>
              <Clock size={18} />
              <span>Overdue</span>
              <strong>{exceptionSummary.total_overdue}</strong>
            </div>
            <div>
              <CheckCircle2 size={18} />
              <span>Assigned to Me</span>
              <strong>{exceptionSummary.total_assigned_to_me}</strong>
            </div>
          </div>
        </section>
      )}

      {approvalSummary !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Pending Approvals</h2>
            <Link to="/approvals">Open approval center</Link>
          </div>
          <div className="dashboard-summary-strip">
            <div>
              <FileText size={18} />
              <span>Pending</span>
              <strong>{approvalSummary.total_pending}</strong>
            </div>
            <div>
              <AlertTriangle size={18} />
              <span>High Risk</span>
              <strong>{approvalSummary.total_high_risk}</strong>
            </div>
            <div>
              <Clock size={18} />
              <span>Overdue</span>
              <strong>{approvalSummary.total_overdue}</strong>
            </div>
            <div>
              <CheckCircle2 size={18} />
              <span>Assigned to Me</span>
              <strong>{approvalSummary.total_assigned_to_me}</strong>
            </div>
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

      {containerRisk !== null && (
        <section className="panel">
          <div className="panel-header">
            <h2>Container Risk</h2>
            <Link to="/shipments">View shipments</Link>
          </div>
          {containerRisk.length === 0 ? (
            <p className="muted">No container demurrage or detention risk right now.</p>
          ) : (
            <div className="notification-list compact">
              {containerRisk.map((row) => (
                <article className="notification-row" key={`${row.container_id}`}>
                  <span className={`badge priority-${row.risk_level === 'running' ? 'critical' : row.risk_level}`}>
                    {row.risk_level}
                  </span>
                  <div>
                    <strong>{row.container_number}</strong>
                    <p>
                      {row.shipment_code} · {row.current_status} · demurrage {row.demurrage_status} · detention {row.detention_status}
                    </p>
                  </div>
                  <Link to={`/shipments/${row.shipment_id}`}>Open</Link>
                </article>
              ))}
            </div>
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
