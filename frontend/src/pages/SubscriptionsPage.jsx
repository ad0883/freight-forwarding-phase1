import { Activity, AlertTriangle, Calendar, CheckCircle2, ChevronRight, CreditCard, Info, Plus, Receipt, Search, ShieldAlert, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const STATUS_COLORS = {
  trial: 'var(--color-primary)',
  active: 'var(--color-success)',
  past_due: 'var(--color-warning)',
  suspended: 'var(--color-danger)',
  cancelled: 'var(--color-border)',
  expired: 'var(--color-border)',
  manual_override: 'var(--color-primary)',
  internal: 'var(--color-primary)',
};

function formatDate(dateString) {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function SubscriptionsPage() {
  const [currentUser] = useState(() => { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [events, setEvents] = useState([]);
  
  // Modals / Forms
  const [assigningPlan, setAssigningPlan] = useState(null);
  const [editingStatus, setEditingStatus] = useState(false);
  const [extendingTrial, setExtendingTrial] = useState(false);

  useEffect(() => {
    loadData();
  }, [currentUser]);

  async function loadData() {
    if (currentUser?.role !== 'ADMIN' && currentUser?.role !== 'ORG_ADMIN') {
      setError('Access restricted. Subscription management is available only to Admin users.');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError('');
    try {
      const [plansRes, subRes] = await Promise.all([
        api.get('/subscriptions/plans'),
        api.get(`/subscriptions/organizations/${currentUser.organization_id}`),
      ]);
      setPlans(plansRes.data);
      setSubscription(subRes.data);
      
      const eventsRes = await api.get(`/subscriptions/organizations/${currentUser.organization_id}/events`);
      setEvents(eventsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  }

  async function handleAssignPlan(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      plan_id: assigningPlan.id,
      status: fd.get('status'),
      billing_mode: fd.get('billing_mode'),
      notes: fd.get('notes'),
    };
    if (fd.get('trial_end_date')) data.trial_end_date = fd.get('trial_end_date');
    if (fd.get('billing_contact_name')) data.billing_contact_name = fd.get('billing_contact_name');
    if (fd.get('billing_contact_email')) data.billing_contact_email = fd.get('billing_contact_email');
    if (fd.get('manual_payment_reference')) data.manual_payment_reference = fd.get('manual_payment_reference');

    try {
      await api.post(`/subscriptions/organizations/${currentUser.organization_id}/assign-plan`, data);
      setAssigningPlan(null);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to assign plan');
    }
  }

  async function handleStatusChange(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api.patch(`/subscriptions/${subscription.id}/status`, {
        status: fd.get('status'),
        note: fd.get('note'),
      });
      setEditingStatus(false);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to change status');
    }
  }

  async function handleExtendTrial(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api.post(`/subscriptions/${subscription.id}/extend-trial`, {
        trial_ends_at: fd.get('trial_ends_at'),
        note: fd.get('note'),
      });
      setExtendingTrial(false);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to extend trial');
    }
  }

  if (loading) return <LoadingState label="Loading subscriptions data" />;
  if (error && currentUser?.role !== 'ADMIN' && currentUser?.role !== 'ORG_ADMIN') {
    return (
      <div className="page-stack">
        <div className="page-header"><div><h1>Subscriptions</h1></div></div>
        <div className="state-box empty-state"><ShieldAlert size={32} /><strong>Access Denied</strong><p>{error}</p></div>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin / Advanced</p>
          <h1>Subscriptions</h1>
        </div>
      </div>
      <p className="page-helper">Manage organization subscription plan, trial periods, and view billing events.</p>
      
      {error && <ErrorState message={error} onRetry={loadData} />}

      {/* Current Subscription Card */}
      {subscription && (
        <section className="card">
          <div className="card-header">
            <h3>Current Subscription</h3>
            <span className="badge" style={{ backgroundColor: STATUS_COLORS[subscription.subscription_status] || 'var(--color-border)', color: '#fff' }}>
              {subscription.subscription_status.toUpperCase()}
            </span>
          </div>
          <div className="card-body">
            <div className="grid-2-col" style={{ gap: '1.5rem', marginBottom: '1.5rem' }}>
              <div>
                <p className="eyebrow">Plan Details</p>
                <div style={{ marginTop: '0.5rem' }}>
                  <strong>{subscription.plan?.name || 'Unknown Plan'}</strong> ({subscription.plan?.plan_key})<br />
                  <span className="muted">Billing Mode: {subscription.billing_mode}</span><br />
                  <span className="muted">Started: {formatDate(subscription.started_at)}</span>
                </div>
              </div>
              <div>
                <p className="eyebrow">Trial / Period</p>
                <div style={{ marginTop: '0.5rem' }}>
                  <span className="muted">Trial Ends:</span> <strong>{formatDate(subscription.trial_ends_at)}</strong><br />
                  <span className="muted">Current Period:</span> {formatDate(subscription.current_period_start)} to {formatDate(subscription.current_period_end)}
                </div>
              </div>
              <div>
                <p className="eyebrow">Billing Contact</p>
                <div style={{ marginTop: '0.5rem' }}>
                  {subscription.billing_contact_name || 'No name'} <br/>
                  <span className="muted">{subscription.billing_contact_email || 'No email'}</span>
                </div>
              </div>
              <div>
                <p className="eyebrow">Reference</p>
                <div style={{ marginTop: '0.5rem' }}>
                  {subscription.manual_payment_reference || 'None'}<br/>
                  <span className="muted">Last updated: {formatDate(subscription.updated_at)}</span>
                </div>
              </div>
            </div>
            
            <div className="button-group" style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
              <button className="secondary-button" type="button" onClick={() => setEditingStatus(true)}>Change Status</button>
              <button className="secondary-button" type="button" onClick={() => setExtendingTrial(true)}>Extend Trial</button>
            </div>
          </div>
        </section>
      )}

      {/* Available Plans */}
      <section>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Available Plans</h2>
        <div className="grid-3-col">
          {plans.map(plan => (
            <article key={plan.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="card-body" style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h3 style={{ fontSize: '1.1rem', margin: 0 }}>{plan.name}</h3>
                  {subscription?.plan_id === plan.id && <CheckCircle2 size={18} color="var(--color-success)" />}
                </div>
                <p className="muted" style={{ fontSize: '0.85rem', marginTop: '0.5rem', minHeight: '40px' }}>{plan.description}</p>
                <div style={{ margin: '1rem 0' }}>
                  <span className="badge">{plan.billing_period}</span>
                  {plan.base_price_amount && <span className="badge" style={{ marginLeft: '0.5rem' }}>{plan.currency} {plan.base_price_amount}</span>}
                  {!plan.is_public && <span className="badge priority-low" style={{ marginLeft: '0.5rem' }}>Internal</span>}
                </div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.85rem', color: 'var(--color-text-light)' }}>
                  {plan.features.slice(0, 5).map(f => (
                    <li key={f.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                      <CheckCircle2 size={12} color="var(--color-primary)" /> {f.feature_label}
                    </li>
                  ))}
                  {plan.features.length > 5 && <li className="muted">+{plan.features.length - 5} more...</li>}
                </ul>
              </div>
              <div className="card-body" style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem', paddingBottom: '1rem' }}>
                <button 
                  className="primary-button" 
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => setAssigningPlan(plan)}
                  disabled={subscription?.plan_id === plan.id}
                >
                  {subscription?.plan_id === plan.id ? 'Current Plan' : 'Assign to Organization'}
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Subscription Events */}
      <section>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Event Log</h2>
        {events.length === 0 ? (
          <EmptyState title="No events" description="No subscription changes recorded yet." icon={<Activity />} />
        ) : (
          <div className="table-responsive card">
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Event</th>
                  <th>Summary</th>
                  <th>Status Change</th>
                  <th>User</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td className="muted" style={{ whiteSpace: 'nowrap' }}>{formatDate(ev.created_at)}</td>
                    <td><span className="badge">{ev.event_type}</span></td>
                    <td>{ev.safe_summary}</td>
                    <td>
                      {ev.old_status && ev.new_status ? (
                        <span className="muted" style={{ fontSize: '0.8rem' }}>{ev.old_status} &rarr; {ev.new_status}</span>
                      ) : '-'}
                    </td>
                    <td>{ev.created_by_name || 'System'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Modals */}
      {assigningPlan && (
        <div className="modal-backdrop">
          <form className="modal-content" onSubmit={handleAssignPlan}>
            <div className="modal-header">
              <h2>Assign Plan: {assigningPlan.name}</h2>
              <button type="button" className="icon-button" onClick={() => setAssigningPlan(null)}><XCircle size={20} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Status</label>
                <select name="status" className="form-input" required defaultValue="active">
                  <option value="trial">Trial</option>
                  <option value="active">Active</option>
                  <option value="internal">Internal</option>
                  <option value="manual_override">Manual Override</option>
                </select>
              </div>
              <div className="form-group">
                <label>Billing Mode</label>
                <select name="billing_mode" className="form-input" required defaultValue="manual">
                  <option value="manual">Manual</option>
                  <option value="free_trial">Free Trial</option>
                  <option value="offline_invoice">Offline Invoice</option>
                  <option value="internal">Internal</option>
                </select>
              </div>
              <div className="grid-2-col" style={{ gap: '1rem' }}>
                <div className="form-group">
                  <label>Trial End Date (Optional)</label>
                  <input type="date" name="trial_end_date" className="form-input" />
                </div>
                <div className="form-group">
                  <label>Manual Reference (Optional)</label>
                  <input type="text" name="manual_payment_reference" className="form-input" placeholder="e.g. INV-2026-001" />
                </div>
              </div>
              <div className="grid-2-col" style={{ gap: '1rem' }}>
                <div className="form-group">
                  <label>Billing Contact Name</label>
                  <input type="text" name="billing_contact_name" className="form-input" defaultValue={subscription?.billing_contact_name || ''} />
                </div>
                <div className="form-group">
                  <label>Billing Contact Email</label>
                  <input type="email" name="billing_contact_email" className="form-input" defaultValue={subscription?.billing_contact_email || ''} />
                </div>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea name="notes" className="form-input" rows="2" placeholder="Reason for assignment..."></textarea>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="secondary-button" onClick={() => setAssigningPlan(null)}>Cancel</button>
              <button type="submit" className="primary-button">Confirm Assignment</button>
            </div>
          </form>
        </div>
      )}

      {editingStatus && (
        <div className="modal-backdrop">
          <form className="modal-content" onSubmit={handleStatusChange}>
            <div className="modal-header">
              <h2>Change Subscription Status</h2>
              <button type="button" className="icon-button" onClick={() => setEditingStatus(false)}><XCircle size={20} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>New Status</label>
                <select name="status" className="form-input" required defaultValue={subscription.subscription_status}>
                  <option value="trial">Trial</option>
                  <option value="active">Active</option>
                  <option value="past_due">Past Due</option>
                  <option value="suspended">Suspended</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="expired">Expired</option>
                  <option value="manual_override">Manual Override</option>
                  <option value="internal">Internal</option>
                </select>
              </div>
              <div className="form-group">
                <label>Note (Optional)</label>
                <input type="text" name="note" className="form-input" placeholder="Reason for change..." />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="secondary-button" onClick={() => setEditingStatus(false)}>Cancel</button>
              <button type="submit" className="primary-button">Save Changes</button>
            </div>
          </form>
        </div>
      )}

      {extendingTrial && (
        <div className="modal-backdrop">
          <form className="modal-content" onSubmit={handleExtendTrial}>
            <div className="modal-header">
              <h2>Extend Trial</h2>
              <button type="button" className="icon-button" onClick={() => setExtendingTrial(false)}><XCircle size={20} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>New Trial End Date</label>
                <input type="date" name="trial_ends_at" className="form-input" required 
                  defaultValue={subscription.trial_ends_at ? new Date(subscription.trial_ends_at).toISOString().split('T')[0] : ''} />
              </div>
              <div className="form-group">
                <label>Note (Optional)</label>
                <input type="text" name="note" className="form-input" placeholder="Reason for extension..." />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="secondary-button" onClick={() => setExtendingTrial(false)}>Cancel</button>
              <button type="submit" className="primary-button">Extend</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default SubscriptionsPage;
