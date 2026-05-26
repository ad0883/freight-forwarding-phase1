import {
  AlertTriangle,
  Box,
  Plus,
  RefreshCcw,
  ShieldAlert,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import api from '../api/client.js';
import { ConfirmDialog, EmptyState, ErrorState, LoadingState } from './States.jsx';

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

const RISK_BADGE = {
  none: 'status-active',
  info: 'priority-info',
  warning: 'priority-warning',
  critical: 'priority-critical',
  running: 'priority-critical',
};

function formatMoney(amount, currency = 'INR') {
  if (amount === null || amount === undefined) return '-';
  const numeric = Number(amount);
  if (Number.isNaN(numeric)) return String(amount);
  return `${currency} ${numeric.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString();
}

function ContainersPanel({ shipmentId, shipmentType }) {
  const [user] = useState(cachedUser);
  const [containers, setContainers] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({
    container_number: '',
    container_size: '',
    container_type: '',
    seal_number: '',
  });
  const [transitionTarget, setTransitionTarget] = useState(null);
  const [eventTarget, setEventTarget] = useState(null);
  const [eventForm, setEventForm] = useState({ event_type: '', event_date: '', description: '' });
  const [transitionForm, setTransitionForm] = useState({ new_status: '', reason: '' });
  const canWrite = user && ['ADMIN', 'STAFF'].includes(user.role);

  async function load() {
    setError('');
    setLoading(true);
    try {
      const [list, allStatuses] = await Promise.all([
        api.get(`/shipments/${shipmentId}/containers`),
        api.get('/containers/statuses'),
      ]);
      setContainers(list.data);
      setStatuses(allStatuses.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load containers');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (shipmentId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipmentId]);

  async function refreshShipmentExposure() {
    setError('');
    setNotice('');
    try {
      await api.post(`/shipments/${shipmentId}/refresh-container-exposure`);
      setNotice('Container exposure refreshed.');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Refresh failed');
    }
  }

  async function refreshContainer(containerId) {
    setError('');
    try {
      await api.post(`/containers/${containerId}/refresh-exposure`);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Refresh failed');
    }
  }

  async function addContainer(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const payload = Object.fromEntries(
        Object.entries(addForm).filter(([, value]) => value !== '')
      );
      await api.post(`/shipments/${shipmentId}/containers`, payload);
      setNotice('Container added.');
      setShowAdd(false);
      setAddForm({ container_number: '', container_size: '', container_type: '', seal_number: '' });
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not add container');
    }
  }

  async function submitTransition(event) {
    event.preventDefault();
    if (!transitionTarget) return;
    setError('');
    setNotice('');
    try {
      await api.post(`/containers/${transitionTarget.id}/transition`, transitionForm);
      setNotice('Container transitioned.');
      setTransitionTarget(null);
      setTransitionForm({ new_status: '', reason: '' });
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Transition failed');
    }
  }

  async function submitEvent(event) {
    event.preventDefault();
    if (!eventTarget) return;
    setError('');
    setNotice('');
    try {
      await api.post(`/containers/${eventTarget.id}/events`, eventForm);
      setNotice('Event added.');
      setEventTarget(null);
      setEventForm({ event_type: '', event_date: '', description: '' });
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Event failed');
    }
  }

  const totalExposure = useMemo(() => {
    let demurrage = 0;
    let detention = 0;
    let currency = 'INR';
    containers.forEach((c) => {
      if (!c.exposure) return;
      currency = c.exposure.currency || currency;
      demurrage += Number(c.exposure.demurrage_estimated_amount || 0);
      detention += Number(c.exposure.detention_estimated_amount || 0);
    });
    return { demurrage, detention, currency };
  }, [containers]);

  return (
    <section className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <h2>Containers ({containers.length})</h2>
          <div className="row-actions">
            <button className="secondary-button" type="button" onClick={refreshShipmentExposure}>
              <RefreshCcw size={15} />
              Refresh exposure
            </button>
            {canWrite && (
              <button className="primary-button" type="button" onClick={() => setShowAdd(true)}>
                <Plus size={15} />
                Add container
              </button>
            )}
          </div>
        </div>
        <ErrorState message={error} onRetry={load} />
        {notice && <p className="success-text">{notice}</p>}
        <div className="dashboard-summary-strip">
          <div>
            <Box size={18} />
            <span>Containers</span>
            <strong>{containers.length}</strong>
          </div>
          <div>
            <ShieldAlert size={18} />
            <span>Demurrage estimate</span>
            <strong>{formatMoney(totalExposure.demurrage, totalExposure.currency)}</strong>
          </div>
          <div>
            <ShieldAlert size={18} />
            <span>Detention estimate</span>
            <strong>{formatMoney(totalExposure.detention, totalExposure.currency)}</strong>
          </div>
        </div>

        {loading ? (
          <LoadingState label="Loading containers..." />
        ) : containers.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Container</th>
                  <th>Size/Type</th>
                  <th>Status</th>
                  <th>Demurrage</th>
                  <th>Detention</th>
                  <th>Empty return</th>
                  <th>Risk</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {containers.map((container) => (
                  <tr key={container.id}>
                    <td>
                      <strong>{container.container_number}</strong>
                      {container.seal_number && (
                        <p className="muted">Seal {container.seal_number}</p>
                      )}
                    </td>
                    <td>
                      {container.container_size || '-'} / {container.container_type || '-'}
                    </td>
                    <td>{container.current_status}</td>
                    <td>
                      {container.exposure
                        ? `${formatMoney(container.exposure.demurrage_estimated_amount, container.exposure.currency)} (${container.exposure.demurrage_status})`
                        : '-'}
                    </td>
                    <td>
                      {container.exposure
                        ? `${formatMoney(container.exposure.detention_estimated_amount, container.exposure.currency)} (${container.exposure.detention_status})`
                        : '-'}
                    </td>
                    <td>{formatDate(container.empty_return_deadline)}</td>
                    <td>
                      <span className={`badge ${RISK_BADGE[container.exposure?.risk_level || 'none']}`}>
                        {container.exposure?.risk_level || 'none'}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => refreshContainer(container.id)}
                        >
                          <RefreshCcw size={13} />
                          Refresh
                        </button>
                        {canWrite && (
                          <>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => {
                                setTransitionTarget(container);
                                setTransitionForm({
                                  new_status: '',
                                  reason: '',
                                });
                              }}
                            >
                              Transition
                            </button>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => {
                                setEventTarget(container);
                                setEventForm({
                                  event_type: '',
                                  event_date: '',
                                  description: '',
                                });
                              }}
                            >
                              Add event
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No containers yet"
            detail={canWrite ? 'Add a container to start tracking lifecycle, demurrage, and detention.' : 'Containers will appear here once created.'}
          />
        )}
      </section>

      {showAdd && (
        <div className="dialog-backdrop" role="presentation" onClick={() => setShowAdd(false)}>
          <section
            className="dialog-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Add container"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-header">
              <h2>Add container</h2>
            </div>
            <form className="form-grid" onSubmit={addContainer}>
              <label className="span-2">
                Container number
                <input
                  required
                  value={addForm.container_number}
                  onChange={(event) =>
                    setAddForm((current) => ({ ...current, container_number: event.target.value.toUpperCase() }))
                  }
                  placeholder="ABCD1234567"
                />
              </label>
              <label>
                Size
                <input
                  value={addForm.container_size}
                  onChange={(event) =>
                    setAddForm((current) => ({ ...current, container_size: event.target.value }))
                  }
                  placeholder="20 / 40"
                />
              </label>
              <label>
                Type
                <input
                  value={addForm.container_type}
                  onChange={(event) =>
                    setAddForm((current) => ({ ...current, container_type: event.target.value }))
                  }
                  placeholder="40HC"
                />
              </label>
              <label className="span-2">
                Seal number
                <input
                  value={addForm.seal_number}
                  onChange={(event) =>
                    setAddForm((current) => ({ ...current, seal_number: event.target.value }))
                  }
                />
              </label>
              <div className="row-actions form-actions span-2">
                <button className="secondary-button" type="button" onClick={() => setShowAdd(false)}>
                  Cancel
                </button>
                <button className="primary-button" type="submit">
                  <Plus size={14} />
                  Add
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {transitionTarget && (
        <div className="dialog-backdrop" role="presentation" onClick={() => setTransitionTarget(null)}>
          <section
            className="dialog-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Transition container"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-header">
              <h2>Transition {transitionTarget.container_number}</h2>
            </div>
            <form className="form-grid" onSubmit={submitTransition}>
              <label className="span-2">
                New status
                <select
                  required
                  value={transitionForm.new_status}
                  onChange={(event) =>
                    setTransitionForm((current) => ({ ...current, new_status: event.target.value }))
                  }
                >
                  <option value="">Select status</option>
                  {statuses.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label className="span-2">
                Reason
                <input
                  value={transitionForm.reason}
                  onChange={(event) =>
                    setTransitionForm((current) => ({ ...current, reason: event.target.value }))
                  }
                />
              </label>
              <div className="row-actions form-actions span-2">
                <button className="secondary-button" type="button" onClick={() => setTransitionTarget(null)}>
                  Cancel
                </button>
                <button className="primary-button" type="submit">Transition</button>
              </div>
            </form>
          </section>
        </div>
      )}

      {eventTarget && (
        <div className="dialog-backdrop" role="presentation" onClick={() => setEventTarget(null)}>
          <section
            className="dialog-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Add container event"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-header">
              <h2>Add event for {eventTarget.container_number}</h2>
            </div>
            <form className="form-grid" onSubmit={submitEvent}>
              <label className="span-2">
                Event type
                <input
                  required
                  value={eventForm.event_type}
                  onChange={(event) =>
                    setEventForm((current) => ({ ...current, event_type: event.target.value.toUpperCase() }))
                  }
                  placeholder="GATE_IN"
                />
              </label>
              <label>
                Event date
                <input
                  type="date"
                  value={eventForm.event_date}
                  onChange={(event) =>
                    setEventForm((current) => ({ ...current, event_date: event.target.value }))
                  }
                />
              </label>
              <label>
                Description
                <input
                  value={eventForm.description}
                  onChange={(event) =>
                    setEventForm((current) => ({ ...current, description: event.target.value }))
                  }
                />
              </label>
              <div className="row-actions form-actions span-2">
                <button className="secondary-button" type="button" onClick={() => setEventTarget(null)}>
                  Cancel
                </button>
                <button className="primary-button" type="submit">Add event</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </section>
  );
}

export default ContainersPanel;
