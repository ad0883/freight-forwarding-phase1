import { Ban, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ConfirmDialog, EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const initialParty = {
  name: '',
  type: 'exporter',
  contact_person: '',
  email: '',
  phone: '',
  country: '',
  gstin: '',
};

function PartiesPage() {
  const [parties, setParties] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [form, setForm] = useState(initialParty);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);
  const canWrite = currentUser && currentUser.role !== 'VIEW_ONLY';
  const canAdmin = currentUser?.role === 'ADMIN';

  async function loadParties() {
    setLoading(true);
    try {
      const response = await api.get('/parties', { params: includeInactive ? { include_inactive: true } : {} });
      setParties(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load parties');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    api.get('/auth/me').then((response) => setCurrentUser(response.data)).catch(() => setCurrentUser(null));
  }, []);

  useEffect(() => {
    loadParties();
  }, [includeInactive]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, value === '' ? null : value])
      );
      await api.post('/parties', payload);
      setForm(initialParty);
      setNotice('Party created');
      await loadParties();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create party');
    }
  }

  async function deactivateParty(party) {
    const reason = window.prompt(`Reason for deactivating ${party.name}`, '');
    if (reason === null) return;
    setError('');
    setNotice('');
    try {
      await api.patch(`/parties/${party.id}/deactivate`, { reason: reason || null });
      setNotice('Party deactivated');
      await loadParties();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to deactivate party');
    }
  }

  async function reactivateParty(party) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/parties/${party.id}/reactivate`);
      setNotice('Party reactivated');
      await loadParties();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to reactivate party');
    }
  }

  async function deleteParty() {
    if (!confirmAction) return;
    setError('');
    setNotice('');
    try {
      await api.delete(`/parties/${confirmAction.id}`);
      setNotice('Party permanently deleted');
      setConfirmAction(null);
      await loadParties();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete party');
      setConfirmAction(null);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Directory</p>
          <h1>Parties</h1>
        </div>
      </div>

      <ErrorState message={error} />
      {notice && <p className="success-text">{notice}</p>}

      {canWrite && (
        <form className="panel form-grid" onSubmit={handleSubmit}>
          <div className="panel-header span-2 no-margin">
            <h2>New Party</h2>
          </div>
          <label>
            Name <span style={{ color: 'var(--color-danger)' }}>*</span>
            <input required value={form.name} onChange={(event) => updateField('name', event.target.value)} placeholder="Company name" />
          </label>
          <label>
            Type
            <select value={form.type} onChange={(event) => updateField('type', event.target.value)}>
              <option value="exporter">exporter</option>
              <option value="importer">importer</option>
              <option value="cha">cha</option>
              <option value="overseas_ff">overseas_ff</option>
              <option value="line">line</option>
              <option value="courier">courier</option>
              <option value="buyer">buyer</option>
              <option value="other">other</option>
            </select>
          </label>
          <label>
            Contact Person
            <input value={form.contact_person} onChange={(event) => updateField('contact_person', event.target.value)} placeholder="Full name" />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} placeholder="email@example.com" />
          </label>
          <label>
            Phone
            <input value={form.phone} onChange={(event) => updateField('phone', event.target.value)} placeholder="+91 ..." />
          </label>
          <label>
            Country
            <input value={form.country} onChange={(event) => updateField('country', event.target.value)} placeholder="Country" />
          </label>
          <label>
            GSTIN
            <input value={form.gstin} onChange={(event) => updateField('gstin', event.target.value)} placeholder="22AAAAA0000A1Z5" />
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              <Plus size={18} />
              <span>Create Party</span>
            </button>
          </div>
        </form>
      )}

      <section className="panel">
        <div className="panel-header">
          <h2>Party Directory</h2>
          <label className="checkbox-label compact-toggle">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
            />
            Include Inactive
          </label>
        </div>
        {loading ? (
          <LoadingState label="Loading parties..." />
        ) : !parties.length ? (
          <EmptyState title="No parties yet" detail="Create your first party above." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Contact</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Country</th>
                  <th>GSTIN</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {parties.map((party) => (
                  <tr key={party.id}>
                    <td><strong>{party.name}</strong></td>
                    <td>
                      <span className={`badge ${party.is_active ? 'status-active' : 'state-inactive'}`}>
                        {party.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>{party.type}</td>
                    <td>{party.contact_person || '-'}</td>
                    <td>{party.email || '-'}</td>
                    <td>{party.phone || '-'}</td>
                    <td>{party.country || '-'}</td>
                    <td>{party.gstin || '-'}</td>
                    <td>
                      {canAdmin && (
                        <div className="row-actions">
                          {party.is_active ? (
                            <button className="secondary-button" type="button" onClick={() => deactivateParty(party)}>
                              <Ban size={16} />
                              <span>Deactivate</span>
                            </button>
                          ) : (
                            <button className="secondary-button" type="button" onClick={() => reactivateParty(party)}>
                              <RotateCcw size={16} />
                              <span>Reactivate</span>
                            </button>
                          )}
                          <button className="secondary-button danger-text" type="button" onClick={() => setConfirmAction(party)}>
                            <Trash2 size={16} />
                            <span>Delete</span>
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={Boolean(confirmAction)}
        title="Delete Party Permanently"
        message={`Delete ${confirmAction?.name} permanently? This only works for unused parties and cannot be undone.`}
        confirmLabel="Delete Permanently"
        danger
        onCancel={() => setConfirmAction(null)}
        onConfirm={deleteParty}
      />
    </div>
  );
}

export default PartiesPage;
