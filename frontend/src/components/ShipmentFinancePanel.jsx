import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from './States.jsx';

function formatMoney(amount, currency = 'INR') {
  if (amount === null || amount === undefined) return `${currency} 0.00`;
  return `${currency} ${Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function ShipmentFinancePanel({ shipmentId, canWrite }) {
  const [summary, setSummary] = useState(null);
  const [releaseChecks, setReleaseChecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  async function loadAll() {
    setError('');
    setLoading(true);
    try {
      const [summaryResponse, releaseResponse] = await Promise.all([
        api.get(`/shipments/${shipmentId}/finance-summary`),
        api.get(`/shipments/${shipmentId}/release-checks`),
      ]);
      setSummary(summaryResponse.data);
      setReleaseChecks(releaseResponse.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load finance summary');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipmentId]);

  async function refreshRisks() {
    if (!canWrite) return;
    setRefreshing(true);
    try {
      await api.post(`/shipments/${shipmentId}/finance-refresh`);
      await loadAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to refresh finance risks');
    } finally {
      setRefreshing(false);
    }
  }

  async function createInvoiceFromCharge(chargeId) {
    if (!canWrite) return;
    try {
      await api.post(`/finance/invoices/from-charge/${chargeId}`);
      await loadAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create invoice from charge');
    }
  }

  if (loading) return <LoadingState label="Loading finance summary" />;
  if (error)
    return (
      <ErrorState message={error} onRetry={loadAll} />
    );
  if (!summary) return <EmptyState title="Finance summary unavailable" />;

  const currency = summary.currency || 'INR';

  return (
    <section className="page-stack">
      <div className="panel">
        <div className="panel-header">
          <h2>Finance Summary</h2>
          {canWrite && (
            <button
              className="secondary-button"
              type="button"
              onClick={refreshRisks}
              disabled={refreshing}
            >
              <RefreshCw size={16} />
              <span>{refreshing ? 'Refreshing…' : 'Refresh risks'}</span>
            </button>
          )}
        </div>
        <div className="metric-grid">
          <article className="metric-card">
            <span>Receivable total</span>
            <strong>{formatMoney(summary.receivable_total, currency)}</strong>
          </article>
          <article className="metric-card">
            <span>Receivable outstanding</span>
            <strong>{formatMoney(summary.receivable_outstanding, currency)}</strong>
          </article>
          <article className="metric-card">
            <span>Payable total</span>
            <strong>{formatMoney(summary.payable_total, currency)}</strong>
          </article>
          <article className="metric-card">
            <span>Payable outstanding</span>
            <strong>{formatMoney(summary.payable_outstanding, currency)}</strong>
          </article>
          <article className="metric-card">
            <span>Invoices</span>
            <strong>{summary.invoice_count}</strong>
          </article>
          <article className="metric-card">
            <span>Payments</span>
            <strong>{summary.payment_count}</strong>
          </article>
          <article
            className={`metric-card${summary.margin_negative ? ' accent-critical' : ''}`}
          >
            <span>Net P&amp;L</span>
            <strong>
              {formatMoney(summary.pnl_net_profit, summary.pnl_currency || currency)}
            </strong>
          </article>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Active credit holds</h2>
        </div>
        {!summary.active_holds.length ? (
          <EmptyState title="No active credit holds" />
        ) : (
          <ul className="bare-list">
            {summary.active_holds.map((hold) => (
              <li key={hold.id} className="hold-row">
                <span className={`badge severity-${hold.severity}`}>{hold.severity}</span>
                <strong>{hold.hold_type.replace(/_/g, ' ')}</strong>
                <p>{hold.reason || 'No reason provided'}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Release checks</h2>
        </div>
        {!releaseChecks.length ? (
          <EmptyState title="No release checks available" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Message</th>
                  <th>Active holds</th>
                </tr>
              </thead>
              <tbody>
                {releaseChecks.map((check) => (
                  <tr key={check.action_key}>
                    <td>{check.action_key.replace(/_/g, ' ')}</td>
                    <td>
                      <span
                        className={`badge ${check.allowed ? 'status-ok' : 'severity-critical'}`}
                      >
                        {check.allowed ? 'Allowed' : 'Blocked'}
                      </span>
                    </td>
                    <td>{check.message}</td>
                    <td>{check.blocked_by.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Open finance risks</h2>
        </div>
        {!summary.open_risks.length ? (
          <EmptyState title="No open finance risks" />
        ) : (
          <ul className="bare-list">
            {summary.open_risks.map((risk) => (
              <li key={risk.id} className="risk-row">
                <span className={`badge severity-${risk.severity}`}>{risk.severity}</span>
                <strong>{risk.risk_type.replace(/_/g, ' ')}</strong>
                <p>{risk.message}</p>
                {risk.recommended_action && (
                  <em className="muted small">{risk.recommended_action}</em>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default ShipmentFinancePanel;
