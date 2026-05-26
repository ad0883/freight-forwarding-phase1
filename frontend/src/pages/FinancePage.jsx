import { Banknote, ListChecks, RefreshCw, Wallet } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

function formatMoney(amount, currency = 'INR') {
  if (amount === null || amount === undefined) return `${currency} 0.00`;
  return `${currency} ${Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'receivables', label: 'Receivables' },
  { key: 'payables', label: 'Payables' },
  { key: 'payments', label: 'Payments' },
  { key: 'credit', label: 'Credit Control' },
  { key: 'holds', label: 'Holds' },
  { key: 'aging', label: 'Aging' },
  { key: 'fx', label: 'FX Rates' },
  { key: 'risks', label: 'Risks' },
];

function StatCard({ icon: Icon, label, value, accent }) {
  return (
    <article className={`metric-card${accent ? ` accent-${accent}` : ''}`}>
      {Icon ? <Icon size={18} /> : null}
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function OverviewSection({ overview }) {
  if (!overview) return null;
  const currency = overview.currency || 'INR';
  return (
    <div className="finance-overview">
      <div className="metric-grid">
        <StatCard
          icon={Wallet}
          label="Receivable outstanding"
          value={formatMoney(overview.receivable_total, currency)}
        />
        <StatCard
          icon={Wallet}
          label="Receivable overdue"
          value={formatMoney(overview.receivable_overdue, currency)}
          accent={Number(overview.receivable_overdue) > 0 ? 'critical' : ''}
        />
        <StatCard
          icon={Banknote}
          label="Payable outstanding"
          value={formatMoney(overview.payable_total, currency)}
        />
        <StatCard
          icon={Banknote}
          label="Payable overdue"
          value={formatMoney(overview.payable_overdue, currency)}
          accent={Number(overview.payable_overdue) > 0 ? 'warning' : ''}
        />
        <StatCard
          icon={ListChecks}
          label="Active credit holds"
          value={overview.active_holds}
          accent={overview.active_holds > 0 ? 'critical' : ''}
        />
        <StatCard
          icon={ListChecks}
          label="Open finance risks"
          value={overview.open_risks}
          accent={overview.open_risks > 0 ? 'warning' : ''}
        />
        <StatCard
          icon={Banknote}
          label="Unallocated payments"
          value={formatMoney(overview.unallocated_payments, currency)}
        />
        <StatCard
          icon={ListChecks}
          label="Negative-margin shipments"
          value={overview.negative_margin_shipments}
          accent={overview.negative_margin_shipments > 0 ? 'warning' : ''}
        />
      </div>
    </div>
  );
}

function InvoicesTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No invoices yet" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Invoice</th>
            <th>Shipment</th>
            <th>Party</th>
            <th>Status</th>
            <th>Total</th>
            <th>Outstanding</th>
            <th>Due</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((invoice) => (
            <tr key={invoice.id}>
              <td>
                <strong>{invoice.invoice_number || `#${invoice.id}`}</strong>
                <div className="muted small">{invoice.invoice_type}</div>
              </td>
              <td>{invoice.shipment_code || '-'}</td>
              <td>{invoice.party_name || '-'}</td>
              <td>
                <span className={`badge status-${invoice.status}`}>{invoice.status}</span>
              </td>
              <td>{formatMoney(invoice.total_amount, invoice.currency)}</td>
              <td>
                <strong>{formatMoney(invoice.outstanding_amount, invoice.currency)}</strong>
              </td>
              <td>{invoice.due_date || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PaymentsTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No payments recorded" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Party</th>
            <th>Type</th>
            <th>Direction</th>
            <th>Amount</th>
            <th>Unallocated</th>
            <th>Status</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((payment) => (
            <tr key={payment.id}>
              <td>{payment.reference_number || `#${payment.id}`}</td>
              <td>{payment.party_name || '-'}</td>
              <td>{payment.payment_type}</td>
              <td>{payment.direction}</td>
              <td>{formatMoney(payment.amount, payment.currency)}</td>
              <td>{formatMoney(payment.unallocated_amount, payment.currency)}</td>
              <td>
                <span className={`badge status-${payment.status}`}>{payment.status}</span>
              </td>
              <td>{payment.payment_date || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CreditProfilesTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No credit profiles configured yet" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Party</th>
            <th>Credit limit</th>
            <th>Outstanding</th>
            <th>Overdue</th>
            <th>Available</th>
            <th>Days</th>
            <th>Holds</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((profile) => (
            <tr key={profile.id}>
              <td>
                <strong>{profile.party_name || `Party #${profile.party_id}`}</strong>
              </td>
              <td>{formatMoney(profile.credit_limit, profile.credit_currency)}</td>
              <td>{formatMoney(profile.current_outstanding, profile.credit_currency)}</td>
              <td>{formatMoney(profile.overdue_amount, profile.credit_currency)}</td>
              <td>{formatMoney(profile.available_credit, profile.credit_currency)}</td>
              <td>{profile.credit_days}</td>
              <td>{profile.active_holds}</td>
              <td>
                <span className={`badge status-${profile.status}`}>{profile.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HoldsTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No active credit holds" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Type</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Party</th>
            <th>Shipment</th>
            <th>Outstanding</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((hold) => (
            <tr key={hold.id}>
              <td>{hold.hold_type.replace(/_/g, ' ')}</td>
              <td>
                <span className={`badge severity-${hold.severity}`}>{hold.severity}</span>
              </td>
              <td>{hold.status}</td>
              <td>{hold.party_name || '-'}</td>
              <td>{hold.shipment_code || '-'}</td>
              <td>{hold.current_outstanding ?? '-'}</td>
              <td>{hold.reason || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AgingSection({ summary }) {
  if (!summary) {
    return <LoadingState label="Loading aging" />;
  }
  const buckets = summary.buckets || {};
  const currency = summary.currency || 'INR';
  return (
    <div className="finance-aging">
      <div className="metric-grid">
        <StatCard label="Not due" value={formatMoney(buckets.not_due, currency)} />
        <StatCard label="0-30 days" value={formatMoney(buckets.bucket_0_30, currency)} />
        <StatCard label="31-60 days" value={formatMoney(buckets.bucket_31_60, currency)} />
        <StatCard label="61-90 days" value={formatMoney(buckets.bucket_61_90, currency)} />
        <StatCard label="90+ days" value={formatMoney(buckets.bucket_90_plus, currency)} />
        <StatCard
          label="Total outstanding"
          value={formatMoney(buckets.total_outstanding, currency)}
        />
      </div>
      <div className="table-wrap" style={{ marginTop: '1rem' }}>
        <table>
          <thead>
            <tr>
              <th>Party</th>
              <th>Total</th>
              <th>Overdue</th>
              <th>0-30</th>
              <th>31-60</th>
              <th>61-90</th>
              <th>90+</th>
            </tr>
          </thead>
          <tbody>
            {(summary.parties || []).map((row) => (
              <tr key={row.party_id || 'unassigned'}>
                <td>
                  <strong>{row.party_name || 'Unassigned'}</strong>
                </td>
                <td>{formatMoney(row.buckets.total_outstanding, currency)}</td>
                <td>{formatMoney(row.buckets.overdue_amount, currency)}</td>
                <td>{formatMoney(row.buckets.bucket_0_30, currency)}</td>
                <td>{formatMoney(row.buckets.bucket_31_60, currency)}</td>
                <td>{formatMoney(row.buckets.bucket_61_90, currency)}</td>
                <td>{formatMoney(row.buckets.bucket_90_plus, currency)}</td>
              </tr>
            ))}
            {!(summary.parties || []).length && (
              <tr>
                <td colSpan={7} className="muted">
                  No party-level aging data yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FxTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No FX rates recorded" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Pair</th>
            <th>Rate</th>
            <th>Source</th>
            <th>Manual</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((rate) => (
            <tr key={rate.id}>
              <td>{rate.rate_date}</td>
              <td>
                {rate.base_currency} → {rate.quote_currency}
              </td>
              <td>{rate.rate}</td>
              <td>{rate.source}</td>
              <td>{rate.is_manual ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RisksTable({ rows }) {
  if (!rows.length) {
    return <EmptyState title="No open finance risks" />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Type</th>
            <th>Severity</th>
            <th>Shipment</th>
            <th>Party</th>
            <th>Message</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((risk) => (
            <tr key={risk.id}>
              <td>{risk.risk_type.replace(/_/g, ' ')}</td>
              <td>
                <span className={`badge severity-${risk.severity}`}>{risk.severity}</span>
              </td>
              <td>{risk.shipment_code || '-'}</td>
              <td>{risk.party_name || '-'}</td>
              <td>{risk.message}</td>
              <td>
                <span className={`badge status-${risk.status}`}>{risk.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FinancePage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [receivables, setReceivables] = useState([]);
  const [payables, setPayables] = useState([]);
  const [payments, setPayments] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [holds, setHolds] = useState([]);
  const [aging, setAging] = useState(null);
  const [agingDirection, setAgingDirection] = useState('receivable');
  const [fxRates, setFxRates] = useState([]);
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadAll() {
    setError('');
    setLoading(true);
    try {
      const [
        overviewResponse,
        receivablesResponse,
        payablesResponse,
        paymentsResponse,
        profilesResponse,
        holdsResponse,
        agingResponse,
        fxResponse,
        risksResponse,
      ] = await Promise.all([
        api.get('/finance/overview'),
        api.get('/finance/invoices', { params: { direction: 'receivable', limit: 100 } }),
        api.get('/finance/invoices', { params: { direction: 'payable', limit: 100 } }),
        api.get('/finance/payments', { params: { limit: 100 } }),
        api.get('/finance/credit-profiles'),
        api.get('/finance/holds', { params: { status: 'active' } }),
        api.get('/finance/aging', { params: { direction: agingDirection } }),
        api.get('/finance/fx-rates'),
        api.get('/finance/risks', { params: { status: 'open' } }),
      ]);
      setOverview(overviewResponse.data);
      setReceivables(receivablesResponse.data);
      setPayables(payablesResponse.data);
      setPayments(paymentsResponse.data);
      setProfiles(profilesResponse.data);
      setHolds(holdsResponse.data);
      setAging(agingResponse.data);
      setFxRates(fxResponse.data);
      setRisks(risksResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load finance data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshAging(direction) {
    setAgingDirection(direction);
    try {
      const response = await api.get('/finance/aging', { params: { direction } });
      setAging(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load aging');
    }
  }

  if (loading) {
    return <LoadingState label="Loading finance data" />;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Finance + credit control</p>
          <h1>Finance</h1>
        </div>
        <div className="page-header-actions">
          <button className="secondary-button" type="button" onClick={loadAll}>
            <RefreshCw size={16} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <ErrorState message={error} onRetry={loadAll} />

      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`tab${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <section className="panel">
        {activeTab === 'overview' && <OverviewSection overview={overview} />}
        {activeTab === 'receivables' && <InvoicesTable rows={receivables} />}
        {activeTab === 'payables' && <InvoicesTable rows={payables} />}
        {activeTab === 'payments' && <PaymentsTable rows={payments} />}
        {activeTab === 'credit' && <CreditProfilesTable rows={profiles} />}
        {activeTab === 'holds' && <HoldsTable rows={holds} />}
        {activeTab === 'aging' && (
          <div>
            <div className="form-row" style={{ marginBottom: '0.75rem' }}>
              <label>
                Direction
                <select
                  value={agingDirection}
                  onChange={(event) => refreshAging(event.target.value)}
                >
                  <option value="receivable">Receivable</option>
                  <option value="payable">Payable</option>
                </select>
              </label>
            </div>
            <AgingSection summary={aging} />
          </div>
        )}
        {activeTab === 'fx' && <FxTable rows={fxRates} />}
        {activeTab === 'risks' && <RisksTable rows={risks} />}
      </section>
    </div>
  );
}

export default FinancePage;
