import { AlertTriangle, BarChart3, Brain, CheckCircle2, Clock, Shield, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';
import { getRoleMode, getRoleHelperPrefix } from '../utils/roleMode.js';

function PredictivePage() {
  const currentUser = (() => { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } })();
  const mode = getRoleMode(currentUser?.role);
  const [summary, setSummary] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [models, setModels] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('predictions');

  async function load() {
    setLoading(true); setError('');
    try {
      const [sRes, pRes, mRes, rRes] = await Promise.all([
        api.get('/predictive/summary'),
        api.get('/predictive/predictions'),
        api.get('/predictive/models'),
        api.get('/predictive/runs'),
      ]);
      setSummary(sRes.data); setPredictions(pRes.data);
      setModels(mRes.data); setRuns(rRes.data);
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (loading) return <LoadingState label="Loading predictive intelligence..." />;

  return (
    <div className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Management</p><h1>Risk Alerts</h1></div></div>
      <p className="page-helper">{getRoleHelperPrefix(mode)}Review rule-based risk predictions and recommended preventive actions.</p>

      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
          <article className="metric-card"><Brain size={20} /><span>Active</span><strong>{summary.total_active}</strong></article>
          <article className="metric-card critical-card"><AlertTriangle size={20} /><span>Critical</span><strong>{summary.critical}</strong></article>
          <article className="metric-card warning-card"><Shield size={20} /><span>High</span><strong>{summary.high}</strong></article>
          <article className="metric-card info-card"><TrendingUp size={20} /><span>Medium</span><strong>{summary.medium}</strong></article>
          <article className="metric-card"><CheckCircle2 size={20} /><span>Low</span><strong>{summary.low}</strong></article>
          <article className="metric-card"><Clock size={20} /><span>Pending Recs</span><strong>{summary.pending_recommendations}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)' }}>
        {['predictions', 'models', 'runs'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t}</button>
        ))}
      </nav>

      {tab === 'predictions' && (
        <div className="panel" style={{ padding: 0 }}>
          {predictions.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Brain size={24} /><div><strong>No predictions yet</strong><p>Run a prediction to generate risk assessments.</p></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Risk</th><th>Domain</th><th>Title</th><th>Score</th><th>Confidence</th><th>Status</th><th>Shipment</th></tr></thead><tbody>
              {predictions.map((p) => (
                <tr key={p.id}>
                  <td><span className={`badge ${p.risk_level === 'critical' ? 'status-critical' : p.risk_level === 'high' ? 'status-warning' : ''}`}>{p.risk_level}</span></td>
                  <td><span className="badge">{p.risk_domain.replace(/_/g, ' ')}</span></td>
                  <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.title}</td>
                  <td style={{ fontWeight: 700 }}>{p.risk_score.toFixed(0)}</td>
                  <td>{(p.confidence * 100).toFixed(0)}%</td>
                  <td><span className="badge">{p.status}</span></td>
                  <td>{p.shipment_id ? <Link to={`/shipments/${p.shipment_id}`}>#{p.shipment_id}</Link> : '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'models' && (
        <div className="panel" style={{ padding: 0 }}>
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Key</th><th>Type</th><th>Domain</th><th>Version</th><th>Status</th></tr></thead><tbody>
            {models.map((m) => (
              <tr key={m.id}>
                <td>{m.name}</td>
                <td><code style={{ fontSize: '0.72rem' }}>{m.model_key}</code></td>
                <td>{m.model_type.replace(/_/g, ' ')}</td>
                <td><span className="badge">{m.risk_domain.replace(/_/g, ' ')}</span></td>
                <td>{m.version}</td>
                <td><span className={`badge ${m.is_active ? 'status-active' : ''}`}>{m.status}</span></td>
              </tr>
            ))}
          </tbody></table></div>
        </div>
      )}

      {tab === 'runs' && (
        <div className="panel" style={{ padding: 0 }}>
          {runs.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><BarChart3 size={24} /><div><strong>No prediction runs</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Run #</th><th>Scope</th><th>Status</th><th>Models</th><th>Records</th><th>High</th><th>Medium</th><th>Started</th></tr></thead><tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td><code style={{ fontSize: '0.72rem' }}>{r.run_number}</code></td>
                  <td>{r.scope}</td>
                  <td><span className={`badge ${r.status === 'completed' ? 'status-active' : r.status === 'failed' ? 'status-critical' : ''}`}>{r.status}</span></td>
                  <td>{r.models_run}</td>
                  <td>{r.records_created}</td>
                  <td style={{ color: r.high_risk_count > 0 ? '#dc2626' : 'inherit', fontWeight: 600 }}>{r.high_risk_count}</td>
                  <td>{r.medium_risk_count}</td>
                  <td style={{ fontSize: '0.78rem' }}>{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}
    </div>
  );
}

export default PredictivePage;
