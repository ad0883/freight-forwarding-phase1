import { RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

function formatMoney(amount, currency = 'INR') {
  return `${currency} ${Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function PendingTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No pending records" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Shipment Code</th>
            <th>Party</th>
            <th>Amount</th>
            <th>Invoice No</th>
            <th>Date</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.charge_id}>
              <td><strong>{row.shipment_code}</strong></td>
              <td>{row.party_name || '-'}</td>
              <td>{formatMoney(row.amount, row.currency)}</td>
              <td>{row.invoice_no || '-'}</td>
              <td>{row.date || '-'}</td>
              <td>{row.notes || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReportsPage() {
  const today = new Date();
  const [month, setMonth] = useState(String(today.getMonth() + 1));
  const [year, setYear] = useState(String(today.getFullYear()));
  const [monthly, setMonthly] = useState(null);
  const [receivables, setReceivables] = useState([]);
  const [payables, setPayables] = useState([]);
  const [shipmentPnl, setShipmentPnl] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadReports() {
    setError('');
    setLoading(true);
    try {
      const [monthlyResponse, receivablesResponse, payablesResponse, pnlResponse] = await Promise.all([
        api.get('/reports/monthly', { params: { month: Number(month), year: Number(year) } }),
        api.get('/reports/pending-receivables'),
        api.get('/reports/pending-payables'),
        api.get('/reports/shipment-pnl'),
      ]);
      setMonthly(monthlyResponse.data);
      setReceivables(receivablesResponse.data);
      setPayables(payablesResponse.data);
      setShipmentPnl(pnlResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load reports');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Finance</p>
          <h1>Reports</h1>
        </div>
      </div>

      <ErrorState message={error} onRetry={loadReports} />

      <section className="panel form-grid">
        <label>
          Month
          <select value={month} onChange={(event) => setMonth(event.target.value)}>
            {Array.from({ length: 12 }, (_, index) => String(index + 1)).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Year
          <input type="number" min="2000" max="2100" value={year} onChange={(event) => setYear(event.target.value)} />
        </label>
        <div className="form-actions span-2">
          <button className="primary-button" type="button" onClick={loadReports} disabled={loading}>
            <RefreshCw size={18} />
            <span>{loading ? 'Loading...' : 'Refresh'}</span>
          </button>
        </div>
      </section>

      {loading && !monthly ? (
        <LoadingState label="Loading reports..." />
      ) : monthly ? (
        <>
          <section className="metric-grid finance-grid">
            <article className="metric-card">
              <span>Shipments</span>
              <strong>{monthly.shipment_count}</strong>
            </article>
            <article className="metric-card">
              <span>Completed</span>
              <strong>{monthly.completed_shipments}</strong>
            </article>
            <article className="metric-card success-card">
              <span>Total Receivable</span>
              <strong>{formatMoney(monthly.total_receivable, monthly.currency)}</strong>
            </article>
            <article className="metric-card info-card">
              <span>Total Payable</span>
              <strong>{formatMoney(monthly.total_payable, monthly.currency)}</strong>
            </article>
            <article className={`metric-card ${Number(monthly.net_profit) < 0 ? 'critical-card' : 'success-card'}`}>
              <span>Net Profit</span>
              <strong>{formatMoney(monthly.net_profit, monthly.currency)}</strong>
            </article>
          </section>
          {monthly.multiple_currencies && (
            <p className="finance-note">Multiple currencies are present. Totals are not converted automatically.</p>
          )}
        </>
      ) : null}

      <section className="split-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Pending Receivables</h2>
          </div>
          <PendingTable rows={receivables} />
        </div>
        <div className="panel">
          <div className="panel-header">
            <h2>Pending Payables</h2>
          </div>
          <PendingTable rows={payables} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Shipment-wise P&L</h2>
        </div>
        {!shipmentPnl.length ? (
          <EmptyState title="No shipment P&L records yet" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Shipment Code</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Total Receivable</th>
                  <th>Total Payable</th>
                  <th>Net Profit</th>
                  <th>Pending Receivable</th>
                  <th>Pending Payable</th>
                </tr>
              </thead>
              <tbody>
                {shipmentPnl.map((row) => (
                  <tr key={row.shipment_id}>
                    <td><strong>{row.shipment_code}</strong></td>
                    <td>{row.type}</td>
                    <td><span className={`badge status-${row.status}`}>{row.status}</span></td>
                    <td>{formatMoney(row.total_receivable, row.currency)}</td>
                    <td>{formatMoney(row.total_payable, row.currency)}</td>
                    <td style={{ color: Number(row.net_profit) < 0 ? 'var(--color-danger)' : 'var(--color-success)', fontWeight: 600 }}>
                      {formatMoney(row.net_profit, row.currency)}
                    </td>
                    <td>{formatMoney(row.pending_receivable, row.currency)}</td>
                    <td>{formatMoney(row.pending_payable, row.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default ReportsPage;
