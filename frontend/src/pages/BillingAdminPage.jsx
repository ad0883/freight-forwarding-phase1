import React, { useState, useEffect } from 'react';
import { CreditCard, DollarSign, AlertCircle, FileText, Plus, CheckCircle, Clock } from 'lucide-react';
import api from '../api/client.js';

const BillingAdminPage = () => {
  const [summary, setSummary] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [records, setRecords] = useState([]);
  const [events, setEvents] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Organization selector for admin (in a real app this would be a proper dropdown)
  // For S6 placeholder, we assume we're looking at organization_id = 1
  const [selectedOrgId, setSelectedOrgId] = useState(1);

  useEffect(() => {
    fetchBillingData();
  }, [selectedOrgId]);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      const [sumRes, dashRes, recRes, evRes, profRes] = await Promise.all([
        api.get('/billing/summary'),
        api.get('/billing/dashboard'),
        api.get(`/billing/organizations/${selectedOrgId}/records`),
        api.get(`/billing/organizations/${selectedOrgId}/events`),
        api.get(`/billing/organizations/${selectedOrgId}/profile`)
      ]);
      
      setSummary(sumRes.data);
      setDashboard(dashRes.data);
      setRecords(recRes.data);
      setEvents(evRes.data);
      setProfile(profRes.data);
      setError(null);
    } catch (err) {
      console.error(err);
      if (err.response && err.response.status === 403) {
        setError("Billing management is restricted to Admin users.");
      } else {
        setError("Failed to load billing data.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleMarkPaid = async (recordId) => {
    try {
      await api.post(`/billing/records/${recordId}/mark-paid`, {
        payment_reference: 'MANUAL_' + Date.now(),
        note: 'Marked paid from admin dashboard'
      });
      fetchBillingData();
    } catch (err) {
      console.error(err);
      alert('Failed to mark as paid');
    }
  };

  const handleMarkOverdue = async (recordId) => {
    try {
      await api.post(`/billing/records/${recordId}/mark-overdue`, {
        note: 'Marked overdue from admin dashboard'
      });
      fetchBillingData();
    } catch (err) {
      console.error(err);
      alert('Failed to mark as overdue');
    }
  };

  if (loading) {
    return <div className="p-6">Loading billing data...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-500">{error}</div>;
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Billing Administration</h1>
      </div>

      {/* Dashboard Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div className="card">
          <div className="card-body p-6 flex items-center space-x-4" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
            <div className="p-3 bg-red-100 text-red-600 rounded-lg" style={{ padding: '0.75rem', backgroundColor: '#fee2e2', color: '#dc2626', borderRadius: '0.5rem' }}>
              <DollarSign className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500 eyebrow">Platform Outstanding</p>
              <h3 className="text-2xl font-bold text-slate-800" style={{ fontSize: '1.5rem', margin: 0 }}>${dashboard?.total_outstanding_platform?.toFixed(2) || '0.00'}</h3>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-body p-6 flex items-center space-x-4" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
            <div className="p-3 bg-green-100 text-green-600 rounded-lg" style={{ padding: '0.75rem', backgroundColor: '#dcfce7', color: '#16a34a', borderRadius: '0.5rem' }}>
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500 eyebrow">Platform Paid (Month)</p>
              <h3 className="text-2xl font-bold text-slate-800" style={{ fontSize: '1.5rem', margin: 0 }}>${dashboard?.total_paid_this_month_platform?.toFixed(2) || '0.00'}</h3>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body p-6 flex items-center space-x-4" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
            <div className="p-3 bg-orange-100 text-orange-600 rounded-lg" style={{ padding: '0.75rem', backgroundColor: '#ffedd5', color: '#ea580c', borderRadius: '0.5rem' }}>
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500 eyebrow">Overdue Records</p>
              <h3 className="text-2xl font-bold text-slate-800" style={{ fontSize: '1.5rem', margin: 0 }}>{dashboard?.overdue_records_count || 0}</h3>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body p-6 flex items-center space-x-4" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
            <div className="p-3 bg-slate-100 text-slate-600 rounded-lg" style={{ padding: '0.75rem', backgroundColor: '#f1f5f9', color: '#475569', borderRadius: '0.5rem' }}>
              <CreditCard className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500 eyebrow">Manual Review</p>
              <h3 className="text-2xl font-bold text-slate-800" style={{ fontSize: '1.5rem', margin: 0 }}>{dashboard?.manual_review_records_count || 0}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2-col" style={{ gap: '1.5rem', marginTop: '1.5rem' }}>
        {/* Profile */}
        <div className="card lg:col-span-1">
          <div className="card-header">
            <h3>Organization Profile (Org #{selectedOrgId})</h3>
          </div>
          <div className="card-body">
            {profile ? (
              <div className="space-y-4 text-sm" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <span className="font-medium text-slate-500 eyebrow">Contact:</span>
                  <p className="text-slate-800">{profile.billing_contact_name || 'Not set'} ({profile.billing_contact_email || 'No email'})</p>
                </div>
                <div>
                  <span className="font-medium text-slate-500 eyebrow">Cycle:</span>
                  <p className="text-slate-800 capitalize">{profile.billing_cycle}</p>
                </div>
                <div>
                  <span className="font-medium text-slate-500 eyebrow">Currency:</span>
                  <p className="text-slate-800">{profile.billing_currency}</p>
                </div>
                <div>
                  <span className="font-medium text-slate-500 eyebrow">Payment Terms:</span>
                  <p className="text-slate-800">Net {profile.payment_terms_days}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No profile found.</p>
            )}
          </div>
        </div>

        {/* Records */}
        <div className="card lg:col-span-2">
          <div className="card-header flex flex-row items-center justify-between">
            <h3>Manual Billing Records</h3>
          </div>
          <div className="card-body">
            <div className="table-responsive">
              <table className="table w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-slate-500 border-b">
                  <tr>
                    <th className="py-3 px-4 font-medium">Ref / Type</th>
                    <th className="py-3 px-4 font-medium">Status</th>
                    <th className="py-3 px-4 font-medium">Amount</th>
                    <th className="py-3 px-4 font-medium">Due Date</th>
                    <th className="py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {records.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="py-4 text-center text-slate-500">No records found.</td>
                    </tr>
                  ) : (
                    records.map(record => (
                      <tr key={record.id} className="hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <div className="font-medium text-slate-800">{record.invoice_reference || 'Draft'}</div>
                          <div className="text-xs text-slate-500 capitalize">{record.record_type}</div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`badge capitalize
                            ${record.payment_status === 'paid' ? 'bg-green-100 text-green-800' : 
                              record.payment_status === 'overdue' ? 'bg-red-100 text-red-800' : 
                              'bg-yellow-100 text-yellow-800'}`}>
                            {record.payment_status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="text-slate-800 font-medium">
                            {record.currency} {record.amount_due}
                          </div>
                          {record.amount_paid > 0 && (
                            <div className="text-xs text-green-600">Paid: {record.amount_paid}</div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {record.due_date ? new Date(record.due_date).toLocaleDateString() : '-'}
                        </td>
                        <td className="py-3 px-4 flex gap-2">
                          {record.payment_status !== 'paid' && (
                            <button onClick={() => handleMarkPaid(record.id)} className="secondary-button" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                              Mark Paid
                            </button>
                          )}
                          {record.payment_status !== 'overdue' && record.payment_status !== 'paid' && (
                            <button onClick={() => handleMarkOverdue(record.id)} className="secondary-button" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--color-danger)', borderColor: 'var(--color-danger)' }}>
                              Mark Overdue
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Events */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <h3>Billing Events</h3>
        </div>
        <div className="card-body">
          <div className="space-y-4" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {events.length === 0 ? (
              <p className="text-sm text-slate-500">No events found.</p>
            ) : (
              events.slice(0, 10).map(event => (
                <div key={event.id} className="flex items-start space-x-3 text-sm" style={{ display: 'flex', gap: '0.75rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '1rem' }}>
                  <div className="mt-1">
                    <Clock className="w-4 h-4 text-slate-400" />
                  </div>
                  <div>
                    <p className="text-slate-800 font-medium" style={{ margin: 0 }}>{event.event_type.replace(/_/g, ' ').toUpperCase()}</p>
                    <p className="text-slate-600" style={{ margin: '0.25rem 0' }}>{event.safe_summary}</p>
                    <p className="text-xs text-slate-400 muted mt-1">
                      {new Date(event.created_at).toLocaleString()} by {event.created_by_name || 'System'}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BillingAdminPage;
