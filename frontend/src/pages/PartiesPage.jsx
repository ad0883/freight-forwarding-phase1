import { Plus } from 'lucide-react';
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
  const [form, setForm] = useState(initialParty);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function loadParties() {
    const response = await api.get('/parties');
    setParties(response.data);
  }

  useEffect(() => {
    loadParties().catch((err) => setError(err.response?.data?.detail || 'Unable to load parties'));
  }, []);

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

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Directory</p>
          <h1>Parties</h1>
        </div>
      </div>

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

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Contact</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Country</th>
                <th>GSTIN</th>
              </tr>
            </thead>
            <tbody>
              {parties.map((party) => (
                <tr key={party.id}>
                  <td>{party.name}</td>
                  <td>{party.type}</td>
                  <td>{party.contact_person || '-'}</td>
                  <td>{party.email || '-'}</td>
                  <td>{party.phone || '-'}</td>
                  <td>{party.country || '-'}</td>
                  <td>{party.gstin || '-'}</td>
                </tr>
              ))}
              {!parties.length && (
                <tr>
                  <td colSpan="7">No parties yet.</td>
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
