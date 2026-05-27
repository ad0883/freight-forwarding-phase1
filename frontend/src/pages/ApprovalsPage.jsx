import { CheckCircle2, Clock, FileCheck, Shield, ShieldAlert, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

const RISK_COLORS = { critical: '#dc2626', high: '#ea580c', medium: '#ca8a04', low: '#2563eb' };
const STATUS_LABELS = {
  draft: 'Draft', pending: 'Pending', in_review: 'In Review', changes_requested: 'Changes Requested',
  approved: 'Approved', rejected: 'Rejected', cancelled: 'Cancelled', expired: 'Expired',
  executed: 'Executed', failed_execution: 'Failed',
};

function ApprovalsPage() {
  const [summary, setSummary] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [steps, setSteps] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [tab, setTab] = useState('pending');
  const [actionLoading, setActionLoading] = useState('');

  const currentUser = (() => { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } })();
  const isAdmin = currentUser?.role === 'ADMIN';
  const canMutate = ['ADMIN', 'STAFF'].includes(currentUser?.role);

  async function load() {
    setLoading(true); setError('');
    try {
      const [sRes, lRes] = await Promise.all([
        api.get('/approvals/summary'),
        api.get('/approvals', { params: buildParams() }),
      ]);
      setSummary(sRes.data); setApprovals(lRes.data);
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }

  function buildParams() {
    const p = { limit: 100 };
    if (tab === 'pending') p.status = 'pending';
    if (tab === 'my-queue') p.assigned_to_user_id = currentUser?.id;
    if (tab === 'high-risk') p.risk_level = 'high';
    if (tab === 'approved') p.status = 'approved';
    if (tab === 'rejected') p.status = 'rejected';
    return p;
  }

  useEffect(() => { load(); }, [tab]);

  async function openDetail(item) {
    setSelected(item);
    try {
      const [sRes, eRes] = await Promise.all([
        api.get(`/approvals/${item.id}/steps`),
        api.get(`/approvals/${item.id}/evidence`),
      ]);
      setSteps(sRes.data); setEvidence(eRes.data);
    } catch { /* graceful */ }
  }

  async function doAction(action, body = {}) {
    if (!selected) return;
    setActionLoading(action);
    try {
      const res = await api.post(`/approvals/${selected.id}/${action}`, body);
      setSelected(res.data); load();
    } catch (err) { alert(err.response?.data?.detail || `${action} failed`); }
    setActionLoading('');
  }

  if (error && !approvals.length) return <ErrorState message={error} />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Governance</p>
          <h1>Approval Center</h1>
        </div>
      </div>

      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(5, minmax(130px, 1fr))' }}>
          <article className="metric-card"><Shield size={20} /><span>Pending</span><strong>{summary.total_pending}</strong></article>
          <article className="metric-card info-card"><FileCheck size={20} /><span>Assigned to Me</span><strong>{summary.total_assigned_to_me}</strong></article>
          <article className="metric-card critical-card"><ShieldAlert size={20} /><span>High Risk</span><strong>{summary.total_high_risk}</strong></article>
          <article className="metric-card warning-card"><Clock size={20} /><span>Overdue</span><strong>{summary.total_overdue}</strong></article>
          <article className="metric-card"><Shield size={20} /><span>Bot Pending</span><strong>{summary.total_bot_pending}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)' }}>
        {[
          { key: 'pending', label: 'Pending' },
          { key: 'my-queue', label: 'My Queue' },
          { key: 'high-risk', label: 'High Risk' },
          { key: 'approved', label: 'Approved' },
          { key: 'rejected', label: 'Rejected' },
        ].map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer',
            borderBottom: tab === t.key ? '2px solid var(--color-primary)' : '2px solid transparent',
            marginBottom: '-2px', color: tab === t.key ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: tab === t.key ? 700 : 500, fontSize: '0.85rem',
          }}>{t.label}</button>
        ))}
      </nav>

      {loading ? <LoadingState /> : (
        <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 400px' : '1fr', gap: '1rem', alignItems: 'start' }}>
          <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
            {approvals.length === 0 ? (
              <div className="state-box empty-state" style={{ minHeight: '160px', border: 'none' }}><Shield size={28} /><div><strong>No approvals</strong><p>Nothing here for this view.</p></div></div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Approval #</th><th>Title</th><th>Type</th><th>Risk</th><th>Status</th><th>Assigned</th></tr></thead>
                  <tbody>
                    {approvals.map((a) => (
                      <tr key={a.id} onClick={() => openDetail(a)} className="clickable-row" style={{ background: selected?.id === a.id ? 'var(--color-primary-light)' : undefined }}>
                        <td><code style={{ fontSize: '0.72rem' }}>{a.approval_number}</code></td>
                        <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.title}</td>
                        <td><span className="badge">{a.approval_type.replace(/_/g, ' ')}</span></td>
                        <td><span style={{ color: RISK_COLORS[a.risk_level], fontWeight: 600, fontSize: '0.82rem' }}>{a.risk_level}</span></td>
                        <td><span className="badge">{STATUS_LABELS[a.status] || a.status}</span></td>
                        <td style={{ fontSize: '0.82rem' }}>{a.assigned_to_name || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {selected && (
            <div className="panel" style={{ padding: '1.15rem', position: 'sticky', top: '1rem', maxHeight: 'calc(100vh - 3rem)', overflow: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div>
                  <h2 style={{ fontSize: '1rem', margin: 0 }}>{selected.title}</h2>
                  <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>{selected.approval_number}</p>
                </div>
                <button onClick={() => setSelected(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '1.1rem' }}>✕</button>
              </div>

              <div className="info-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: '1rem' }}>
                <div className="info-item"><span>Type</span><strong>{selected.approval_type.replace(/_/g, ' ')}</strong></div>
                <div className="info-item"><span>Risk</span><strong style={{ color: RISK_COLORS[selected.risk_level] }}>{selected.risk_level}</strong></div>
                <div className="info-item"><span>Status</span><strong>{STATUS_LABELS[selected.status]}</strong></div>
                <div className="info-item"><span>Steps</span><strong>{selected.current_step_no}/{selected.required_steps}</strong></div>
                <div className="info-item"><span>Requested By</span><strong>{selected.requested_by_name || '—'}</strong></div>
                <div className="info-item"><span>Action</span><strong style={{ fontSize: '0.82rem' }}>{selected.requested_action}</strong></div>
              </div>

              {selected.description && <p style={{ fontSize: '0.84rem', color: 'var(--color-text-secondary)', marginBottom: '0.75rem', padding: '0.6rem', background: '#f8fafc', borderRadius: '6px' }}>{selected.description}</p>}

              {/* Steps */}
              {steps.length > 0 && (
                <div style={{ marginBottom: '0.75rem' }}>
                  <h3 style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>Approval Steps</h3>
                  {steps.map((s) => (
                    <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.82rem' }}>
                      <span style={{ width: '20px', textAlign: 'center' }}>{s.status === 'approved' ? '✅' : s.status === 'rejected' ? '❌' : '⏳'}</span>
                      <span>Step {s.step_no}</span>
                      <span className="badge" style={{ fontSize: '0.68rem' }}>{s.status}</span>
                      {s.approver_name && <span className="muted">— {s.approver_name}</span>}
                    </div>
                  ))}
                </div>
              )}

              {/* Evidence */}
              {evidence.length > 0 && (
                <div style={{ marginBottom: '0.75rem' }}>
                  <h3 style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>Evidence</h3>
                  {evidence.map((e) => (
                    <div key={e.id} style={{ padding: '0.35rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
                      <span className="badge" style={{ fontSize: '0.68rem' }}>{e.evidence_type}</span>
                      {e.label && <span style={{ marginLeft: '0.4rem' }}>{e.label}</span>}
                      {e.summary && <p className="muted" style={{ margin: '0.15rem 0 0', fontSize: '0.78rem' }}>{e.summary}</p>}
                    </div>
                  ))}
                </div>
              )}

              {/* Actions */}
              {canMutate && ['pending', 'in_review', 'changes_requested'].includes(selected.status) && (
                <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)' }}>
                  {isAdmin && <button className="primary-button" onClick={() => doAction('approve', { notes: 'Approved' })} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}><CheckCircle2 size={13} /> Approve</button>}
                  {isAdmin && <button className="secondary-button" onClick={() => doAction('reject', { notes: 'Rejected' })} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}><XCircle size={13} /> Reject</button>}
                  {isAdmin && <button className="secondary-button" onClick={() => doAction('request-changes', { notes: 'Please provide more info' })} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>Request Changes</button>}
                  <button className="secondary-button" onClick={() => doAction('cancel', { notes: 'Cancelled' })} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}>Cancel</button>
                </div>
              )}
              {isAdmin && selected.status === 'approved' && (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)' }}>
                  <button className="primary-button" onClick={() => doAction('execute')} disabled={!!actionLoading} style={{ fontSize: '0.78rem' }}><FileCheck size={13} /> Execute Approved Action</button>
                </div>
              )}

              {selected.shipment_id && (
                <div style={{ marginTop: '0.75rem' }}>
                  <Link to={`/shipments/${selected.shipment_id}`} style={{ fontSize: '0.82rem' }}>View Shipment #{selected.shipment_id} →</Link>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ApprovalsPage;
