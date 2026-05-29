import { Activity, AlertTriangle, Anchor, BarChart3, CheckCircle2, Clock, CreditCard, Eye, FileText, Globe, Map, MapPin, Radio, Ship, ShieldAlert, Truck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function WidgetError({ name }) {
  return <div className="state-box empty-state" style={{ minHeight: '80px', border: '1px dashed var(--color-border)' }}><AlertTriangle size={18} /><div><strong>{name}</strong><p style={{ fontSize: '0.78rem' }}>Failed to load. <button onClick={() => window.location.reload()} style={{ color: 'var(--color-primary)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>Retry</button></p></div></div>;
}

function ControlTowerPage() {
  const [summary, setSummary] = useState(null);
  const [riskHeatmap, setRiskHeatmap] = useState(null);
  const [topRisks, setTopRisks] = useState(null);
  const [slaOverdue, setSlaOverdue] = useState(null);
  const [mapReadiness, setMapReadiness] = useState(null);
  const [etaChanges, setEtaChanges] = useState(null);
  const [sourceHealth, setSourceHealth] = useState(null);
  const [staleData, setStaleData] = useState(null);
  const [partyPerf, setPartyPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState({});

  async function load() {
    setLoading(true); setErrors({});
    const fetches = [
      { key: 'summary', url: '/control-tower/summary', setter: setSummary },
      { key: 'risk', url: '/control-tower/risk-heatmap', setter: setRiskHeatmap },
      { key: 'topRisks', url: '/control-tower/top-risks', setter: setTopRisks },
      { key: 'sla', url: '/control-tower/sla-overdue', setter: setSlaOverdue },
      { key: 'map', url: '/control-tower/map-readiness', setter: setMapReadiness },
      { key: 'eta', url: '/control-tower/eta-etd-changes', setter: setEtaChanges },
      { key: 'health', url: '/control-tower/tracking-source-health', setter: setSourceHealth },
      { key: 'stale', url: '/control-tower/stale-data', setter: setStaleData },
      { key: 'party', url: '/control-tower/party-performance', setter: setPartyPerf },
    ];
    const results = await Promise.allSettled(fetches.map(f => api.get(f.url)));
    const errs = {};
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') fetches[i].setter(r.value.data);
      else errs[fetches[i].key] = true;
    });
    setErrors(errs);
    setLoading(false);
  }
  useEffect(() => { load(); }, []);

  if (loading) return <LoadingState label="Loading Control Tower — aggregating operations data..." />;

  const ops = summary?.operations || {};
  const ea = summary?.exceptions_approvals || {};
  const trk = summary?.tracking || {};

  return (
    <div className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Command Center</p><h1>Control Tower</h1></div></div>

      {/* Executive Overview */}
      <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}>
        {riskHeatmap && <article className={`metric-card ${riskHeatmap.risk_level === 'critical' ? 'critical-card' : riskHeatmap.risk_level === 'high' ? 'warning-card' : 'info-card'}`}><Activity size={20} /><span>Risk Score</span><strong>{riskHeatmap.risk_score}</strong></article>}
        <article className="metric-card"><Ship size={20} /><span>Active Shipments</span><strong>{ops.active_shipments ?? '—'}</strong></article>
        <article className="metric-card critical-card"><AlertTriangle size={20} /><span>Critical Exceptions</span><strong><Link to="/manual-review">{ea.critical_exceptions ?? 0}</Link></strong></article>
        <article className="metric-card warning-card"><Clock size={20} /><span>Pending Approvals</span><strong><Link to="/approvals">{ea.pending_approvals ?? 0}</Link></strong></article>
        <article className="metric-card"><Radio size={20} /><span>Tracking Mismatches</span><strong><Link to="/tracking">{trk.open_mismatches ?? 0}</Link></strong></article>
        <article className="metric-card"><Truck size={20} /><span>Transport Delayed</span><strong><Link to="/transport">{summary?.transport?.delayed ?? 0}</Link></strong></article>
      </div>

      {/* Risk Heatmap */}
      {riskHeatmap && (
        <div className="panel" style={{ padding: '1rem' }}>
          <h3 style={{ margin: '0 0 0.5rem' }}>Risk Heatmap</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.5rem' }}>
            {Object.entries(riskHeatmap.inputs || {}).map(([k, v]) => (
              <div key={k} style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: '6px', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>{k.replace(/_/g, ' ')}</span>
                <strong style={{ display: 'block', fontSize: '1.1rem' }}>{v}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Risks */}
      {topRisks && topRisks.length > 0 && (
        <div className="panel" style={{ padding: 0 }}>
          <h3 style={{ padding: '0.75rem 1rem 0' }}>Top Risks</h3>
          <div className="table-wrap"><table><thead><tr><th>Type</th><th>Severity</th><th>Title</th><th>Link</th></tr></thead><tbody>
            {topRisks.map((r, i) => (
              <tr key={i}>
                <td><span className="badge">{r.type.replace(/_/g, ' ')}</span></td>
                <td style={{ fontWeight: 600, color: r.severity === 'critical' ? '#dc2626' : '#ea580c' }}>{r.severity}</td>
                <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title}</td>
                <td><Link to={r.link}>View →</Link></td>
              </tr>
            ))}
          </tbody></table></div>
        </div>
      )}

      {/* Map Readiness (Phase 22.1) */}
      {mapReadiness ? (
        <div className="panel" style={{ padding: '1rem' }}>
          <h3 style={{ margin: '0 0 0.5rem' }}><Globe size={16} style={{ marginRight: '0.4rem' }} />Map Readiness</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
            {Object.entries(mapReadiness).map(([k, v]) => (
              <div key={k} style={{ padding: '0.75rem', background: 'var(--color-surface)', borderRadius: '6px' }}>
                <strong style={{ fontSize: '0.85rem' }}>{k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: '0.25rem 0' }}>{v.message}</p>
                <span style={{ fontSize: '0.78rem' }}>Data points: {v.items_count}</span>
              </div>
            ))}
          </div>
        </div>
      ) : errors.map && <WidgetError name="Map Readiness" />}

      {/* Stale Data Monitor (Phase 22.1) */}
      {staleData ? (
        staleData.warnings?.length > 0 && (
          <div className="panel" style={{ padding: 0 }}>
            <h3 style={{ padding: '0.75rem 1rem 0' }}><Clock size={16} style={{ marginRight: '0.4rem' }} />Stale Data Monitor ({staleData.total_stale} items)</h3>
            <div className="table-wrap"><table><thead><tr><th>Category</th><th>Count</th><th>Threshold</th><th>Link</th></tr></thead><tbody>
              {staleData.warnings.map((w, i) => (
                <tr key={i}>
                  <td style={{ textTransform: 'capitalize' }}>{w.category}</td>
                  <td><strong>{w.count}</strong></td>
                  <td>{w.threshold}</td>
                  <td><Link to={w.link}>View →</Link></td>
                </tr>
              ))}
            </tbody></table></div>
          </div>
        )
      ) : errors.stale && <WidgetError name="Stale Data Monitor" />}

      {/* Tracking Source Health (Phase 22.1) */}
      {sourceHealth ? (
        <div className="panel" style={{ padding: 0 }}>
          <h3 style={{ padding: '0.75rem 1rem 0' }}><Radio size={16} style={{ marginRight: '0.4rem' }} />Tracking Adapter Health</h3>
          <div className="table-wrap"><table><thead><tr><th>Provider</th><th>Type</th><th>Status</th><th>Manual/Mock</th><th>Last Sync</th><th>Failed</th><th>Stale</th></tr></thead><tbody>
            {sourceHealth.map((h, i) => (
              <tr key={i}>
                <td>{h.name}</td>
                <td><span className="badge">{h.provider_type.replace(/_/g, ' ')}</span></td>
                <td><span className={`badge ${h.status === 'active' ? 'status-active' : ''}`}>{h.status}</span></td>
                <td>{h.is_manual ? 'Manual' : h.is_mock ? 'Mock' : 'Real'}</td>
                <td style={{ fontSize: '0.78rem' }}>{h.last_sync_at ? new Date(h.last_sync_at).toLocaleString() : '—'}</td>
                <td style={{ color: h.failed_sync_count > 0 ? '#dc2626' : 'inherit' }}>{h.failed_sync_count}</td>
                <td style={{ color: h.stale_watch_items > 0 ? '#ca8a04' : 'inherit' }}>{h.stale_watch_items}</td>
              </tr>
            ))}
          </tbody></table></div>
        </div>
      ) : errors.health && <WidgetError name="Tracking Source Health" />}

      {/* Party Performance (Phase 22.1) */}
      {partyPerf ? (
        <div className="panel" style={{ padding: '1rem' }}>
          <h3 style={{ margin: '0 0 0.5rem' }}>Party Performance</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
            <div style={{ padding: '0.75rem', background: 'var(--color-surface)', borderRadius: '6px' }}>
              <strong>CHA</strong>
              <p style={{ fontSize: '0.8rem', margin: '0.25rem 0' }}>Open queries: <Link to="/customs">{partyPerf.cha?.open_queries ?? 0}</Link></p>
              <p style={{ fontSize: '0.8rem', margin: 0 }}>Delayed cases: {partyPerf.cha?.delayed_cases ?? 0}</p>
            </div>
            <div style={{ padding: '0.75rem', background: 'var(--color-surface)', borderRadius: '6px' }}>
              <strong>Transporter</strong>
              <p style={{ fontSize: '0.8rem', margin: '0.25rem 0' }}>Delayed jobs: <Link to="/transport">{partyPerf.transporter?.delayed_jobs ?? 0}</Link></p>
              <p style={{ fontSize: '0.8rem', margin: 0 }}>Empty pending: {partyPerf.transporter?.empty_return_pending ?? 0}</p>
            </div>
            <div style={{ padding: '0.75rem', background: 'var(--color-surface)', borderRadius: '6px' }}>
              <strong>Customer</strong>
              <p style={{ fontSize: '0.8rem', margin: '0.25rem 0' }}>Open requests: <Link to="/portal">{partyPerf.customer?.open_requests ?? 0}</Link></p>
            </div>
          </div>
        </div>
      ) : errors.party && <WidgetError name="Party Performance" />}

      {/* SLA Overdue */}
      {slaOverdue && slaOverdue.length > 0 && (
        <div className="panel" style={{ padding: 0 }}>
          <h3 style={{ padding: '0.75rem 1rem 0' }}>SLA Overdue</h3>
          <div className="table-wrap"><table><thead><tr><th>Type</th><th>Title</th><th>Days Overdue</th><th>Link</th></tr></thead><tbody>
            {slaOverdue.map((s, i) => (
              <tr key={i}>
                <td><span className="badge">{s.type}</span></td>
                <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</td>
                <td style={{ fontWeight: 600, color: s.days_overdue > 5 ? '#dc2626' : '#ca8a04' }}>{s.days_overdue}d</td>
                <td><Link to={s.link}>View →</Link></td>
              </tr>
            ))}
          </tbody></table></div>
        </div>
      )}

      {/* ETA/ETD Changes (Phase 22.1) */}
      {etaChanges && etaChanges.length > 0 && (
        <div className="panel" style={{ padding: 0 }}>
          <h3 style={{ padding: '0.75rem 1rem 0' }}>ETA / ETD Changes</h3>
          <div className="table-wrap"><table><thead><tr><th>Shipment</th><th>Latest ETA</th><th>Source</th><th>Confidence</th><th>Vessel</th><th>Received</th></tr></thead><tbody>
            {etaChanges.slice(0, 10).map((e, i) => (
              <tr key={i}>
                <td>{e.shipment_id ? <Link to={`/shipments/${e.shipment_id}`}>#{e.shipment_id}</Link> : '—'}</td>
                <td>{e.latest_eta ? new Date(e.latest_eta).toLocaleDateString() : '—'}</td>
                <td>{e.source?.replace(/_/g, ' ')}</td>
                <td style={{ fontWeight: 600 }}>{e.confidence ? `${(e.confidence * 100).toFixed(0)}%` : '—'}</td>
                <td>{e.vessel_name || '—'}</td>
                <td style={{ fontSize: '0.78rem' }}>{new Date(e.received_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody></table></div>
        </div>
      )}
    </div>
  );
}

export default ControlTowerPage;
