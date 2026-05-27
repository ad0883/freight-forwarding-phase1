import { Bell, FileText, MessageSquare, Ship } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function PortalPage() {
  const [dashboard, setDashboard] = useState(null);
  const [shipments, setShipments] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('shipments');
  const [selectedShipment, setSelectedShipment] = useState(null);
  const [noPortal, setNoPortal] = useState(false);

  async function load() {
    setLoading(true); setError('');
    try {
      const dRes = await api.get('/portal/dashboard');
      setDashboard(dRes.data);
      const sRes = await api.get('/portal/shipments');
      setShipments(sRes.data);
      const rRes = await api.get('/portal/requests');
      setRequests(rRes.data);
    } catch (err) {
      if (err.response?.status === 403) { setNoPortal(true); }
      else { setError(err.response?.data?.detail || 'Failed to load portal'); }
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  if (noPortal) return (
    <div className="page-stack">
      <div className="page-header"><div><h1>Customer Portal</h1></div></div>
      <div className="state-box"><div><strong>No portal account</strong><p>Your account does not have portal access. Contact your freight forwarder to get access.</p></div></div>
    </div>
  );

  if (error) return <ErrorState message={error} />;
  if (loading) return <LoadingState />;

  return (
    <div className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Customer Portal</p><h1>My Shipments</h1></div></div>

      {dashboard && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(3, minmax(140px, 1fr))' }}>
          <article className="metric-card"><Ship size={20} /><span>Active Shipments</span><strong>{dashboard.active_shipments}</strong></article>
          <article className="metric-card info-card"><MessageSquare size={20} /><span>Open Requests</span><strong>{dashboard.open_requests}</strong></article>
          <article className="metric-card"><Bell size={20} /><span>Notifications</span><strong>{dashboard.unread_notifications}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)' }}>
        {['shipments', 'requests', 'notifications'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t}</button>
        ))}
      </nav>

      {tab === 'shipments' && (
        <div className="panel" style={{ padding: 0 }}>
          {shipments.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Ship size={24} /><div><strong>No shipments</strong><p>No shipments assigned to your account yet.</p></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Code</th><th>Type</th><th>Status</th><th>Origin</th><th>Destination</th><th>ETD</th><th>ETA</th></tr></thead><tbody>
              {shipments.map((s) => (
                <tr key={s.id} className="clickable-row" onClick={() => setSelectedShipment(s)}>
                  <td><strong>{s.shipment_code}</strong></td>
                  <td><span className="badge">{s.type}</span></td>
                  <td><span className="badge status-active">{s.workflow_state || s.status}</span></td>
                  <td>{s.origin_port}</td><td>{s.destination_port}</td>
                  <td>{s.etd || '—'}</td><td>{s.eta || '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'requests' && (
        <div className="panel" style={{ padding: 0 }}>
          {requests.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><MessageSquare size={24} /><div><strong>No requests</strong><p>You have not raised any requests yet.</p></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>#</th><th>Title</th><th>Type</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {requests.map((r) => (
                <tr key={r.id}><td><code style={{ fontSize: '0.72rem' }}>{r.request_number}</code></td><td>{r.title}</td><td><span className="badge">{r.request_type}</span></td><td><span className="badge">{r.status}</span></td><td style={{ fontSize: '0.78rem' }}>{new Date(r.created_at).toLocaleDateString()}</td></tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'notifications' && (
        <div className="panel" style={{ padding: '1rem' }}>
          <p className="muted">Notifications will appear here when your shipments are updated.</p>
        </div>
      )}
    </div>
  );
}

export default PortalPage;
