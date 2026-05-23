import { Ban, CheckCircle2, Edit3, ExternalLink, Plus, RotateCcw, Save, ToggleRight } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api/client.js';

const exportStatuses = [
  'Booking Received',
  'Container Booked',
  'SI Submitted',
  'VGM Filed',
  'BL Draft Received',
  'BL Approved',
  'Final BL Received',
  'Docs Collected',
  'Docs Dispatched',
  'Overseas Coordinated',
  'Freight Invoiced',
  'Vessel Sailed',
  'Completed',
];

const importStatuses = [
  'Pre-Alert Received',
  'ETA Tracking Active',
  'IGM Filed',
  'Freight Invoice Received',
  'BL Surrender Confirmed',
  'DO Received',
  'DO Handed to CHA',
  'Clearance In Progress',
  'Container Delivered',
  'Freight Collected',
  'Completed',
];

const emptyFollowup = {
  party_id: '',
  channel: 'email',
  summary: '',
  next_action: '',
  status: 'open',
  date: new Date().toISOString().slice(0, 10),
};

const chargeTypeOptions = [
  ['ocean_freight', 'Ocean Freight'],
  ['do_charges', 'DO Charges'],
  ['bl_charges', 'BL Charges'],
  ['hbl_charges', 'HBL Charges'],
  ['liner_charges', 'Liner Charges'],
  ['clearance_charges', 'Clearance Charges'],
  ['courier_charges', 'Courier Charges'],
  ['agent_charges', 'Agent Charges'],
  ['demurrage', 'Demurrage'],
  ['documentation', 'Documentation'],
  ['handling', 'Handling'],
  ['transport', 'Transport'],
  ['other', 'Other'],
];

const chargeTypeLabels = Object.fromEntries(chargeTypeOptions);

const chargeStatusOptions = {
  payable: ['pending', 'paid', 'cancelled'],
  receivable: ['pending', 'received', 'cancelled'],
};

function emptyChargeForm() {
  return {
    charge_type: 'ocean_freight',
    direction: 'receivable',
    amount: '',
    currency: 'INR',
    party_id: '',
    status: 'pending',
    invoice_no: '',
    date: new Date().toISOString().slice(0, 10),
    notes: '',
  };
}

function InfoItem({ label, value }) {
  return (
    <div className="info-item">
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </div>
  );
}

function formatMoney(amount, currency = 'INR') {
  return `${currency} ${Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function cleanNullableForm(form) {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => {
      if (value === '') return [key, null];
      if (key === 'party_id') return [key, value ? Number(value) : null];
      return [key, value];
    })
  );
}

function ShipmentDetailPage() {
  const { id } = useParams();
  const [shipment, setShipment] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [bl, setBl] = useState(null);
  const [demurrage, setDemurrage] = useState(null);
  const [followups, setFollowups] = useState([]);
  const [charges, setCharges] = useState([]);
  const [pnl, setPnl] = useState(null);
  const [parties, setParties] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [followupForm, setFollowupForm] = useState(emptyFollowup);
  const [chargeForm, setChargeForm] = useState(emptyChargeForm());
  const [editingChargeId, setEditingChargeId] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const canWrite = currentUser && currentUser.role !== 'VIEW_ONLY';
  const workflowStatuses = useMemo(
    () => (shipment?.type === 'export' ? exportStatuses : importStatuses),
    [shipment?.type]
  );

  async function loadFinance() {
    const [chargesResponse, pnlResponse] = await Promise.all([
      api.get(`/shipments/${id}/charges`),
      api.get(`/shipments/${id}/pnl`),
    ]);
    setCharges(chargesResponse.data);
    setPnl(pnlResponse.data);
  }

  async function loadAll() {
    const [
      meResponse,
      shipmentResponse,
      documentsResponse,
      tasksResponse,
      blResponse,
      demurrageResponse,
      followupsResponse,
      partiesResponse,
      chargesResponse,
      pnlResponse,
    ] =
      await Promise.all([
        api.get('/auth/me'),
        api.get(`/shipments/${id}`),
        api.get(`/documents/shipment/${id}`),
        api.get('/tasks', { params: { shipment_id: id } }),
        api.get(`/shipments/${id}/bl`),
        api.get(`/shipments/${id}/demurrage`),
        api.get(`/shipments/${id}/followups`),
        api.get('/parties'),
        api.get(`/shipments/${id}/charges`),
        api.get(`/shipments/${id}/pnl`),
      ]);
    setCurrentUser(meResponse.data);
    setShipment(shipmentResponse.data);
    setWorkflowStatus(shipmentResponse.data.status);
    setDocuments(documentsResponse.data);
    setTasks(tasksResponse.data);
    setBl(blResponse.data);
    setDemurrage(demurrageResponse.data);
    setFollowups(followupsResponse.data);
    setParties(partiesResponse.data);
    setCharges(chargesResponse.data);
    setPnl(pnlResponse.data);
  }

  useEffect(() => {
    loadAll().catch((err) => setError(err.response?.data?.detail || 'Unable to load shipment'));
  }, [id]);

  function updateDocument(documentId, field, value) {
    setDocuments((current) =>
      current.map((document) => (document.id === documentId ? { ...document, [field]: value } : document))
    );
  }

  async function saveDocument(document) {
    setNotice('');
    try {
      const response = await api.patch(`/documents/${document.id}`, {
        status: document.status,
        file_url: document.file_url || null,
        notes: document.notes || null,
        is_required: document.is_required,
      });
      setDocuments((current) => current.map((item) => (item.id === document.id ? response.data : item)));
      setNotice('Document saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save document');
    }
  }

  async function toggleTask(task) {
    setNotice('');
    try {
      const response = await api.patch(`/tasks/${task.id}`, {
        status: task.status === 'open' ? 'done' : 'open',
      });
      setTasks((current) => current.map((item) => (item.id === task.id ? response.data : item)));
      setNotice('Task updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update task');
    }
  }

  async function saveWorkflowStatus() {
    setNotice('');
    try {
      const response = await api.patch(`/shipments/${id}/workflow-status`, { status: workflowStatus });
      setShipment(response.data);
      await loadAll();
      setNotice('Workflow status updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update workflow status');
    }
  }

  async function saveBl() {
    setNotice('');
    try {
      const response = await api.patch(`/shipments/${id}/bl`, cleanNullableForm(bl));
      setBl(response.data);
      setNotice('BL management saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save BL management');
    }
  }

  async function saveDemurrage() {
    setNotice('');
    try {
      const payload = cleanNullableForm(demurrage);
      const response = await api.patch(`/shipments/${id}/demurrage`, {
        free_days: payload.free_days === null ? null : Number(payload.free_days),
        start_date: payload.start_date,
        rate_per_day: payload.rate_per_day === null ? null : Number(payload.rate_per_day),
        currency: payload.currency,
        alert_at_days: payload.alert_at_days === null ? null : Number(payload.alert_at_days),
        container_count: payload.container_count === null ? null : Number(payload.container_count),
      });
      setDemurrage(response.data);
      setNotice('Demurrage saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save demurrage');
    }
  }

  async function createFollowup(event) {
    event.preventDefault();
    setNotice('');
    try {
      const response = await api.post(`/shipments/${id}/followups`, cleanNullableForm(followupForm));
      setFollowups((current) => [response.data, ...current]);
      setFollowupForm(emptyFollowup);
      setNotice('Follow-up logged');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create follow-up');
    }
  }

  async function updateFollowupStatus(followup, status) {
    setNotice('');
    try {
      const response = await api.patch(`/followups/${followup.id}`, { status });
      setFollowups((current) => current.map((item) => (item.id === followup.id ? response.data : item)));
      setNotice('Follow-up updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update follow-up');
    }
  }

  async function deleteFollowup(followupId) {
    setNotice('');
    try {
      await api.delete(`/followups/${followupId}`);
      setFollowups((current) => current.filter((item) => item.id !== followupId));
      setNotice('Follow-up deleted');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete follow-up');
    }
  }

  function updateChargeForm(field, value) {
    setChargeForm((current) => {
      const next = { ...current, [field]: value };
      if (field === 'direction' && !chargeStatusOptions[value].includes(next.status)) {
        next.status = 'pending';
      }
      return next;
    });
  }

  function resetChargeForm() {
    setChargeForm(emptyChargeForm());
    setEditingChargeId(null);
  }

  function editCharge(charge) {
    setEditingChargeId(charge.id);
    setChargeForm({
      charge_type: charge.charge_type,
      direction: charge.direction,
      amount: charge.amount,
      currency: charge.currency || 'INR',
      party_id: charge.party_id || '',
      status: charge.status,
      invoice_no: charge.invoice_no || '',
      date: charge.date || '',
      notes: charge.notes || '',
    });
    setActiveTab('charges');
  }

  function chargePayload() {
    return {
      shipment_id: Number(id),
      charge_type: chargeForm.charge_type,
      direction: chargeForm.direction,
      amount: Number(chargeForm.amount),
      currency: chargeForm.currency || 'INR',
      party_id: chargeForm.party_id ? Number(chargeForm.party_id) : null,
      status: chargeForm.status,
      invoice_no: chargeForm.invoice_no || null,
      date: chargeForm.date || null,
      notes: chargeForm.notes || null,
    };
  }

  async function saveCharge(event) {
    event.preventDefault();
    setNotice('');
    if (chargeForm.amount === '' || Number(chargeForm.amount) < 0) {
      setError('Charge amount is required and cannot be negative');
      return;
    }
    try {
      if (editingChargeId) {
        await api.patch(`/charges/${editingChargeId}`, chargePayload());
        setNotice('Charge updated');
      } else {
        await api.post(`/shipments/${id}/charges`, chargePayload());
        setNotice('Charge added');
      }
      resetChargeForm();
      await loadFinance();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save charge');
    }
  }

  async function updateChargeStatus(charge, status) {
    setNotice('');
    try {
      await api.patch(`/charges/${charge.id}`, { status });
      await loadFinance();
      setNotice(status === 'cancelled' ? 'Charge cancelled' : 'Charge status updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update charge');
    }
  }

  async function cancelCharge(charge) {
    setNotice('');
    try {
      await api.delete(`/charges/${charge.id}`);
      await loadFinance();
      setNotice('Charge cancelled');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to cancel charge');
    }
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!shipment) {
    return <p className="muted">Loading shipment...</p>;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">{shipment.type}</p>
          <h1>{shipment.shipment_code}</h1>
        </div>
        <span className="badge status-active">{shipment.status}</span>
      </div>
      {notice && <p className="success-text">{notice}</p>}

      <div className="tabs" role="tablist">
        {['overview', 'documents', 'tasks', 'bl', 'followups', 'demurrage', 'charges'].map((tab) => (
          <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
            {tab === 'bl' ? 'BL Management' : tab === 'followups' ? 'Follow-up Log' : tab[0].toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <section className="panel form-grid">
          <label>
            Current Status
            <select value={workflowStatus} disabled={!canWrite} onChange={(event) => setWorkflowStatus(event.target.value)}>
              {workflowStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <div className="form-actions">
            {canWrite && (
              <button className="primary-button" type="button" onClick={saveWorkflowStatus}>
                <Save size={18} />
                <span>Update Status</span>
              </button>
            )}
          </div>
          <div className="span-2 info-grid">
            <InfoItem label="Shipment Code" value={shipment.shipment_code} />
            <InfoItem label="Type" value={shipment.type} />
            <InfoItem label="Status" value={shipment.status} />
            <InfoItem label="Shipping Line" value={shipment.shipping_line} />
            <InfoItem label="Vessel" value={shipment.vessel_name} />
            <InfoItem label="Voyage No" value={shipment.voyage_no} />
            <InfoItem label="Origin Port" value={shipment.origin_port} />
            <InfoItem label="Destination Port" value={shipment.dest_port} />
            <InfoItem label="Container No" value={shipment.container_no} />
            <InfoItem label="Container Type" value={shipment.container_type} />
            <InfoItem label="ETD" value={shipment.etd} />
            <InfoItem label="ETA" value={shipment.eta} />
            <InfoItem label="Booking Ref" value={shipment.booking_ref} />
            <InfoItem label="Commodity" value={shipment.commodity} />
          </div>
        </section>
      )}

      {activeTab === 'documents' && (
        <section className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Document Type</th>
                  <th>Status</th>
                  <th>File Link</th>
                  <th>Notes</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id}>
                    <td>{document.doc_type}</td>
                    <td>
                      <select
                        value={document.status}
                        disabled={!canWrite}
                        onChange={(event) => updateDocument(document.id, 'status', event.target.value)}
                      >
                        <option value="pending">pending</option>
                        <option value="received">received</option>
                        <option value="sent">sent</option>
                        <option value="approved">approved</option>
                        <option value="not_required">not_required</option>
                      </select>
                    </td>
                    <td className="link-cell">
                      <input
                        value={document.file_url || ''}
                        disabled={!canWrite}
                        onChange={(event) => updateDocument(document.id, 'file_url', event.target.value)}
                        placeholder="Paste Google Drive URL"
                      />
                      {document.file_url && (
                        <a href={document.file_url} target="_blank" rel="noreferrer" title="Open link">
                          <ExternalLink size={17} />
                        </a>
                      )}
                    </td>
                    <td>
                      <input
                        value={document.notes || ''}
                        disabled={!canWrite}
                        onChange={(event) => updateDocument(document.id, 'notes', event.target.value)}
                        placeholder="Notes"
                      />
                    </td>
                    <td>
                      {canWrite && (
                        <button className="icon-button" type="button" onClick={() => saveDocument(document)} title="Save">
                          <Save size={17} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === 'tasks' && (
        <section className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Task Title</th>
                  <th>Description</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td>{task.title}</td>
                    <td>{task.description || '-'}</td>
                    <td>
                      <span className={`badge priority-${task.priority}`}>{task.priority}</span>
                    </td>
                    <td>
                      <span className={`badge task-${task.status}`}>{task.status}</span>
                    </td>
                    <td>
                      {canWrite && (
                        <button className="secondary-button" type="button" onClick={() => toggleTask(task)}>
                          {task.status === 'open' ? <ToggleRight size={17} /> : <RotateCcw size={17} />}
                          <span>{task.status === 'open' ? 'Mark done' : 'Reopen'}</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {!tasks.length && (
                  <tr>
                    <td colSpan="5">No tasks for this shipment.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === 'bl' && bl && (
        <section className="panel form-grid">
          <label>
            BL Type
            <select value={bl.bl_type || 'Ocean'} disabled={!canWrite} onChange={(event) => setBl({ ...bl, bl_type: event.target.value })}>
              {['OBL', 'HBL', 'Surrender', 'Telex', 'Seaway', 'Ocean'].map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Draft Received
            <input type="date" value={bl.draft_received || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, draft_received: event.target.value })} />
          </label>
          <label>
            Approval Date
            <input type="date" value={bl.approval_date || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, approval_date: event.target.value })} />
          </label>
          <label>
            Final BL Date
            <input type="date" value={bl.final_bl_date || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, final_bl_date: event.target.value })} />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={bl.surrender_done} disabled={!canWrite} onChange={(event) => setBl({ ...bl, surrender_done: event.target.checked })} />
            Surrender Done
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={bl.telex_release} disabled={!canWrite} onChange={(event) => setBl({ ...bl, telex_release: event.target.checked })} />
            Telex Release
          </label>
          <label className="span-2">
            Final BL Google Drive Link
            <input value={bl.file_url || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, file_url: event.target.value })} />
          </label>
          <label className="span-2">
            Corrections
            <textarea value={bl.corrections || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, corrections: event.target.value })} />
          </label>
          {canWrite && (
            <div className="form-actions span-2">
              <button className="primary-button" type="button" onClick={saveBl}>
                <Save size={18} />
                <span>Save BL</span>
              </button>
            </div>
          )}
        </section>
      )}

      {activeTab === 'demurrage' && (
        <section className="panel">
          {shipment.type === 'export' ? (
            <p className="muted">Demurrage tracking is mainly applicable to import shipments.</p>
          ) : (
            demurrage && (
              <div className="page-stack">
                <div className="form-grid">
                  <label>
                    Free Days Allowed
                    <input type="number" value={demurrage.free_days ?? ''} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, free_days: event.target.value })} />
                  </label>
                  <label>
                    Start Date
                    <input type="date" value={demurrage.start_date || ''} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, start_date: event.target.value })} />
                  </label>
                  <label>
                    Rate Per Day
                    <input type="number" value={demurrage.rate_per_day ?? ''} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, rate_per_day: event.target.value })} />
                  </label>
                  <label>
                    Currency
                    <input value={demurrage.currency || 'INR'} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, currency: event.target.value })} />
                  </label>
                  <label>
                    Alert At Days
                    <input type="number" value={demurrage.alert_at_days ?? 3} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, alert_at_days: event.target.value })} />
                  </label>
                  <label>
                    Container Count
                    <input type="number" value={demurrage.container_count ?? 1} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, container_count: event.target.value })} />
                  </label>
                  {canWrite && (
                    <div className="form-actions span-2">
                      <button className="primary-button" type="button" onClick={saveDemurrage}>
                        <Save size={18} />
                        <span>Save Demurrage</span>
                      </button>
                    </div>
                  )}
                </div>
                <div
                  className={`demurrage-summary ${
                    demurrage.is_demurrage_running
                      ? 'critical'
                      : demurrage.days_remaining !== null && demurrage.days_remaining <= demurrage.alert_at_days
                        ? 'warning'
                        : ''
                  }`}
                >
                  <InfoItem label="Free Days End Date" value={demurrage.free_days_end_date} />
                  <InfoItem label="Days Used" value={demurrage.days_used} />
                  <InfoItem label="Days Remaining" value={demurrage.days_remaining ?? '-'} />
                  <InfoItem label="Status" value={demurrage.status} />
                  <InfoItem label="Demurrage Running" value={demurrage.is_demurrage_running ? 'Yes' : 'No'} />
                  <InfoItem label="Total Due" value={`${demurrage.currency} ${demurrage.total_demurrage_due}`} />
                </div>
              </div>
            )
          )}
        </section>
      )}

      {activeTab === 'followups' && (
        <section className="page-stack">
          {canWrite && (
            <form className="panel form-grid" onSubmit={createFollowup}>
              <label>
                Party
                <select value={followupForm.party_id} onChange={(event) => setFollowupForm({ ...followupForm, party_id: event.target.value })}>
                  <option value="">No party</option>
                  {parties.map((party) => (
                    <option key={party.id} value={party.id}>
                      {party.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Channel
                <select value={followupForm.channel} onChange={(event) => setFollowupForm({ ...followupForm, channel: event.target.value })}>
                  <option value="email">email</option>
                  <option value="call">call</option>
                  <option value="whatsapp">whatsapp</option>
                  <option value="meeting">meeting</option>
                </select>
              </label>
              <label>
                Date
                <input type="date" value={followupForm.date} onChange={(event) => setFollowupForm({ ...followupForm, date: event.target.value })} />
              </label>
              <label>
                Status
                <select value={followupForm.status} onChange={(event) => setFollowupForm({ ...followupForm, status: event.target.value })}>
                  <option value="open">open</option>
                  <option value="closed">closed</option>
                </select>
              </label>
              <label className="span-2">
                Summary
                <textarea required value={followupForm.summary} onChange={(event) => setFollowupForm({ ...followupForm, summary: event.target.value })} />
              </label>
              <label className="span-2">
                Next Action
                <textarea value={followupForm.next_action} onChange={(event) => setFollowupForm({ ...followupForm, next_action: event.target.value })} />
              </label>
              <div className="form-actions span-2">
                <button className="primary-button" type="submit">
                  <Plus size={18} />
                  <span>Add Follow-up</span>
                </button>
              </div>
            </form>
          )}
          <div className="panel table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Party</th>
                  <th>Channel</th>
                  <th>Summary</th>
                  <th>Next Action</th>
                  <th>Status</th>
                  <th>Logged By</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {followups.map((followup) => (
                  <tr key={followup.id}>
                    <td>{followup.date}</td>
                    <td>{followup.party?.name || '-'}</td>
                    <td>{followup.channel}</td>
                    <td>{followup.summary}</td>
                    <td>{followup.next_action || '-'}</td>
                    <td>
                      <span className={`badge task-${followup.status === 'open' ? 'open' : 'done'}`}>{followup.status}</span>
                    </td>
                    <td>{followup.logger?.name || followup.logged_by}</td>
                    <td>
                      {canWrite && (
                        <div className="row-actions">
                          <button className="secondary-button" type="button" onClick={() => updateFollowupStatus(followup, followup.status === 'open' ? 'closed' : 'open')}>
                            {followup.status === 'open' ? 'Close' : 'Reopen'}
                          </button>
                          <button className="icon-button danger" type="button" onClick={() => deleteFollowup(followup.id)} title="Delete">
                            <Trash2 size={17} />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {!followups.length && (
                  <tr>
                    <td colSpan="8">No follow-ups yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === 'charges' && (
        <section className="page-stack">
          {pnl && (
            <>
              <div className="metric-grid finance-grid">
                <article className="metric-card">
                  <span>Total Receivable</span>
                  <strong>{formatMoney(pnl.total_receivable, pnl.currency)}</strong>
                </article>
                <article className="metric-card">
                  <span>Total Payable</span>
                  <strong>{formatMoney(pnl.total_payable, pnl.currency)}</strong>
                </article>
                <article className={`metric-card ${Number(pnl.net_profit) < 0 ? 'critical-card' : 'success-card'}`}>
                  <span>Net Profit</span>
                  <strong>{formatMoney(pnl.net_profit, pnl.currency)}</strong>
                </article>
                <article className="metric-card warning-card">
                  <span>Pending Receivable</span>
                  <strong>{formatMoney(pnl.pending_receivable, pnl.currency)}</strong>
                </article>
                <article className="metric-card info-card">
                  <span>Pending Payable</span>
                  <strong>{formatMoney(pnl.pending_payable, pnl.currency)}</strong>
                </article>
              </div>
              {pnl.multiple_currencies && (
                <p className="finance-note">Multiple currencies are present. Totals are not converted automatically.</p>
              )}
            </>
          )}

          {canWrite && (
            <form className="panel form-grid" onSubmit={saveCharge}>
              <label>
                Charge Type
                <select value={chargeForm.charge_type} onChange={(event) => updateChargeForm('charge_type', event.target.value)}>
                  {chargeTypeOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Direction
                <select value={chargeForm.direction} onChange={(event) => updateChargeForm('direction', event.target.value)}>
                  <option value="receivable">receivable</option>
                  <option value="payable">payable</option>
                </select>
              </label>
              <label>
                Amount
                <input
                  required
                  min="0"
                  step="0.01"
                  type="number"
                  value={chargeForm.amount}
                  onChange={(event) => updateChargeForm('amount', event.target.value)}
                />
              </label>
              <label>
                Currency
                <input value={chargeForm.currency} onChange={(event) => updateChargeForm('currency', event.target.value.toUpperCase())} />
              </label>
              <label>
                Party
                <select value={chargeForm.party_id} onChange={(event) => updateChargeForm('party_id', event.target.value)}>
                  <option value="">No party</option>
                  {parties.map((party) => (
                    <option key={party.id} value={party.id}>
                      {party.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Status
                <select value={chargeForm.status} onChange={(event) => updateChargeForm('status', event.target.value)}>
                  {chargeStatusOptions[chargeForm.direction].map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Invoice No
                <input value={chargeForm.invoice_no} onChange={(event) => updateChargeForm('invoice_no', event.target.value)} />
              </label>
              <label>
                Date
                <input type="date" value={chargeForm.date} onChange={(event) => updateChargeForm('date', event.target.value)} />
              </label>
              <label className="span-2">
                Notes
                <textarea value={chargeForm.notes} onChange={(event) => updateChargeForm('notes', event.target.value)} />
              </label>
              <div className="form-actions span-2">
                {editingChargeId && (
                  <button className="secondary-button" type="button" onClick={resetChargeForm}>
                    Cancel Edit
                  </button>
                )}
                <button className="primary-button" type="submit">
                  <Save size={18} />
                  <span>{editingChargeId ? 'Save Charge' : 'Add Charge'}</span>
                </button>
              </div>
            </form>
          )}

          <div className="panel table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Direction</th>
                  <th>Amount</th>
                  <th>Party</th>
                  <th>Status</th>
                  <th>Invoice No</th>
                  <th>Date</th>
                  <th>Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {charges.map((charge) => (
                  <tr key={charge.id}>
                    <td>{chargeTypeLabels[charge.charge_type] || charge.charge_type}</td>
                    <td>{charge.direction}</td>
                    <td>{formatMoney(charge.amount, charge.currency)}</td>
                    <td>{charge.party_name || '-'}</td>
                    <td>
                      <span className={`badge charge-${charge.status}`}>{charge.status}</span>
                    </td>
                    <td>{charge.invoice_no || '-'}</td>
                    <td>{charge.date || '-'}</td>
                    <td>{charge.notes || '-'}</td>
                    <td>
                      {canWrite && charge.status !== 'cancelled' && (
                        <div className="row-actions">
                          <button className="icon-button" type="button" onClick={() => editCharge(charge)} title="Edit charge">
                            <Edit3 size={17} />
                          </button>
                          {charge.direction === 'payable' && charge.status !== 'paid' && (
                            <button className="secondary-button" type="button" onClick={() => updateChargeStatus(charge, 'paid')}>
                              <CheckCircle2 size={17} />
                              <span>Mark Paid</span>
                            </button>
                          )}
                          {charge.direction === 'receivable' && charge.status !== 'received' && (
                            <button className="secondary-button" type="button" onClick={() => updateChargeStatus(charge, 'received')}>
                              <CheckCircle2 size={17} />
                              <span>Mark Received</span>
                            </button>
                          )}
                          <button className="secondary-button danger-text" type="button" onClick={() => cancelCharge(charge)}>
                            <Ban size={17} />
                            <span>Cancel Charge</span>
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {!charges.length && (
                  <tr>
                    <td colSpan="9">No charges for this shipment.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default ShipmentDetailPage;
