import { ExternalLink, RotateCcw, Save, ToggleRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api/client.js';

function InfoItem({ label, value }) {
  return (
    <div className="info-item">
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </div>
  );
}

function ShipmentDetailPage() {
  const { id } = useParams();
  const [shipment, setShipment] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function loadAll() {
    const [shipmentResponse, documentsResponse, tasksResponse] = await Promise.all([
      api.get(`/shipments/${id}`),
      api.get(`/documents/shipment/${id}`),
      api.get('/tasks', { params: { shipment_id: id } }),
    ]);
    setShipment(shipmentResponse.data);
    setDocuments(documentsResponse.data);
    setTasks(tasksResponse.data);
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
        <span className={`badge status-${shipment.status}`}>{shipment.status}</span>
      </div>
      {notice && <p className="success-text">{notice}</p>}

      <div className="tabs" role="tablist">
        <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>
          Overview
        </button>
        <button className={activeTab === 'documents' ? 'active' : ''} onClick={() => setActiveTab('documents')}>
          Documents
        </button>
        <button className={activeTab === 'tasks' ? 'active' : ''} onClick={() => setActiveTab('tasks')}>
          Tasks
        </button>
      </div>

      {activeTab === 'overview' && (
        <section className="panel info-grid">
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
                        onChange={(event) => updateDocument(document.id, 'notes', event.target.value)}
                        placeholder="Notes"
                      />
                    </td>
                    <td>
                      <button className="icon-button" type="button" onClick={() => saveDocument(document)} title="Save">
                        <Save size={17} />
                      </button>
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
                      <button className="secondary-button" type="button" onClick={() => toggleTask(task)}>
                        {task.status === 'open' ? <ToggleRight size={17} /> : <RotateCcw size={17} />}
                        <span>{task.status === 'open' ? 'Mark done' : 'Reopen'}</span>
                      </button>
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
    </div>
  );
}

export default ShipmentDetailPage;
