import { Activity, AlertTriangle, Bot, CheckCircle2, Clock, Pause, Play, Shield } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function BotGovernancePage() {
  const [summary, setSummary] = useState(null);
  const [agents, setAgents] = useState([]);
  const [actions, setActions] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('agents');
  const [actionLoading, setActionLoading] = useState('');

  const currentUser = (() => { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } })();
  const isAdmin = currentUser?.role === 'ADMIN';

  async function load() {
    setLoading(true); setError('');
    try {
      const [sRes, aRes] = await Promise.all([
        api.get('/bot-governance/summary'),
        api.get('/bot-governance/agents'),
      ]);
      setSummary(sRes.data); setAgents(aRes.data);
      if (tab === 'actions') { const r = await api.get('/bot-governance/actions'); setActions(r.data); }
      if (tab === 'learning') { const r = await api.get('/bot-governance/learning-candidates'); setCandidates(r.data); }
      if (tab === 'guardrails') { const r = await api.get('/bot-governance/guardrail-violations'); setViolations(r.data); }
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [tab]);

  async function pauseAgent(id) {
    setActionLoading(`pause-${id}`);
    try { await api.post(`/bot-governance/agents/${id}/pause`); load(); } catch {}
    setActionLoading('');
  }
  async function resumeAgent(id) {
    setActionLoading(`resume-${id}`);
    try { await api.post(`/bot-governance/agents/${id}/resume`); load(); } catch {}
    setActionLoading('');
  }

  if (error && !agents.length) return <ErrorState message={error} />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div><p className="eyebrow">Intelligence</p><h1>Bot Governance</h1></div>
      </div>

      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(140px, 1fr))' }}>
          <article className="metric-card"><Bot size={20} /><span>Active Agents</span><strong>{summary.active_agents}</strong></article>
          <article className="metric-card warning-card"><AlertTriangle size={20} /><span>Needs Review</span><strong>{summary.needs_review}</strong></article>
          <article className="metric-card critical-card"><Shield size={20} /><span>Guardrail Violations</span><strong>{summary.guardrail_violations}</strong></article>
          <article className="metric-card info-card"><Activity size={20} /><span>Open Candidates</span><strong>{summary.open_learning_candidates}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)' }}>
        {['agents', 'actions', 'learning', 'guardrails'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t}</button>
        ))}
      </nav>

      {loading ? <LoadingState /> : (
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          {tab === 'agents' && (
            <div className="table-wrap"><table><thead><tr><th>Bot</th><th>Type</th><th>Status</th><th>Risk</th><th>Approval Required</th><th>Actions</th></tr></thead><tbody>
              {agents.map((a) => (
                <tr key={a.id}>
                  <td><strong>{a.name}</strong><br/><code style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{a.bot_key}</code></td>
                  <td><span className="badge">{a.bot_type}</span></td>
                  <td><span className={`badge ${a.status === 'active' ? 'status-active' : a.status === 'paused' ? 'priority-warning' : 'priority-critical'}`}>{a.status}</span></td>
                  <td style={{ fontWeight: 600, color: a.risk_level === 'high' ? '#ea580c' : a.risk_level === 'critical' ? '#dc2626' : 'inherit' }}>{a.risk_level}</td>
                  <td>{a.is_approval_required ? '✅ Yes' : '—'}</td>
                  <td>
                    {isAdmin && a.status === 'active' && <button className="secondary-button" onClick={() => pauseAgent(a.id)} disabled={!!actionLoading} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}><Pause size={12} /> Pause</button>}
                    {isAdmin && a.status === 'paused' && <button className="secondary-button" onClick={() => resumeAgent(a.id)} disabled={!!actionLoading} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}><Play size={12} /> Resume</button>}
                  </td>
                </tr>
              ))}
            </tbody></table></div>
          )}

          {tab === 'actions' && (
            <div className="table-wrap"><table><thead><tr><th>Bot</th><th>Action</th><th>Status</th><th>Risk</th><th>Confidence</th><th>Outcome</th><th>Created</th></tr></thead><tbody>
              {actions.map((a) => (
                <tr key={a.id}>
                  <td><code style={{ fontSize: '0.72rem' }}>{a.bot_key}</code></td>
                  <td>{a.action_type}</td>
                  <td><span className="badge">{a.status}</span></td>
                  <td style={{ fontWeight: 600 }}>{a.risk_level}</td>
                  <td>{a.confidence != null ? `${a.confidence}%` : '—'}</td>
                  <td>{a.outcome_status || '—'}</td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{new Date(a.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {!actions.length && <tr><td colSpan="7" style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>No bot actions recorded yet.</td></tr>}
            </tbody></table></div>
          )}

          {tab === 'learning' && (
            <div className="table-wrap"><table><thead><tr><th>Bot</th><th>Type</th><th>Title</th><th>Risk</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {candidates.map((c) => (
                <tr key={c.id}>
                  <td><code style={{ fontSize: '0.72rem' }}>{c.bot_key}</code></td>
                  <td><span className="badge">{c.candidate_type}</span></td>
                  <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title}</td>
                  <td style={{ fontWeight: 600 }}>{c.risk_level}</td>
                  <td><span className="badge">{c.status}</span></td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {!candidates.length && <tr><td colSpan="6" style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>No learning candidates.</td></tr>}
            </tbody></table></div>
          )}

          {tab === 'guardrails' && (
            <div className="table-wrap"><table><thead><tr><th>Bot</th><th>Violation</th><th>Severity</th><th>Message</th><th>Blocked</th><th>Created</th></tr></thead><tbody>
              {violations.map((v) => (
                <tr key={v.id}>
                  <td><code style={{ fontSize: '0.72rem' }}>{v.bot_key}</code></td>
                  <td><span className="badge priority-critical">{v.violation_type}</span></td>
                  <td style={{ fontWeight: 600, color: v.severity === 'critical' ? '#dc2626' : v.severity === 'high' ? '#ea580c' : 'inherit' }}>{v.severity}</td>
                  <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.82rem' }}>{v.message}</td>
                  <td style={{ fontSize: '0.82rem' }}>{v.blocked_action || '—'}</td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{new Date(v.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {!violations.length && <tr><td colSpan="6" style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>No guardrail violations. All clear.</td></tr>}
            </tbody></table></div>
          )}
        </div>
      )}
    </div>
  );
}

export default BotGovernancePage;
