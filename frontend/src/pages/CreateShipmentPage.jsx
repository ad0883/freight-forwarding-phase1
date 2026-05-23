import { Save } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client.js';

const initialForm = {
  type: 'export',
  exporter_id: '',
  importer_id: '',
  shipping_line: '',
  vessel_name: '',
  voyage_no: '',
  origin_port: '',
  dest_port: '',
  container_no: '',
  container_type: '20GP',
  etd: '',
  eta: '',
  booking_ref: '',
  commodity: '',
};

function cleanPayload(form) {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => {
      if (value === '') return [key, null];
      if (key.endsWith('_id')) return [key, Number(value)];
      return [key, value];
    })
  );
}

function CreateShipmentPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [parties, setParties] = useState([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function loadParties() {
      try {
        const response = await api.get('/parties');
        setParties(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Unable to load parties');
      }
    }
    loadParties();
  }, []);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const response = await api.post('/shipments', cleanPayload(form));
      navigate(`/shipments/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create shipment');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Shipments</p>
          <h1>Create Shipment</h1>
        </div>
      </div>

      <form className="panel form-grid" onSubmit={handleSubmit}>
        <label>
          Type
          <select value={form.type} onChange={(event) => updateField('type', event.target.value)}>
            <option value="export">Export</option>
            <option value="import">Import</option>
          </select>
        </label>
        <label>
          Exporter
          <select value={form.exporter_id} onChange={(event) => updateField('exporter_id', event.target.value)}>
            <option value="">Select exporter</option>
            {parties.map((party) => (
              <option key={party.id} value={party.id}>
                {party.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Importer
          <select value={form.importer_id} onChange={(event) => updateField('importer_id', event.target.value)}>
            <option value="">Select importer</option>
            {parties.map((party) => (
              <option key={party.id} value={party.id}>
                {party.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Shipping Line
          <input value={form.shipping_line} onChange={(event) => updateField('shipping_line', event.target.value)} />
        </label>
        <label>
          Vessel Name
          <input value={form.vessel_name} onChange={(event) => updateField('vessel_name', event.target.value)} />
        </label>
        <label>
          Voyage No
          <input value={form.voyage_no} onChange={(event) => updateField('voyage_no', event.target.value)} />
        </label>
        <label>
          Origin Port
          <input value={form.origin_port} onChange={(event) => updateField('origin_port', event.target.value)} />
        </label>
        <label>
          Destination Port
          <input value={form.dest_port} onChange={(event) => updateField('dest_port', event.target.value)} />
        </label>
        <label>
          Container No
          <input value={form.container_no} onChange={(event) => updateField('container_no', event.target.value)} />
        </label>
        <label>
          Container Type
          <select value={form.container_type} onChange={(event) => updateField('container_type', event.target.value)}>
            <option value="20GP">20GP</option>
            <option value="40GP">40GP</option>
            <option value="40HC">40HC</option>
            <option value="LCL">LCL</option>
          </select>
        </label>
        <label>
          ETD
          <input type="date" value={form.etd} onChange={(event) => updateField('etd', event.target.value)} />
        </label>
        <label>
          ETA
          <input type="date" value={form.eta} onChange={(event) => updateField('eta', event.target.value)} />
        </label>
        <label>
          Booking Ref
          <input value={form.booking_ref} onChange={(event) => updateField('booking_ref', event.target.value)} />
        </label>
        <label className="span-2">
          Commodity
          <textarea value={form.commodity} onChange={(event) => updateField('commodity', event.target.value)} />
        </label>
        {error && <p className="error-text span-2">{error}</p>}
        <div className="form-actions span-2">
          <button className="primary-button" type="submit" disabled={saving}>
            <Save size={18} />
            <span>{saving ? 'Creating...' : 'Create Shipment'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

export default CreateShipmentPage;
