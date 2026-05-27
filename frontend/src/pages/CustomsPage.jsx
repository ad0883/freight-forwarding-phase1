import { AlertTriangle, CheckCircle2, Clock, FileText, Ship } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function CustomsPage() {
  const [summary, setSummary] = useState(null);
  const [cases, setCases] = useState([]);
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('cases');

  async function load() {
    setLoading(true); setError('');
    try {
      const [sRes, cRes, qRes] = await Promise.all([
        api.get('/customs/summary'), api.get('/customs'), api.get('/customs/queries'),
      ]);
      setSummary(sRes.data); setCases(cRes.data); setQueries(qRes.data);
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  if (error) return <ErrorState message={error} />;
  if (loading) return <LoadingState />;

  return (
    <div className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Operations</p><h1>Customs Coordination</h1></div></div>

      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(5, minmax(120px, 1fr))' }}>
          <article className="metric-card"><Ship size={20} /><span>Active Cases</span><strong>{summary.total_active}</strong></article>
          <article className="metric-card warning-card"><FileText size={20} /><span>Docs Pending</span><strong>{summary.documents_pending}</strong></article>
          <article className="metric-card info-card"><Clock size={20} /><span>OOC Pending</span><strong>{summary.ooc_pending}</strong></article>
          <article className="metric-card"><CheckCircle2 size={20} /><span>LEO Pending</span><strong>{summary.leo_pending}</strong></article>
          <article className="metric-card critical-card"><AlertTriangle size={20} /><span>Queries Open</span><strong>{summary.queries_open}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)' }}>
        {['cases', 'queries'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t}</button>
        ))}
      </nav>

      {tab === 'cases' && (
        <div className="panel" style={{ padding: 0 }}>
          {cases.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Ship size={24} /><div><strong>No customs cases</strong><p>Create a customs case from a shipment.</p></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Case #</th><th>Shipment</th><th>Direction</th><th>Type</th><th>Status</th><th>CHA</th><th>Port</th><th>OOC/LEO</th></tr></thead><tbody>
              {cases.map((c) => (
                <tr key={c.id}>
                  <td><code style={{ fontSize: '0.72rem' }}>{c.case_number}</code></td>
                  <td><Link to={`/shipments/${c.shipment_id}`}>#{c.shipment_id}</Link></td>
                  <td><span className="badge">{c.customs_direction}</span></td>
                  <td>{c.case_type.replace(/_/g, ' ')}</td>
                  <td><span className="badge status-active">{c.status.replace(/_/g, ' ')}</span></td>
                  <td>{c.cha_name || '—'}</td>
                  <td>{c.port_of_filing || '—'}</td>
                  <td>{c.customs_direction === 'import' ? (c.ooc_at ? '✅ OOC' : '⏳ OOC') : (c.leo_at ? '✅ LEO' : '⏳ LEO')}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'queries' && (
        <div className="panel" style={{ padding: 0 }}>
          {queries.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><AlertTriangle size={24} /><div><strong>No queries</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Title</th><th>Type</th><th>Severity</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {queries.map((q) => (
                <tr key={q.id}>
                  <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.title}</td>
                  <td><span className="badge">{q.query_type}</span></td>
                  <td style={{ fontWeight: 600, color: q.severity === 'critical' ? '#dc2626' : q.severity === 'high' ? '#ea580c' : 'inherit' }}>{q.severity}</td>
                  <td><span className="badge">{q.status}</span></td>
                  <td style={{ fontSize: '0.78rem' }}>{new Date(q.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}
    </div>
  );
}

export default CustomsPage;
