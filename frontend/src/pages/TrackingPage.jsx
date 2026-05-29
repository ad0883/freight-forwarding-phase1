import { AlertTriangle, CheckCircle2, Clock, Eye, Radio, RefreshCw, Satellite } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function TrackingPage() {
  const [summary, setSummary] = useState(null);
  const [watchItems, setWatchItems] = useState([]);
  const [observations, setObservations] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [mismatches, setMismatches] = useState([]);
  const [providers, setProviders] = useState([]);
  const [syncRuns, setSyncRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('watch-items');
  const [syncing, setSyncing] = useState(false);

  async function load() {
    setLoading(true); setError('');
    try {
      const [sRes, wRes, oRes, sgRes, mRes, pRes, srRes] = await Promise.all([
        api.get('/tracking/summary'),
        api.get('/tracking/watch-items'),
        api.get('/tracking/observations'),
        api.get('/tracking/suggestions'),
        api.get('/tracking/mismatches'),
        api.get('/tracking/providers'),
        api.get('/tracking/sync-runs'),
      ]);
      setSummary(sRes.data); setWatchItems(wRes.data); setObservations(oRes.data);
      setSuggestions(sgRes.data); setMismatches(mRes.data); setProviders(pRes.data);
      setSyncRuns(srRes.data);
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (loading) return <LoadingState label="Loading tracking data..." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div><p className="eyebrow">Operations</p><h1>Tracking</h1></div>
        <button className="primary-button" disabled={syncing} onClick={async () => {
          setSyncing(true);
          try { await api.post('/tracking/run-sync', {}); await load(); }
          catch (err) { setError('Sync failed: ' + (err.response?.data?.detail || 'Unknown error')); }
          finally { setSyncing(false); }
        }}>
          <RefreshCw size={16} className={syncing ? 'spin-icon' : ''} />
          <span>{syncing ? 'Syncing — may take up to 30s...' : 'Run Sync'}</span>
        </button>
      </div>
      <p className="page-helper">Monitor container and vessel tracking updates, mismatches, and sync health.</p>
      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(6, minmax(100px, 1fr))' }}>
          <article className="metric-card"><Eye size={20} /><span>Watch Items</span><strong>{summary.active_watch_items}</strong></article>
          <article className="metric-card info-card"><Radio size={20} /><span>Observations</span><strong>{summary.total_observations}</strong></article>
          <article className="metric-card warning-card"><Clock size={20} /><span>Pending</span><strong>{summary.pending_suggestions}</strong></article>
          <article className="metric-card critical-card"><AlertTriangle size={20} /><span>Mismatches</span><strong>{summary.open_mismatches}</strong></article>
          <article className="metric-card"><RefreshCw size={20} /><span>Failed Syncs</span><strong>{summary.failed_sync_runs}</strong></article>
          <article className="metric-card"><Satellite size={20} /><span>Stale</span><strong>{summary.stale_tracking}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)', flexWrap: 'wrap' }}>
        {['watch-items', 'observations', 'suggestions', 'mismatches', 'providers', 'sync-runs'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t.replace('-', ' ')}</button>
        ))}
      </nav>

      {tab === 'watch-items' && (
        <div className="panel" style={{ padding: 0 }}>
          {watchItems.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Eye size={24} /><div><strong>No watch items</strong><p>Create a watch item to start tracking.</p></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Type</th><th>Identifier</th><th>Shipment</th><th>Status</th><th>Last Sync</th><th>Last Observation</th></tr></thead><tbody>
              {watchItems.map((w) => (
                <tr key={w.id}>
                  <td><span className="badge">{w.watch_type}</span></td>
                  <td><code style={{ fontSize: '0.72rem' }}>{w.tracking_identifier}</code></td>
                  <td>{w.shipment_id ? <Link to={`/shipments/${w.shipment_id}`}>#{w.shipment_id}</Link> : '—'}</td>
                  <td><span className={`badge ${w.status === 'active' ? 'status-active' : ''}`}>{w.status}</span></td>
                  <td style={{ fontSize: '0.78rem' }}>{w.last_sync_at ? new Date(w.last_sync_at).toLocaleString() : '—'}</td>
                  <td style={{ fontSize: '0.78rem' }}>{w.last_observation_at ? new Date(w.last_observation_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'observations' && (
        <div className="panel" style={{ padding: 0 }}>
          {observations.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Radio size={24} /><div><strong>No observations</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Status</th><th>Source</th><th>Location</th><th>Confidence</th><th>ETA</th><th>Vessel</th><th>Received</th></tr></thead><tbody>
              {observations.map((o) => (
                <tr key={o.id}>
                  <td><span className="badge">{o.normalized_status.replace(/_/g, ' ')}</span></td>
                  <td>{o.source.replace(/_/g, ' ')}</td>
                  <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.location_text || '—'}</td>
                  <td style={{ fontWeight: 600, color: o.confidence >= 0.8 ? '#16a34a' : o.confidence >= 0.5 ? '#ca8a04' : '#dc2626' }}>{(o.confidence * 100).toFixed(0)}%</td>
                  <td style={{ fontSize: '0.78rem' }}>{o.eta ? new Date(o.eta).toLocaleDateString() : '—'}</td>
                  <td>{o.vessel_name || '—'}</td>
                  <td style={{ fontSize: '0.78rem' }}>{new Date(o.received_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'suggestions' && (
        <div className="panel" style={{ padding: 0 }}>
          {suggestions.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><CheckCircle2 size={24} /><div><strong>No pending suggestions</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Type</th><th>Target</th><th>Field</th><th>Suggested</th><th>Confidence</th><th>Risk</th><th>Status</th></tr></thead><tbody>
              {suggestions.map((s) => (
                <tr key={s.id}>
                  <td><span className="badge">{s.suggestion_type.replace(/_/g, ' ')}</span></td>
                  <td>{s.target_entity_type}</td>
                  <td>{s.target_field}</td>
                  <td><code style={{ fontSize: '0.72rem' }}>{s.suggested_value || '—'}</code></td>
                  <td style={{ fontWeight: 600 }}>{(s.confidence * 100).toFixed(0)}%</td>
                  <td style={{ color: s.risk_level === 'high' ? '#dc2626' : s.risk_level === 'medium' ? '#ca8a04' : '#16a34a' }}>{s.risk_level}</td>
                  <td><span className="badge">{s.status.replace(/_/g, ' ')}</span></td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'mismatches' && (
        <div className="panel" style={{ padding: 0 }}>
          {mismatches.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><CheckCircle2 size={24} /><div><strong>No tracking mismatches</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Title</th><th>Type</th><th>Severity</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {mismatches.map((m) => (
                <tr key={m.id}>
                  <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.title}</td>
                  <td><span className="badge">{m.mismatch_type.replace(/_/g, ' ')}</span></td>
                  <td style={{ fontWeight: 600, color: m.severity === 'critical' ? '#dc2626' : m.severity === 'high' ? '#ea580c' : 'inherit' }}>{m.severity}</td>
                  <td><span className="badge">{m.status}</span></td>
                  <td style={{ fontSize: '0.78rem' }}>{new Date(m.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'providers' && (
        <div className="panel" style={{ padding: 0 }}>
          {providers.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Satellite size={24} /><div><strong>No providers</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Name</th><th>Key</th><th>Type</th><th>Status</th><th>Manual</th><th>Mock</th><th>Container</th><th>Vessel</th></tr></thead><tbody>
              {providers.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td><code style={{ fontSize: '0.72rem' }}>{p.provider_key}</code></td>
                  <td><span className="badge">{p.provider_type.replace(/_/g, ' ')}</span></td>
                  <td><span className={`badge ${p.status === 'active' ? 'status-active' : ''}`}>{p.status}</span></td>
                  <td>{p.is_manual ? '✓' : '—'}</td>
                  <td>{p.is_mock ? '✓' : '—'}</td>
                  <td>{p.supports_container_tracking ? '✓' : '—'}</td>
                  <td>{p.supports_vessel_tracking ? '✓' : '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'sync-runs' && (
        <div className="panel" style={{ padding: 0 }}>
          {syncRuns.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><RefreshCw size={24} /><div><strong>No sync runs</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Status</th><th>Scope</th><th>Items</th><th>Observations</th><th>Suggestions</th><th>Mismatches</th><th>Started</th></tr></thead><tbody>
              {syncRuns.map((r) => (
                <tr key={r.id}>
                  <td><span className={`badge ${r.status === 'completed' ? 'status-active' : r.status === 'failed' ? 'status-critical' : ''}`}>{r.status}</span></td>
                  <td>{r.scope}</td>
                  <td>{r.watch_items_processed}</td>
                  <td>{r.observations_created}</td>
                  <td>{r.suggestions_created}</td>
                  <td>{r.mismatches_created}</td>
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

export default TrackingPage;
