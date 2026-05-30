import { AlertTriangle, CheckCircle2, Shield, ShieldCheck, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';
import AccessDeniedCard from '../components/AccessDeniedCard.jsx';

function EnterprisePage() {
  const currentUser = (() => { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } })();
  if (currentUser && currentUser.role !== 'ADMIN') {
    return <AccessDeniedCard title="Admin Settings" message="This section is available to Admin users only. Contact your admin if you need access." />;
  }
  const [health, setHealth] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('health');

  async function load() {
    setLoading(true); setError('');
    try {
      const results = await Promise.allSettled([
        api.get('/enterprise/health'),
        api.get('/enterprise/organizations'),
        api.get('/enterprise/roles'),
        api.get('/enterprise/permissions/matrix'),
        api.get('/enterprise/security-events'),
        api.get('/subscriptions/summary'),
      ]);
      if (results[0].status === 'fulfilled') setHealth(results[0].value.data);
      if (results[1].status === 'fulfilled') setOrgs(results[1].value.data);
      if (results[2].status === 'fulfilled') setRoles(results[2].value.data);
      if (results[3].status === 'fulfilled') setPermissions(results[3].value.data);
      if (results[4].status === 'fulfilled') setSecurityEvents(results[4].value.data);
      if (results[5].status === 'fulfilled') setSubscription(results[5].value.data);
      const allFailed = results.every(r => r.status === 'rejected');
      if (allFailed) setError('Failed to load enterprise data');
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (loading) return <LoadingState label="Loading enterprise governance..." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Admin Settings</h1>
        </div>
        {subscription && (
          <div className="page-header-actions">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--color-surface)', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontSize: '0.85rem' }}>
              <span className="muted">Plan:</span> <strong>{subscription.plan_name}</strong>
              <span className={`badge status-${subscription.is_active ? 'active' : 'critical'}`} style={{ marginLeft: '0.5rem' }}>{subscription.status.toUpperCase()}</span>
              {subscription.is_trial && subscription.trial_ends_at && (
                <span className="muted" style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>Ends: {new Date(subscription.trial_ends_at).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        )}
      </div>
      <p className="page-helper">Manage organization settings, users, roles, and system health.</p>

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)', flexWrap: 'wrap' }}>
        {['health', 'organizations', 'roles', 'permissions', 'security'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t}</button>
        ))}
      </nav>

      {tab === 'health' && health && (
        <div className="panel" style={{ padding: '1rem' }}>
          <h3 style={{ margin: '0 0 0.75rem' }}>Enterprise Health: <span style={{ color: health.overall_status === 'ok' ? '#16a34a' : '#dc2626' }}>{health.overall_status.toUpperCase()}</span></h3>
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {health.checks.map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0.6rem', background: 'var(--color-surface)', borderRadius: '4px' }}>
                {c.status === 'ok' ? <CheckCircle2 size={16} color="#16a34a" /> : c.status === 'warning' ? <AlertTriangle size={16} color="#ca8a04" /> : <AlertTriangle size={16} color="#dc2626" />}
                <span style={{ fontWeight: 500, fontSize: '0.85rem', minWidth: '200px' }}>{c.check.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{c.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'organizations' && (
        <div className="panel" style={{ padding: 0 }}>
          {orgs.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '100px', border: 'none' }}><Shield size={24} /><div><strong>No organizations</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {orgs.map((o) => (
                <tr key={o.id}><td>{o.name}</td><td>{o.organization_type || '—'}</td><td><span className="badge status-active">{o.status}</span></td><td style={{ fontSize: '0.78rem' }}>{new Date(o.created_at).toLocaleDateString()}</td></tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'roles' && (
        <div className="panel" style={{ padding: 0 }}>
          <div className="table-wrap"><table><thead><tr><th>Key</th><th>Name</th><th>Scope</th><th>System</th><th>Active</th></tr></thead><tbody>
            {roles.map((r) => (
              <tr key={r.id}><td><code style={{ fontSize: '0.72rem' }}>{r.role_key}</code></td><td>{r.role_name}</td><td>{r.scope}</td><td>{r.is_system_role ? '✓' : '—'}</td><td>{r.is_active ? '✓' : '—'}</td></tr>
            ))}
          </tbody></table></div>
        </div>
      )}

      {tab === 'permissions' && (
        <div className="panel" style={{ padding: 0 }}>
          <div className="table-wrap"><table><thead><tr><th>Role</th><th>Resource</th><th>Action</th><th>Effect</th></tr></thead><tbody>
            {permissions.map((p) => (
              <tr key={p.id}><td><code style={{ fontSize: '0.72rem' }}>{p.role_key}</code></td><td>{p.resource_key}</td><td>{p.action_key}</td><td><span className={`badge ${p.effect === 'allow' ? 'status-active' : 'status-critical'}`}>{p.effect}</span></td></tr>
            ))}
          </tbody></table></div>
        </div>
      )}

      {tab === 'security' && (
        <div className="panel" style={{ padding: 0 }}>
          {securityEvents.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '100px', border: 'none' }}><ShieldCheck size={24} /><div><strong>No security events</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Type</th><th>Severity</th><th>Summary</th><th>Time</th></tr></thead><tbody>
              {securityEvents.map((e) => (
                <tr key={e.id}><td><span className="badge">{e.event_type}</span></td><td style={{ color: e.severity === 'critical' ? '#dc2626' : 'inherit' }}>{e.severity}</td><td>{e.safe_summary}</td><td style={{ fontSize: '0.78rem' }}>{new Date(e.created_at).toLocaleString()}</td></tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}
    </div>
  );
}

export default EnterprisePage;
