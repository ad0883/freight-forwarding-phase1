import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Eye,
  Filter,
  Link2,
  MessageSquare,
  RefreshCw,
  Send,
  Shield,
  UserCheck,
  XCircle,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

const SEVERITY_COLORS = {
  critical: 'var(--color-danger)',
  high: '#ea580c',
  medium: 'var(--color-warning)',
  low: 'var(--color-primary)',
  info: 'var(--color-text-muted)',
};

const SEVERITY_BG = {
  critical: 'var(--color-danger-light)',
  high: '#fff7ed',
  medium: 'var(--color-warning-light)',
  low: 'var(--color-primary-light)',
  info: '#f8fafc',
};

const PRIORITY_LABELS = { p0: 'P0', p1: 'P1', p2: 'P2', p3: 'P3', p4: 'P4' };
const PRIORITY_CLASS = { p0: 'priority-critical', p1: 'priority-critical', p2: 'priority-warning', p3: 'priority-info', p4: 'priority-none' };

const STATUS_LABELS = {
  open: 'Open', acknowledged: 'Acknowledged', in_review: 'In Review',
  waiting_on_party: 'Waiting on Party', waiting_on_document: 'Waiting on Doc',
  waiting_on_finance: 'Waiting on Finance', waiting_on_customer: 'Waiting on Customer',
  waiting_on_vendor: 'Waiting on Vendor', escalated: 'Escalated',
  resolved: 'Resolved', dismissed: 'Dismissed', reopened: 'Reopened',
};

const STATUS_CLASS = {
  open: 'status-active', acknowledged: 'priority-info', in_review: 'priority-info',
  escalated: 'priority-critical', resolved: 'status-completed', dismissed: 'status-archived',
  reopened: 'priority-warning',
};

const CATEGORY_OPTIONS = [
  'workflow', 'document', 'container', 'finance', 'gmail', 'ai',
  'validation', 'notification', 'sla', 'party', 'shipment', 'system', 'other',
];

const CATEGORY_ICONS = {
  workflow: '⚙️', document: '📄', container: '📦', finance: '💰',
  gmail: '✉️', ai: '🤖', validation: '⚠️', notification: '🔔',
  sla: '⏱️', party: '👥', shipment: '🚢', system: '🖥️', other: '📋',
};

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function ManualReviewPage() {
  const [summary, setSummary] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedCase, setSelectedCase] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [comments, setComments] = useState([]);
  const [links, setLinks] = useState([]);
  const [history, setHistory] = useState([]);
  const [filters, setFilters] = useState({ category: '', severity: '', priority: '', status: '' });
  const [showFilters, setShowFilters] = useState(false);
  const [actionLoading, setActionLoading] = useState('');
  const [commentText, setCommentText] = useState('');
  const [resolveNotes, setResolveNotes] = useState('');
  const [dismissReason, setDismissReason] = useState('');
  const [escalateReason, setEscalateReason] = useState('');
  const [showResolve, setShowResolve] = useState(false);
  const [showDismiss, setShowDismiss] = useState(false);
  const [showEscalate, setShowEscalate] = useState(false);
  const [tab, setTab] = useState('all');
  const [detectionResult, setDetectionResult] = useState(null);
  const [detailTab, setDetailTab] = useState('overview');

  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; }
  })();
  const isAdmin = currentUser?.role === 'ADMIN';
  const canMutate = ['ADMIN', 'STAFF'].includes(currentUser?.role);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const [summaryRes, listRes] = await Promise.all([
        api.get('/exceptions/summary'),
        api.get('/exceptions', { params: buildParams() }),
      ]);
      setSummary(summaryRes.data);
      setExceptions(listRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load exceptions');
    } finally {
      setLoading(false);
    }
  }

  function buildParams() {
    const params = { limit: 100 };
    if (filters.category) params.category = filters.category;
    if (filters.severity) params.severity = filters.severity;
    if (filters.priority) params.priority = filters.priority;
    if (filters.status) params.status = filters.status;
    if (tab === 'my-queue') params.assigned_to_user_id = currentUser?.id;
    if (tab === 'overdue') params.overdue = true;
    if (tab === 'critical') params.severity = 'critical';
    if (tab === 'resolved') params.status = 'resolved';
    if (tab === 'dismissed') params.status = 'dismissed';
    return params;
  }

  useEffect(() => { loadData(); }, [tab, filters]);

  async function openDetail(caseItem) {
    setSelectedCase(caseItem);
    setDetailLoading(true);
    setDetailTab('overview');
    setShowResolve(false);
    setShowDismiss(false);
    setShowEscalate(false);
    try {
      const [commentsRes, linksRes, historyRes] = await Promise.all([
        api.get(`/exceptions/${caseItem.id}/comments`),
        api.get(`/exceptions/${caseItem.id}/links`),
        api.get(`/exceptions/${caseItem.id}/history`),
      ]);
      setComments(commentsRes.data);
      setLinks(linksRes.data);
      setHistory(historyRes.data);
    } catch { /* graceful */ }
    setDetailLoading(false);
  }

  async function runDetection() {
    setActionLoading('detection');
    try {
      const res = await api.post('/exceptions/run-detection');
      setDetectionResult(res.data.results);
      loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed');
    }
    setActionLoading('');
  }

  async function doAction(action, body = {}) {
    if (!selectedCase) return;
    setActionLoading(action);
    try {
      const res = await api.post(`/exceptions/${selectedCase.id}/${action}`, body);
      setSelectedCase(res.data);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || `Action ${action} failed`);
    }
    setActionLoading('');
  }

  async function addComment() {
    if (!commentText.trim()) return;
    setActionLoading('comment');
    try {
      await api.post(`/exceptions/${selectedCase.id}/comments`, { comment_text: commentText, is_internal: true });
      setCommentText('');
      const res = await api.get(`/exceptions/${selectedCase.id}/comments`);
      setComments(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add comment');
    }
    setActionLoading('');
  }

  if (error && !exceptions.length) return <ErrorState message={error} />;

  return (
    <div className="page-stack">
      {/* Header */}
      <div className="page-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Manual Review Center</h1>
        </div>
        <div className="header-actions">
          {canMutate && (
            <button className="primary-button" onClick={runDetection} disabled={actionLoading === 'detection'}>
              <RefreshCw size={16} /> {actionLoading === 'detection' ? 'Scanning...' : 'Run Detection'}
            </button>
          )}
          <button className="secondary-button" onClick={() => setShowFilters(!showFilters)}>
            <Filter size={16} /> Filters {showFilters ? '▾' : '▸'}
          </button>
        </div>
      </div>

      {/* Detection result banner */}
      {detectionResult && (
        <div className="state-box" style={{ borderColor: 'var(--color-success-border)', background: 'var(--color-success-light)' }}>
          <CheckCircle2 size={20} style={{ color: 'var(--color-success)' }} />
          <div>
            <strong>Detection complete</strong>
            <p>{Object.entries(detectionResult).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' · ')}</p>
          </div>
          <button className="icon-button" onClick={() => setDetectionResult(null)} style={{ marginLeft: 'auto' }}>✕</button>
        </div>
      )}

      {/* Summary metric cards */}
      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(140px, 1fr))' }}>
          <article className="metric-card">
            <Shield size={20} />
            <span>Open Exceptions</span>
            <strong>{summary.total_open}</strong>
          </article>
          <article className="metric-card critical-card">
            <AlertTriangle size={20} />
            <span>Critical</span>
            <strong>{summary.total_critical}</strong>
          </article>
          <article className="metric-card info-card">
            <UserCheck size={20} />
            <span>Assigned to Me</span>
            <strong>{summary.total_assigned_to_me}</strong>
          </article>
          <article className="metric-card warning-card">
            <Clock size={20} />
            <span>Overdue</span>
            <strong>{summary.total_overdue}</strong>
          </article>
        </div>
      )}

      {/* Filters panel */}
      {showFilters && (
        <div className="panel" style={{ padding: '0.85rem 1rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <select value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })} style={{ width: 'auto', minWidth: '140px' }}>
              <option value="">All Categories</option>
              {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{CATEGORY_ICONS[c] || ''} {c}</option>)}
            </select>
            <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })} style={{ width: 'auto', minWidth: '130px' }}>
              <option value="">All Severities</option>
              <option value="critical">🔴 Critical</option>
              <option value="high">🟠 High</option>
              <option value="medium">🟡 Medium</option>
              <option value="low">🔵 Low</option>
              <option value="info">⚪ Info</option>
            </select>
            <select value={filters.priority} onChange={(e) => setFilters({ ...filters, priority: e.target.value })} style={{ width: 'auto', minWidth: '120px' }}>
              <option value="">All Priorities</option>
              <option value="p0">P0 — Immediate</option>
              <option value="p1">P1 — Urgent</option>
              <option value="p2">P2 — High</option>
              <option value="p3">P3 — Normal</option>
              <option value="p4">P4 — Low</option>
            </select>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} style={{ width: 'auto', minWidth: '140px' }}>
              <option value="">All Statuses</option>
              {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <button className="secondary-button" onClick={() => setFilters({ category: '', severity: '', priority: '', status: '' })} style={{ marginLeft: 'auto' }}>
              Clear All
            </button>
          </div>
        </div>
      )}

      {/* Tab navigation */}
      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)', paddingBottom: '0' }}>
        {[
          { key: 'all', label: 'All Open', count: summary?.total_open },
          { key: 'my-queue', label: 'My Queue', count: summary?.total_assigned_to_me },
          { key: 'critical', label: 'Critical', count: summary?.total_critical },
          { key: 'overdue', label: 'Overdue', count: summary?.total_overdue },
          { key: 'resolved', label: 'Resolved' },
          { key: 'dismissed', label: 'Dismissed' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: '0.6rem 1rem',
              border: 'none',
              borderBottom: tab === t.key ? '2px solid var(--color-primary)' : '2px solid transparent',
              marginBottom: '-2px',
              background: 'none',
              color: tab === t.key ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: tab === t.key ? 700 : 500,
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 150ms ease',
            }}
          >
            {t.label}
            {t.count != null && t.count > 0 && (
              <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem', background: tab === t.key ? 'var(--color-primary-light)' : '#f1f5f9', padding: '0.1rem 0.45rem', borderRadius: '999px', fontWeight: 700 }}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Main content area */}
      {loading ? <LoadingState /> : (
        <div style={{ display: 'grid', gridTemplateColumns: selectedCase ? '1fr 420px' : '1fr', gap: '1rem', alignItems: 'start' }}>
          {/* Exception list */}
          <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
            {exceptions.length === 0 ? (
              <div className="empty-state state-box" style={{ minHeight: '200px', border: 'none' }}>
                <Shield size={32} />
                <div>
                  <strong>No exceptions found</strong>
                  <p>All clear for this view, or try adjusting your filters.</p>
                </div>
              </div>
            ) : (
              <div className="table-wrap" style={{ maxHeight: selectedCase ? '70vh' : 'none', overflow: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: '32px' }}></th>
                      <th>Exception</th>
                      <th>Severity</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Assigned</th>
                      <th>Age</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exceptions.map((exc) => (
                      <tr
                        key={exc.id}
                        onClick={() => openDetail(exc)}
                        className="clickable-row"
                        style={{ background: selectedCase?.id === exc.id ? 'var(--color-primary-light)' : undefined }}
                      >
                        <td style={{ textAlign: 'center', fontSize: '1.1rem' }}>
                          {CATEGORY_ICONS[exc.category] || '📋'}
                        </td>
                        <td>
                          <div style={{ display: 'grid', gap: '0.15rem' }}>
                            <strong style={{ fontSize: '0.85rem', lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '320px' }}>
                              {exc.title}
                            </strong>
                            <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                              {exc.case_number} · {exc.category}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="badge" style={{ color: SEVERITY_COLORS[exc.severity], background: SEVERITY_BG[exc.severity] }}>
                            {exc.severity}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${PRIORITY_CLASS[exc.priority] || 'priority-none'}`}>
                            {PRIORITY_LABELS[exc.priority] || exc.priority}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${STATUS_CLASS[exc.status] || ''}`}>
                            {STATUS_LABELS[exc.status] || exc.status}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>
                          {exc.assigned_to_name || <span style={{ color: 'var(--color-text-faint)' }}>Unassigned</span>}
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                          {timeAgo(exc.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedCase && (
            <div className="panel" style={{ padding: 0, position: 'sticky', top: '1rem', maxHeight: 'calc(100vh - 3rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {/* Detail header */}
              <div style={{ padding: '1rem 1.15rem', borderBottom: '1px solid var(--color-border)', background: SEVERITY_BG[selectedCase.severity] || '#f8fafc' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                      <span style={{ fontSize: '1.2rem' }}>{CATEGORY_ICONS[selectedCase.category] || '📋'}</span>
                      <span className={`badge ${PRIORITY_CLASS[selectedCase.priority] || ''}`}>{PRIORITY_LABELS[selectedCase.priority]}</span>
                      <span className="badge" style={{ color: SEVERITY_COLORS[selectedCase.severity], background: 'rgba(255,255,255,0.7)' }}>{selectedCase.severity}</span>
                    </div>
                    <h2 style={{ fontSize: '1rem', fontWeight: 700, lineHeight: 1.3, margin: 0 }}>{selectedCase.title}</h2>
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                      {selectedCase.case_number} · {STATUS_LABELS[selectedCase.status] || selectedCase.status}
                    </p>
                  </div>
                  <button onClick={() => setSelectedCase(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '1.2rem', color: 'var(--color-text-muted)', padding: '0.25rem' }}>✕</button>
                </div>
              </div>

              {/* Detail tabs */}
              <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border)', padding: '0 1rem' }}>
                {['overview', 'activity', 'links'].map((dt) => (
                  <button
                    key={dt}
                    onClick={() => setDetailTab(dt)}
                    style={{
                      padding: '0.55rem 0.75rem', border: 'none', background: 'none', cursor: 'pointer',
                      fontSize: '0.78rem', fontWeight: detailTab === dt ? 700 : 500, textTransform: 'capitalize',
                      color: detailTab === dt ? 'var(--color-primary)' : 'var(--color-text-muted)',
                      borderBottom: detailTab === dt ? '2px solid var(--color-primary)' : '2px solid transparent',
                      marginBottom: '-1px',
                    }}
                  >
                    {dt}{dt === 'activity' && comments.length > 0 ? ` (${comments.length + history.length})` : ''}{dt === 'links' && links.length > 0 ? ` (${links.length})` : ''}
                  </button>
                ))}
              </div>

              {/* Detail body */}
              <div style={{ flex: 1, overflow: 'auto', padding: '1rem 1.15rem' }}>
                {detailLoading ? <LoadingState /> : (
                  <>
                    {detailTab === 'overview' && <DetailOverview exc={selectedCase} />}
                    {detailTab === 'activity' && <DetailActivity history={history} comments={comments} />}
                    {detailTab === 'links' && <DetailLinks links={links} />}
                  </>
                )}
              </div>

              {/* Action bar */}
              {canMutate && (
                <div style={{ borderTop: '1px solid var(--color-border)', padding: '0.75rem 1.15rem', background: '#f8fafc' }}>
                  {/* Quick actions */}
                  {!showResolve && !showDismiss && !showEscalate && (
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      {selectedCase.status === 'open' && (
                        <button className="secondary-button" onClick={() => doAction('acknowledge')} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>
                          <Eye size={13} /> Acknowledge
                        </button>
                      )}
                      <button className="secondary-button" onClick={() => setShowResolve(true)} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>
                        <CheckCircle2 size={13} /> Resolve
                      </button>
                      {isAdmin && (
                        <>
                          <button className="secondary-button" onClick={() => setShowEscalate(true)} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>
                            <ArrowUpRight size={13} /> Escalate
                          </button>
                          <button className="secondary-button" onClick={() => setShowDismiss(true)} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>
                            <XCircle size={13} /> Dismiss
                          </button>
                        </>
                      )}
                      {['resolved', 'dismissed'].includes(selectedCase.status) && (
                        <button className="secondary-button" onClick={() => doAction('reopen', { reason: 'Reopened from UI' })} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>
                          <RefreshCw size={13} /> Reopen
                        </button>
                      )}
                    </div>
                  )}

                  {/* Resolve form */}
                  {showResolve && (
                    <div style={{ display: 'grid', gap: '0.5rem' }}>
                      <textarea placeholder="How was this resolved?" value={resolveNotes} onChange={(e) => setResolveNotes(e.target.value)} rows={2} style={{ fontSize: '0.84rem' }} />
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button className="primary-button" onClick={() => { doAction('resolve', { resolution_notes: resolveNotes }); setShowResolve(false); setResolveNotes(''); }} disabled={!resolveNotes.trim()} style={{ fontSize: '0.78rem' }}>
                          <CheckCircle2 size={13} /> Confirm Resolve
                        </button>
                        <button className="secondary-button" onClick={() => setShowResolve(false)} style={{ fontSize: '0.78rem' }}>Cancel</button>
                      </div>
                    </div>
                  )}

                  {/* Dismiss form */}
                  {showDismiss && (
                    <div style={{ display: 'grid', gap: '0.5rem' }}>
                      <textarea placeholder="Why is this being dismissed?" value={dismissReason} onChange={(e) => setDismissReason(e.target.value)} rows={2} style={{ fontSize: '0.84rem' }} />
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button className="primary-button" onClick={() => { doAction('dismiss', { dismissal_reason: dismissReason }); setShowDismiss(false); setDismissReason(''); }} disabled={!dismissReason.trim()} style={{ fontSize: '0.78rem', background: 'var(--color-danger)' }}>
                          <XCircle size={13} /> Confirm Dismiss
                        </button>
                        <button className="secondary-button" onClick={() => setShowDismiss(false)} style={{ fontSize: '0.78rem' }}>Cancel</button>
                      </div>
                    </div>
                  )}

                  {/* Escalate form */}
                  {showEscalate && (
                    <div style={{ display: 'grid', gap: '0.5rem' }}>
                      <textarea placeholder="Reason for escalation..." value={escalateReason} onChange={(e) => setEscalateReason(e.target.value)} rows={2} style={{ fontSize: '0.84rem' }} />
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button className="primary-button" onClick={() => { doAction('escalate', { reason: escalateReason, severity: 'critical', priority: 'p0' }); setShowEscalate(false); setEscalateReason(''); }} disabled={!escalateReason.trim()} style={{ fontSize: '0.78rem', background: '#ea580c' }}>
                          <ArrowUpRight size={13} /> Confirm Escalate
                        </button>
                        <button className="secondary-button" onClick={() => setShowEscalate(false)} style={{ fontSize: '0.78rem' }}>Cancel</button>
                      </div>
                    </div>
                  )}

                  {/* Comment input */}
                  {!showResolve && !showDismiss && !showEscalate && (
                    <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.6rem' }}>
                      <input
                        type="text" placeholder="Add a comment..." value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addComment()}
                        style={{ flex: 1, fontSize: '0.82rem', minHeight: '32px', padding: '0.4rem 0.65rem' }}
                      />
                      <button className="primary-button" onClick={addComment} disabled={!commentText.trim() || actionLoading === 'comment'} style={{ minHeight: '32px', padding: '0.4rem 0.6rem' }}>
                        <Send size={13} />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* --- Sub-components --- */

function DetailOverview({ exc }) {
  const isOverdue = exc.due_at && new Date(exc.due_at) < new Date() && !['resolved', 'dismissed'].includes(exc.status);

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      {/* Info grid */}
      <div className="info-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
        <div className="info-item">
          <span>Category</span>
          <strong>{CATEGORY_ICONS[exc.category]} {exc.category}</strong>
        </div>
        <div className="info-item">
          <span>Source</span>
          <strong>{exc.source.replace(/_/g, ' ')}</strong>
        </div>
        <div className="info-item">
          <span>Risk Score</span>
          <strong>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              {exc.risk_score}
              <span style={{ display: 'inline-block', width: '50px', height: '6px', borderRadius: '3px', background: 'var(--color-border)' }}>
                <span style={{ display: 'block', width: `${exc.risk_score}%`, height: '100%', borderRadius: '3px', background: exc.risk_score >= 70 ? 'var(--color-danger)' : exc.risk_score >= 40 ? 'var(--color-warning)' : 'var(--color-success)' }} />
              </span>
            </span>
          </strong>
        </div>
        <div className="info-item" style={isOverdue ? { borderColor: 'var(--color-danger-border)', background: 'var(--color-danger-light)' } : {}}>
          <span>Due</span>
          <strong style={isOverdue ? { color: 'var(--color-danger)' } : {}}>
            {exc.due_at ? new Date(exc.due_at).toLocaleString() : '—'}
            {isOverdue && ' ⚠️ OVERDUE'}
          </strong>
        </div>
        <div className="info-item">
          <span>Assigned To</span>
          <strong>{exc.assigned_to_name || 'Unassigned'}{exc.assigned_to_role ? ` (${exc.assigned_to_role})` : ''}</strong>
        </div>
        <div className="info-item">
          <span>Created By</span>
          <strong>{exc.created_by_name || 'System'}</strong>
        </div>
        <div className="info-item">
          <span>First Seen</span>
          <strong>{new Date(exc.first_seen_at).toLocaleString()}</strong>
        </div>
        <div className="info-item">
          <span>Last Seen</span>
          <strong>{new Date(exc.last_seen_at).toLocaleString()}</strong>
        </div>
      </div>

      {/* Description */}
      {exc.description && (
        <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', fontSize: '0.85rem', lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>
          {exc.description}
        </div>
      )}

      {/* Shipment link */}
      {exc.shipment_id && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 0.75rem', background: 'var(--color-primary-light)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-primary-border)' }}>
          <Link2 size={14} style={{ color: 'var(--color-primary)' }} />
          <span style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>Linked shipment:</span>
          <Link to={`/shipments/${exc.shipment_id}`} style={{ fontSize: '0.82rem', fontWeight: 600 }}>
            Shipment #{exc.shipment_id} →
          </Link>
        </div>
      )}

      {/* Resolution info */}
      {exc.resolved_at && (
        <div style={{ padding: '0.65rem 0.75rem', background: 'var(--color-success-light)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-success-border)', fontSize: '0.82rem' }}>
          <strong style={{ color: 'var(--color-success)' }}>Resolved</strong> by {exc.resolved_by_name || 'Unknown'} on {new Date(exc.resolved_at).toLocaleString()}
          {exc.resolution_notes && <p style={{ marginTop: '0.3rem', color: 'var(--color-text-secondary)' }}>{exc.resolution_notes}</p>}
        </div>
      )}

      {/* Dismissal info */}
      {exc.dismissed_at && (
        <div style={{ padding: '0.65rem 0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', fontSize: '0.82rem' }}>
          <strong>Dismissed</strong> by {exc.dismissed_by_name || 'Unknown'} on {new Date(exc.dismissed_at).toLocaleString()}
          {exc.dismissal_reason && <p style={{ marginTop: '0.3rem', color: 'var(--color-text-secondary)' }}>{exc.dismissal_reason}</p>}
        </div>
      )}
    </div>
  );
}

function DetailActivity({ history, comments }) {
  // Merge history and comments into a timeline
  const timeline = [
    ...history.map((h) => ({ type: 'status', time: h.created_at, data: h })),
    ...comments.map((c) => ({ type: 'comment', time: c.created_at, data: c })),
  ].sort((a, b) => new Date(a.time) - new Date(b.time));

  if (timeline.length === 0) {
    return <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '2rem 0' }}>No activity yet.</p>;
  }

  return (
    <div style={{ display: 'grid', gap: '0.5rem' }}>
      {timeline.map((item, idx) => (
        <div key={`${item.type}-${idx}`} style={{ display: 'flex', gap: '0.6rem', padding: '0.5rem 0', borderBottom: idx < timeline.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
          <div style={{ width: '24px', height: '24px', borderRadius: '50%', display: 'grid', placeItems: 'center', flexShrink: 0, background: item.type === 'comment' ? 'var(--color-primary-light)' : '#f1f5f9' }}>
            {item.type === 'comment' ? <MessageSquare size={12} style={{ color: 'var(--color-primary)' }} /> : <Clock size={12} style={{ color: 'var(--color-text-muted)' }} />}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            {item.type === 'status' && (
              <>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                  <strong>{item.data.changed_by_name || 'System'}</strong> changed status
                  {item.data.old_status && <> from <span className="badge" style={{ fontSize: '0.68rem' }}>{item.data.old_status}</span></>}
                  {' '}to <span className="badge" style={{ fontSize: '0.68rem' }}>{item.data.new_status}</span>
                </div>
                {item.data.reason && <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '0.15rem' }}>{item.data.reason}</p>}
              </>
            )}
            {item.type === 'comment' && (
              <>
                <div style={{ fontSize: '0.8rem' }}>
                  <strong>{item.data.author_name || 'System'}</strong>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginTop: '0.15rem', lineHeight: 1.4 }}>{item.data.comment_text}</p>
              </>
            )}
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-faint)', marginTop: '0.2rem', display: 'block' }}>
              {new Date(item.time).toLocaleString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function DetailLinks({ links }) {
  if (links.length === 0) {
    return <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '2rem 0' }}>No linked entities.</p>;
  }

  const grouped = {};
  links.forEach((link) => {
    const key = link.relationship_type;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(link);
  });

  return (
    <div style={{ display: 'grid', gap: '0.85rem' }}>
      {Object.entries(grouped).map(([rel, items]) => (
        <div key={rel}>
          <h4 style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>
            {rel.replace(/_/g, ' ')}
          </h4>
          <div style={{ display: 'grid', gap: '0.3rem' }}>
            {items.map((link) => (
              <div key={link.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.45rem 0.65rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', background: '#f8fafc' }}>
                <Link2 size={13} style={{ color: 'var(--color-text-faint)', flexShrink: 0 }} />
                <span className="badge" style={{ fontSize: '0.68rem' }}>{link.linked_type.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>#{link.linked_id}</span>
                {link.linked_label && <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{link.linked_label}</span>}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default ManualReviewPage;
