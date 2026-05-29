import { AlertTriangle, CheckCircle2, Clock, CreditCard, FileText, Ship, Truck, ShieldCheck, Satellite, ArrowRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';

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

function OnboardingCard({ role }) {
  const guides = {
    ADMIN: { title: 'Admin Quick Start', steps: ['Add users and configure roles', 'Check Enterprise health', 'Monitor AI and governance', 'Review approvals and risks'] },
    STAFF: { title: 'Getting Started', steps: ['Create a shipment', 'Upload documents', 'Add container', 'Update customs / transport', 'Resolve any issues'] },
    VIEW_ONLY: { title: 'Manager Overview', steps: ['Open Management Dashboard', 'Check blocked shipments', 'Review pending approvals', 'Track risks and alerts'] },
  };
  const guide = guides[role] || guides.STAFF;
  return (
    <div className="onboarding-card">
      <h3>{guide.title}</h3>
      <ol>
        {guide.steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
    </div>
  );
}

function TodayPage() {
  const user = cachedUser();
  const [tasks, setTasks] = useState(null);
  const [docSummary, setDocSummary] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [exceptions, setExceptions] = useState(null);
  const [customsSummary, setCustomsSummary] = useState(null);
  const [transportJobs, setTransportJobs] = useState(null);
  const [financeHolds, setFinanceHolds] = useState(null);
  const [approvalSummary, setApprovalSummary] = useState(null);
  const [staleData, setStaleData] = useState(null);
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
    Promise.allSettled(fetches).finally(() => setLoading(false));
  }, []);

  const isWriter = user && ['ADMIN', 'STAFF'].includes(user.role);

  // Build items
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
        badge: 'alert', badgeClass: 'priority-warning', actionTo: '/', actionLabel: 'Dashboard',
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

  const hasAnyWork = taskItems.length > 0 || docItems.length > 0 || attentionItems.length > 0 ||
    customsItems.length > 0 || transportItems.length > 0 || holdItems.length > 0 ||
    approvalItems.length > 0 || issueItems.length > 0 || staleItems.length > 0;

  if (loading) {
    return (
      <div className="page-stack">
        <div className="page-header"><div><p className="eyebrow">Daily Work</p><h1>Today</h1></div></div>
        <p className="page-helper">Loading your work for today…</p>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Daily Work</p>
          <h1>Today</h1>
        </div>
        {isWriter && (
          <div className="quick-actions">
            <Link to="/shipments/new" className="primary-button">New Shipment</Link>
            <Link to="/shipments" className="secondary-button">All Shipments</Link>
          </div>
        )}
      </div>
      <p className="page-helper">What needs your attention today. Items auto-refresh from all modules.</p>

      {!hasAnyWork && (
        <div className="empty-state-guidance">
          <h3>No urgent work today</h3>
          <p>Create a shipment or check the Management Dashboard for overall operational status.</p>
          <div className="quick-actions">
            {isWriter && <Link to="/shipments/new" className="primary-button">Create Shipment</Link>}
            <Link to="/shipments" className="secondary-button">Open Shipments</Link>
            <Link to="/control-tower" className="secondary-button">Management Dashboard</Link>
          </div>
        </div>
      )}

      <div className="today-grid">
        <TodaySection title="My Open Tasks" icon={Clock} items={taskItems} linkTo="/tasks" linkLabel="All tasks" />
        <TodaySection title="Pending Documents" icon={FileText} items={docItems} countClass="warning" linkTo="/shipments" linkLabel="Shipments" />
        <TodaySection title="Shipments Needing Attention" icon={Ship} items={attentionItems} countClass="warning" linkTo="/" linkLabel="Dashboard" />
        <TodaySection title="Finance Holds" icon={CreditCard} items={holdItems} countClass="danger" linkTo="/finance" linkLabel="Finance" />
        <TodaySection title="Pending Approvals" icon={CheckCircle2} items={approvalItems} countClass="warning" linkTo="/approvals" linkLabel="Approvals" />
        <TodaySection title="Open Issues" icon={AlertTriangle} items={issueItems} countClass="danger" linkTo="/manual-review" linkLabel="All issues" />
        <TodaySection title="Customs Follow-ups" icon={ShieldCheck} items={customsItems} linkTo="/customs" linkLabel="Customs" />
        <TodaySection title="Transport Follow-ups" icon={Truck} items={transportItems} linkTo="/transport" linkLabel="Transport" />
        <TodaySection title="Stale Tracking / Delayed Updates" icon={Satellite} items={staleItems} linkTo="/tracking" linkLabel="Tracking" />
      </div>

      <OnboardingCard role={user?.role || 'STAFF'} />
    </div>
  );
}

export default TodayPage;
