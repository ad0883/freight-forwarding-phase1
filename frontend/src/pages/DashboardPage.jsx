import { AlertTriangle, CheckCircle2, Clock, Ship, Timer } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';

function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const dashboardResponse = await api.get('/shipments/dashboard');
        setSummary(dashboardResponse.data);
        setAlerts(dashboardResponse.data.recent_alerts || []);
      } catch (err) {
        setError(err.response?.data?.detail || 'Unable to load dashboard');
      }
    }
    load();
  }, []);

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!summary) {
    return <p className="muted">Loading dashboard...</p>;
  }

  const cards = [
    { label: 'Live Shipments', value: summary.live_shipments, icon: Ship },
    { label: 'Pending Tasks', value: summary.pending_tasks, icon: Clock },
    { label: 'Future Bookings', value: summary.future_bookings, icon: Timer },
    { label: 'Alerts Today', value: summary.alerts_today, icon: AlertTriangle },
    { label: 'Completed Shipments This Month', value: summary.completed_this_month, icon: CheckCircle2 },
  ];

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Dashboard</h1>
        </div>
        <Link className="primary-button" to="/shipments/new">
          New Shipment
        </Link>
      </div>

      <section className="metric-grid">
        {cards.map(({ label, value, icon: Icon }) => (
          <article className="metric-card" key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="split-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Recent Shipments</h2>
            <Link to="/shipments">View all</Link>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Shipment ID</th>
                  <th>Type</th>
                  <th>Shipping Line</th>
                  <th>ETD</th>
                  <th>ETA</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {summary.shipments.map((shipment) => (
                  <tr key={shipment.id}>
                    <td>
                      <Link to={`/shipments/${shipment.id}`}>{shipment.shipment_code}</Link>
                    </td>
                    <td>{shipment.type}</td>
                    <td>{shipment.shipping_line || '-'}</td>
                    <td>{shipment.etd || '-'}</td>
                    <td>{shipment.eta || '-'}</td>
                    <td>
                      <span className={`badge status-${shipment.status}`}>{shipment.status}</span>
                    </td>
                  </tr>
                ))}
                {!summary.shipments.length && (
                  <tr>
                    <td colSpan="6">No shipments yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="page-stack">
          <div className="panel">
            <div className="panel-header">
              <h2>Pending Tasks</h2>
              <Link to="/tasks">View all</Link>
            </div>
            <div className="alert-list">
              {(summary.urgent_tasks || []).map((task) => (
                <article className="alert-item" key={task.id}>
                  <span className={`badge priority-${task.priority}`}>{task.priority}</span>
                  <strong>{task.title}</strong>
                  <p>Shipment #{task.shipment_id}{task.due_date ? ` due ${task.due_date}` : ''}</p>
                </article>
              ))}
              {!(summary.urgent_tasks || []).length && <p className="muted">No pending tasks.</p>}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Recent Critical Alerts</h2>
            </div>
            <div className="alert-list">
              {alerts.map((alert) => (
                <article className="alert-item" key={alert.id}>
                  <span className={`badge priority-${alert.priority}`}>{alert.priority}</span>
                  <strong>{alert.title}</strong>
                  <p>{alert.message}</p>
                </article>
              ))}
              {!alerts.length && <p className="muted">No critical alerts.</p>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
