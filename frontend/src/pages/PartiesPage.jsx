import { Ban, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';

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
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const canWrite = currentUser && currentUser.role !== 'VIEW_ONLY';
  const canAdmin = currentUser?.role === 'ADMIN';

  async function loadParties() {
    const response = await api.get('/parties', { params: includeInactive ? { include_inactive: true } : {} });
    setParties(response.data);
  }

  useEffect(() => {
    api.get('/auth/me').then((response) => setCurrentUser(response.data)).catch(() => setCurrentUser(null));
  }, []);

  useEffect(() => {
    loadParties().catch((err) => setError(err.response?.data?.detail || 'Unable to load parties'));
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

  async function deleteParty(party) {
    if (!window.confirm(`Delete ${party.name} permanently? This only works for unused parties.`)) return;
    setError('');
    setNotice('');
    try {
      await api.delete(`/parties/${party.id}`);
      setNotice('Party permanently deleted');
      await loadParties();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete party');
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

      {canWrite && (
        <form className="panel form-grid" onSubmit={handleSubmit}>
          <label>
            Name
            <input required value={form.name} onChange={(event) => updateField('name', event.target.value)} />
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
            <input value={form.contact_person} onChange={(event) => updateField('contact_person', event.target.value)} />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} />
          </label>
          <label>
            Phone
            <input value={form.phone} onChange={(event) => updateField('phone', event.target.value)} />
          </label>
          <label>
            Country
            <input value={form.country} onChange={(event) => updateField('country', event.target.value)} />
          </label>
          <label>
            GSTIN
            <input value={form.gstin} onChange={(event) => updateField('gstin', event.target.value)} />
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              <Plus size={18} />
              <span>Create Party</span>
            </button>
          </div>
          {error && <p className="error-text span-2">{error}</p>}
          {notice && <p className="success-text span-2">{notice}</p>}
        </form>
      )}

      {!canWrite && error && <p className="error-text">{error}</p>}
      {!canWrite && notice && <p className="success-text">{notice}</p>}

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
                  <td>{party.name}</td>
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
                            <Ban size={17} />
                            <span>Deactivate Party</span>
                          </button>
                        ) : (
                          <button className="secondary-button" type="button" onClick={() => reactivateParty(party)}>
                            <RotateCcw size={17} />
                            <span>Reactivate Party</span>
                          </button>
                        )}
                        <button className="secondary-button danger-text" type="button" onClick={() => deleteParty(party)}>
                          <Trash2 size={17} />
                          <span>Delete Permanently</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {!parties.length && (
                <tr>
                  <td colSpan="9">No parties yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default PartiesPage;
