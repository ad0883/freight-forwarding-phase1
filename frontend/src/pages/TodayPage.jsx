import { AlertTriangle, CheckCircle2, Clock, CreditCard, FileText, Ship, Truck, ShieldCheck, Satellite, Activity, Bot, Users, ShieldAlert, Settings, BarChart3 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { getRoleMode, getModeLabel, getQuickActions, getTodayWidgets, getOnboardingGuide } from '../utils/roleMode.js';

/* ============================================================
   S2 — Role-Mode-Based Today Page
   Shows different widgets, quick actions, and guidance per mode.
   ============================================================ */

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

function TodaySection({ title, icon: Icon, items, countClass, linkTo, linkLabel }) {
  if (!items || items.length === 0) return null;
  return (
    <section className="today-section">
      <div className="today-section-header">
        <h3>
          <Icon size={16} />
          {title}
          <span className={`today-count ${countClass || ''}`}>{items.length}</span>
        </h3>
        {linkTo && <Link to={linkTo} className="secondary-button">{linkLabel || 'View all'}</Link>}
      </div>
      {items.slice(0, 5).map((item, i) => (
        <div className="today-item" key={item.key || i}>
          {item.badge && <span className={`badge ${item.badgeClass || 'priority-info'}`}>{item.badge}</span>}
          <div className="today-item-info">
            <div className="today-item-title">{item.title}</div>
            {item.meta && <div className="today-item-meta">{item.meta}</div>}
          </div>
          {item.actionTo && <Link to={item.actionTo} className="secondary-button">{item.actionLabel || 'Open'}</Link>}
        </div>
      ))}
    </section>
  );
}

function OnboardingCard({ mode }) {
  const guide = getOnboardingGuide(mode);
  return (
    <div className="onboarding-card">
      <h3>{guide.title}</h3>
      <ol>
        {guide.steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
    </div>
  );
}

/* --- Finance-specific summary widget --- */
function FinanceSummaryWidget({ data }) {
  if (!data) return null;
  const currency = data.currency || 'INR';
  const fmt = (v) => v != null ? `${currency} ${Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `${currency} 0.00`;
  return (
    <section className="today-section">
      <div className="today-section-header">
        <h3><CreditCard size={16} /> Finance Overview</h3>
        <Link to="/finance" className="secondary-button">Open Finance</Link>
      </div>
      <div className="finance-today-metrics">
        <div className={`finance-today-metric ${data.receivable_overdue > 0 ? 'has-issue' : ''}`}>
          <span>Receivable Outstanding</span><strong>{fmt(data.receivable_total)}</strong>
        </div>
        <div className={`finance-today-metric ${data.receivable_overdue > 0 ? 'has-issue' : ''}`}>
          <span>Receivable Overdue</span><strong>{fmt(data.receivable_overdue)}</strong>
        </div>
        <div className="finance-today-metric">
          <span>Payable Outstanding</span><strong>{fmt(data.payable_total)}</strong>
        </div>
        <div className={`finance-today-metric ${data.payable_overdue > 0 ? 'has-issue' : ''}`}>
          <span>Payable Overdue</span><strong>{fmt(data.payable_overdue)}</strong>
        </div>
        <div className={`finance-today-metric ${data.active_holds > 0 ? 'has-issue' : ''}`}>
          <span>Active Credit Holds</span><strong>{data.active_holds ?? 0}</strong>
        </div>
        <div className="finance-today-metric">
          <span>Unallocated Payments</span><strong>{fmt(data.unallocated_payments)}</strong>
        </div>
      </div>
    </section>
  );
}

/* --- Admin-specific system widget --- */
function AdminSystemWidget({ userCount, securityEvents }) {
  return (
    <section className="today-section">
      <div className="today-section-header">
        <h3><Settings size={16} /> System Overview</h3>
        <Link to="/enterprise" className="secondary-button">Admin Settings</Link>
      </div>
      <div className="today-item">
        <span className="badge priority-info">users</span>
        <div className="today-item-info">
          <div className="today-item-title">{userCount ?? '—'} registered user(s)</div>
          <div className="today-item-meta">Manage roles and permissions</div>
        </div>
        <Link to="/users" className="secondary-button">Users</Link>
      </div>
      <div className="today-item">
        <span className="badge priority-info">ai</span>
        <div className="today-item-info">
          <div className="today-item-title">AI / Bot Governance</div>
          <div className="today-item-meta">Review agent rules and prompt safety</div>
        </div>
        <Link to="/bot-governance" className="secondary-button">AI Control</Link>
      </div>
      {securityEvents > 0 && (
        <div className="today-item">
          <span className="badge priority-warning">security</span>
          <div className="today-item-info">
            <div className="today-item-title">{securityEvents} recent security event(s)</div>
          </div>
          <Link to="/audit-logs" className="secondary-button">Audit Logs</Link>
        </div>
      )}
    </section>
  );
}

/* --- Management-specific risk overview --- */
function ManagementRiskWidget({ riskData, predictiveData }) {
  const items = [];
  if (riskData) {
    items.push({
      key: 'risk-score', title: `Overall risk score: ${riskData.risk_score ?? '—'}`,
      meta: `Risk level: ${riskData.risk_level || 'unknown'}`,
      badge: riskData.risk_level || 'info', badgeClass: riskData.risk_level === 'critical' ? 'priority-critical' : riskData.risk_level === 'high' ? 'priority-warning' : 'priority-info',
      actionTo: '/control-tower', actionLabel: 'Dashboard',
    });
  }
  if (predictiveData?.total_active > 0) {
    items.push({
      key: 'predictions', title: `${predictiveData.total_active} active risk prediction(s)`,
      meta: `${predictiveData.critical_count || 0} critical`,
      badge: 'risk', badgeClass: predictiveData.critical_count > 0 ? 'priority-critical' : 'priority-warning',
      actionTo: '/predictive', actionLabel: 'Risk Alerts',
    });
  }
  if (items.length === 0) return null;
  return <TodaySection title="Risk Overview" icon={BarChart3} items={items} linkTo="/control-tower" linkLabel="Management Dashboard" />;
}


function TodayPage() {
  const user = cachedUser();
  const mode = getRoleMode(user?.role);
  const quickActions = getQuickActions(mode);
  const widgetOrder = getTodayWidgets(mode);

  // All data states
  const [tasks, setTasks] = useState(null);
  const [docSummary, setDocSummary] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [exceptions, setExceptions] = useState(null);
  const [customsSummary, setCustomsSummary] = useState(null);
  const [transportJobs, setTransportJobs] = useState(null);
  const [financeHolds, setFinanceHolds] = useState(null);
  const [financeOverview, setFinanceOverview] = useState(null);
  const [approvalSummary, setApprovalSummary] = useState(null);
  const [staleData, setStaleData] = useState(null);
  const [riskHeatmap, setRiskHeatmap] = useState(null);
  const [predictiveSummary, setPredictiveSummary] = useState(null);
  const [userCount, setUserCount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetches = [
      api.get('/tasks', { params: { status: 'open', limit: 10 } }).then(r => setTasks(r.data)).catch(() => setTasks([])),
      api.get('/document-versions/dashboard-summary').then(r => setDocSummary(r.data)).catch(() => setDocSummary(null)),
      api.get('/shipments/dashboard').then(r => setDashboard(r.data)).catch(() => setDashboard(null)),
      api.get('/exceptions/summary').then(r => setExceptions(r.data)).catch(() => setExceptions(null)),
      api.get('/customs/summary').then(r => setCustomsSummary(r.data)).catch(() => setCustomsSummary(null)),
      api.get('/transport', { params: { status: 'open', limit: 10 } }).then(r => setTransportJobs(r.data)).catch(() => setTransportJobs([])),
      api.get('/finance/holds').then(r => setFinanceHolds(r.data)).catch(() => setFinanceHolds([])),
      api.get('/approvals/summary').then(r => setApprovalSummary(r.data)).catch(() => setApprovalSummary(null)),
      api.get('/control-tower/stale-data').then(r => setStaleData(r.data)).catch(() => setStaleData(null)),
    ];

    // Mode-specific additional fetches
    if (mode === 'finance' || mode === 'admin' || mode === 'management') {
      fetches.push(api.get('/finance/overview').then(r => setFinanceOverview(r.data)).catch(() => setFinanceOverview(null)));
    }
    if (mode === 'management' || mode === 'admin') {
      fetches.push(api.get('/control-tower/risk-heatmap').then(r => setRiskHeatmap(r.data)).catch(() => setRiskHeatmap(null)));
      fetches.push(api.get('/predictive/summary').then(r => setPredictiveSummary(r.data)).catch(() => setPredictiveSummary(null)));
    }
    if (mode === 'admin') {
      fetches.push(api.get('/users').then(r => setUserCount(Array.isArray(r.data) ? r.data.length : 0)).catch(() => setUserCount(null)));
    }

    Promise.allSettled(fetches).finally(() => setLoading(false));
  }, [mode]);

  // Build widget items (same logic as S1)
  const taskItems = (Array.isArray(tasks) ? tasks : []).map(t => ({
    key: t.id, title: t.title, meta: t.shipment_code ? `${t.shipment_code} · due ${t.due_date || 'no date'}` : t.due_date || '',
    badge: t.priority || 'info', badgeClass: `priority-${t.priority || 'info'}`,
    actionTo: t.shipment_id ? `/shipments/${t.shipment_id}` : '/tasks', actionLabel: 'Open',
  }));

  const docItems = [];
  if (docSummary) {
    if (docSummary.pending_review_count > 0) {
      (docSummary.pending_review || []).slice(0, 3).forEach(v => {
        docItems.push({
          key: `doc-${v.id}`, title: `${v.document_type} v${v.version_no} — pending review`,
          meta: v.shipment_code || `Shipment #${v.shipment_id}`, badge: 'review', badgeClass: 'priority-warning',
          actionTo: `/shipments/${v.shipment_id}`, actionLabel: 'Review',
        });
      });
    }
    if (docSummary.missing_required_count > 0) {
      docItems.push({
        key: 'missing-docs', title: `${docSummary.missing_required_count} missing required document(s)`,
        meta: 'Upload invoices, BLs, or packing lists', badge: 'missing', badgeClass: 'priority-critical',
        actionTo: '/shipments', actionLabel: 'Open Shipments',
      });
    }
  }

  const attentionItems = [];
  if (dashboard) {
    if (dashboard.alerts_today > 0) {
      attentionItems.push({
        key: 'alerts', title: `${dashboard.alerts_today} alert(s) today`,
        meta: `${dashboard.live_shipments} live shipments · ${dashboard.pending_tasks} pending tasks`,
        badge: 'alert', badgeClass: 'priority-warning', actionTo: '/dashboard', actionLabel: 'Dashboard',
      });
    }
  }

  const customsItems = [];
  if (customsSummary) {
    const pending = customsSummary.pending_clearance || customsSummary.open_cases || 0;
    const queries = customsSummary.open_queries || 0;
    if (pending > 0) customsItems.push({ key: 'customs-pending', title: `${pending} customs case(s) pending clearance`, badge: 'pending', badgeClass: 'priority-warning', actionTo: '/customs', actionLabel: 'Open Customs' });
    if (queries > 0) customsItems.push({ key: 'customs-queries', title: `${queries} open customs quer${queries === 1 ? 'y' : 'ies'}`, badge: 'query', badgeClass: 'priority-info', actionTo: '/customs', actionLabel: 'Open Customs' });
  }

  const transportItems = (Array.isArray(transportJobs) ? transportJobs : []).filter(j => j.status !== 'completed' && j.status !== 'cancelled').slice(0, 5).map(j => ({
    key: j.id, title: j.title || `Transport job #${j.id}`,
    meta: j.shipment_code || (j.shipment_id ? `Shipment #${j.shipment_id}` : ''),
    badge: j.status || 'open', badgeClass: `priority-${j.status === 'delayed' ? 'critical' : 'info'}`,
    actionTo: '/transport', actionLabel: 'Open Transport',
  }));

  const holdItems = (Array.isArray(financeHolds) ? financeHolds : []).filter(h => h.status === 'active' || !h.resolved_at).slice(0, 5).map(h => ({
    key: h.id, title: h.reason || `Credit hold #${h.id}`,
    meta: h.party_name || '', badge: 'hold', badgeClass: 'priority-critical',
    actionTo: '/finance', actionLabel: 'Check Finance',
  }));

  const approvalItems = [];
  if (approvalSummary && approvalSummary.total_pending > 0) {
    approvalItems.push({
      key: 'approvals', title: `${approvalSummary.total_pending} pending approval(s)`,
      meta: approvalSummary.total_high_risk > 0 ? `${approvalSummary.total_high_risk} high-risk` : 'Review and approve or reject',
      badge: approvalSummary.total_high_risk > 0 ? 'high-risk' : 'pending', badgeClass: approvalSummary.total_high_risk > 0 ? 'priority-critical' : 'priority-warning',
      actionTo: '/approvals', actionLabel: 'Review',
    });
  }

  const issueItems = [];
  if (exceptions) {
    if (exceptions.total_open > 0) {
      issueItems.push({
        key: 'issues-open', title: `${exceptions.total_open} open issue(s)`,
        meta: exceptions.total_critical > 0 ? `${exceptions.total_critical} critical` : `${exceptions.total_overdue || 0} overdue`,
        badge: exceptions.total_critical > 0 ? 'critical' : 'open', badgeClass: exceptions.total_critical > 0 ? 'priority-critical' : 'priority-warning',
        actionTo: '/manual-review', actionLabel: 'Review Issues',
      });
    }
  }

  const staleItems = [];
  if (staleData && Array.isArray(staleData) && staleData.length > 0) {
    staleData.slice(0, 3).forEach(item => {
      staleItems.push({
        key: `stale-${item.shipment_id || item.id}`, title: item.shipment_code || `Tracking stale for shipment #${item.shipment_id}`,
        meta: item.reason || 'No tracking update received recently',
        badge: 'stale', badgeClass: 'priority-warning', actionTo: '/tracking', actionLabel: 'View Tracking',
      });
    });
  }

  // Widget map — lookup for ordered rendering
  const widgetMap = {
    tasks: <TodaySection key="tasks" title="My Open Tasks" icon={Clock} items={taskItems} linkTo="/tasks" linkLabel="All tasks" />,
    documents: <TodaySection key="documents" title="Pending Documents" icon={FileText} items={docItems} countClass="warning" linkTo="/shipments" linkLabel="Shipments" />,
    attention: <TodaySection key="attention" title="Shipments Needing Attention" icon={Ship} items={attentionItems} countClass="warning" linkTo="/dashboard" linkLabel="Dashboard" />,
    financeHolds: mode === 'finance'
      ? <FinanceSummaryWidget key="financeOverview" data={financeOverview} />
      : <TodaySection key="financeHolds" title="Finance Holds" icon={CreditCard} items={holdItems} countClass="danger" linkTo="/finance" linkLabel="Finance" />,
    approvals: <TodaySection key="approvals" title="Pending Approvals" icon={CheckCircle2} items={approvalItems} countClass="warning" linkTo="/approvals" linkLabel="Approvals" />,
    issues: <TodaySection key="issues" title="Open Issues" icon={AlertTriangle} items={issueItems} countClass="danger" linkTo="/manual-review" linkLabel="All issues" />,
    customs: <TodaySection key="customs" title="Customs Follow-ups" icon={ShieldCheck} items={customsItems} linkTo="/customs" linkLabel="Customs" />,
    transport: <TodaySection key="transport" title="Transport Follow-ups" icon={Truck} items={transportItems} linkTo="/transport" linkLabel="Transport" />,
    staleTracking: <TodaySection key="staleTracking" title="Stale Tracking / Delayed Updates" icon={Satellite} items={staleItems} linkTo="/tracking" linkLabel="Tracking" />,
  };

  // Mode-specific helper text
  const modeHelpers = {
    operations: 'Your shipments, documents, customs, and transport follow-ups.',
    finance: 'Receivables, payables, credit holds, and finance approvals.',
    management: 'Blocked shipments, risks, approvals, and team performance.',
    admin: 'System health, users, governance, and all operational modules.',
    readonly: 'Read-only view. Summaries and reports across operations.',
  };

  if (loading) {
    return (
      <div className="page-stack">
        <div className="page-header"><div><p className="eyebrow">{getModeLabel(mode)}</p><h1>Today</h1></div></div>
        <p className="page-helper">Loading your work for today…</p>
      </div>
    );
  }

  const hasAnyWork = widgetOrder.some(w => {
    if (w === 'tasks') return taskItems.length > 0;
    if (w === 'documents') return docItems.length > 0;
    if (w === 'attention') return attentionItems.length > 0;
    if (w === 'financeHolds') return mode === 'finance' ? !!financeOverview : holdItems.length > 0;
    if (w === 'approvals') return approvalItems.length > 0;
    if (w === 'issues') return issueItems.length > 0;
    if (w === 'customs') return customsItems.length > 0;
    if (w === 'transport') return transportItems.length > 0;
    if (w === 'staleTracking') return staleItems.length > 0;
    return false;
  });

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">{getModeLabel(mode)}</p>
          <h1>Today</h1>
        </div>
        <div className="quick-actions">
          {quickActions.map(a => (
            <Link key={a.to} to={a.to} className={a.primary ? 'primary-button' : 'secondary-button'}>{a.label}</Link>
          ))}
        </div>
      </div>
      <p className="page-helper">{modeHelpers[mode] || modeHelpers.operations}</p>

      {!hasAnyWork && (
        <div className="empty-state-guidance">
          <h3>No urgent work today</h3>
          <p>{mode === 'finance' ? 'No pending finance items. Check the Finance module for detailed reports.' :
             mode === 'management' ? 'No blocked items or pending approvals. Check the Management Dashboard for overview.' :
             mode === 'admin' ? 'System running normally. Check Admin Settings for configuration.' :
             mode === 'readonly' ? 'No items needing review. Check Management Dashboard or Risk Alerts.' :
             'Create a shipment or check the Management Dashboard for overall operational status.'}</p>
          <div className="quick-actions">
            {quickActions.slice(0, 3).map(a => (
              <Link key={a.to} to={a.to} className={a.primary ? 'primary-button' : 'secondary-button'}>{a.label}</Link>
            ))}
          </div>
        </div>
      )}

      <div className="today-grid">
        {/* Mode-ordered widgets */}
        {widgetOrder.map(w => widgetMap[w] || null)}

        {/* Mode-specific special widgets */}
        {(mode === 'management') && <ManagementRiskWidget riskData={riskHeatmap} predictiveData={predictiveSummary} />}
        {(mode === 'admin') && <AdminSystemWidget userCount={userCount} />}
      </div>

      <OnboardingCard mode={mode} />
    </div>
  );
}

export default TodayPage;
