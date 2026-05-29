import { AlertTriangle, CheckCircle2, Clock, MapPin, Truck, Package } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function TransportPage() {
  const [summary, setSummary] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [exceptions, setExceptions] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('jobs');

  async function load() {
    setLoading(true); setError('');
    try {
      const [sRes, jRes, eRes, vRes, dRes] = await Promise.all([
        api.get('/transport/summary'),
        api.get('/transport'),
        api.get('/transport/exceptions'),
        api.get('/transport/vehicles'),
        api.get('/transport/drivers'),
      ]);
      setSummary(sRes.data); setJobs(jRes.data); setExceptions(eRes.data);
      setVehicles(vRes.data); setDrivers(dRes.data);
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  if (error) return <ErrorState message={error} />;
  if (loading) return <LoadingState />;

  return (
    <div className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Operations</p><h1>Transport</h1></div></div>
      <p className="page-helper">Schedule pickups, deliveries, and track cargo movement between origin and destination.</p>

      {summary && (
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(6, minmax(100px, 1fr))' }}>
          <article className="metric-card"><Truck size={20} /><span>Active Jobs</span><strong>{summary.total_active}</strong></article>
          <article className="metric-card info-card"><MapPin size={20} /><span>In Transit</span><strong>{summary.in_transit}</strong></article>
          <article className="metric-card critical-card"><AlertTriangle size={20} /><span>Delayed</span><strong>{summary.delayed}</strong></article>
          <article className="metric-card warning-card"><Package size={20} /><span>Empty Return</span><strong>{summary.empty_return_pending}</strong></article>
          <article className="metric-card"><Clock size={20} /><span>Unassigned</span><strong>{summary.unassigned}</strong></article>
          <article className="metric-card"><AlertTriangle size={20} /><span>Exceptions</span><strong>{summary.exceptions_open}</strong></article>
        </div>
      )}

      <nav style={{ display: 'flex', gap: '2px', borderBottom: '2px solid var(--color-border)' }}>
        {['jobs', 'exceptions', 'vehicles', 'drivers'].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: '0.6rem 1rem', border: 'none', background: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent', marginBottom: '-2px', color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: tab === t ? 700 : 500, fontSize: '0.85rem', textTransform: 'capitalize' }}>{t}</button>
        ))}
      </nav>

      {tab === 'jobs' && (
        <div className="panel" style={{ padding: 0 }}>
          {jobs.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Truck size={24} /><div><strong>No transport jobs</strong><p>Create a transport job from a shipment.</p></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Job #</th><th>Shipment</th><th>Type</th><th>Status</th><th>Transporter</th><th>Pickup</th><th>Delivery</th><th>Location</th><th>ETA</th></tr></thead><tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td><code style={{ fontSize: '0.72rem' }}>{j.job_number}</code></td>
                  <td><Link to={`/shipments/${j.shipment_id}`}>#{j.shipment_id}</Link></td>
                  <td><span className="badge">{j.job_type.replace(/_/g, ' ')}</span></td>
                  <td><span className={`badge ${j.status === 'delayed' ? 'status-critical' : j.status === 'in_transit' ? 'status-active' : ''}`}>{j.status.replace(/_/g, ' ')}</span></td>
                  <td>{j.transporter_name || '—'}</td>
                  <td style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.pickup_location || '—'}</td>
                  <td style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.delivery_location || '—'}</td>
                  <td style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.last_location_text || '—'}</td>
                  <td style={{ fontSize: '0.78rem' }}>{j.eta ? new Date(j.eta).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'exceptions' && (
        <div className="panel" style={{ padding: 0 }}>
          {exceptions.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><CheckCircle2 size={24} /><div><strong>No transport exceptions</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Title</th><th>Type</th><th>Severity</th><th>Status</th><th>Delay (min)</th><th>Created</th></tr></thead><tbody>
              {exceptions.map((e) => (
                <tr key={e.id}>
                  <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.title}</td>
                  <td><span className="badge">{e.exception_type.replace(/_/g, ' ')}</span></td>
                  <td style={{ fontWeight: 600, color: e.severity === 'critical' ? '#dc2626' : e.severity === 'high' ? '#ea580c' : 'inherit' }}>{e.severity}</td>
                  <td><span className="badge">{e.status}</span></td>
                  <td>{e.delay_minutes ?? '—'}</td>
                  <td style={{ fontSize: '0.78rem' }}>{new Date(e.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'vehicles' && (
        <div className="panel" style={{ padding: 0 }}>
          {vehicles.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Truck size={24} /><div><strong>No vehicles registered</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Vehicle #</th><th>Type</th><th>Capacity</th><th>Status</th><th>Insurance Until</th></tr></thead><tbody>
              {vehicles.map((v) => (
                <tr key={v.id}>
                  <td><code>{v.vehicle_number}</code></td>
                  <td>{v.vehicle_type.replace(/_/g, ' ')}</td>
                  <td>{v.capacity || '—'}</td>
                  <td><span className={`badge ${v.status === 'active' ? 'status-active' : v.status === 'blacklisted' ? 'status-critical' : ''}`}>{v.status}</span></td>
                  <td style={{ fontSize: '0.78rem' }}>{v.insurance_valid_until ? new Date(v.insurance_valid_until).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}

      {tab === 'drivers' && (
        <div className="panel" style={{ padding: 0 }}>
          {drivers.length === 0 ? (
            <div className="state-box empty-state" style={{ minHeight: '120px', border: 'none' }}><Truck size={24} /><div><strong>No drivers registered</strong></div></div>
          ) : (
            <div className="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>License #</th><th>Status</th><th>License Until</th></tr></thead><tbody>
              {drivers.map((d) => (
                <tr key={d.id}>
                  <td>{d.driver_name}</td>
                  <td>{d.phone || '—'}</td>
                  <td>{d.license_number || '—'}</td>
                  <td><span className={`badge ${d.status === 'active' ? 'status-active' : d.status === 'blacklisted' ? 'status-critical' : ''}`}>{d.status}</span></td>
                  <td style={{ fontSize: '0.78rem' }}>{d.license_valid_until ? new Date(d.license_valid_until).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody></table></div>
          )}
        </div>
      )}
    </div>
  );
}

export default TransportPage;
