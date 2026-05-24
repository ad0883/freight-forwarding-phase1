import { Ban, Plus, RotateCcw, ToggleRight, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';

const initialTask = {
  shipment_id: '',
  title: '',
  description: '',
  due_date: '',
  priority: 'info',
};

function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [shipments, setShipments] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [includeCancelled, setIncludeCancelled] = useState(false);
  const [form, setForm] = useState(initialTask);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const canWrite = currentUser && currentUser.role !== 'VIEW_ONLY';

  async function load() {
    const [tasksResponse, shipmentsResponse] = await Promise.all([
      api.get('/tasks', { params: includeCancelled ? { include_cancelled: true } : {} }),
      api.get('/shipments'),
    ]);
    setTasks(tasksResponse.data);
    setShipments(shipmentsResponse.data);
  }

  useEffect(() => {
    api.get('/auth/me').then((response) => setCurrentUser(response.data)).catch(() => setCurrentUser(null));
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err.response?.data?.detail || 'Unable to load tasks'));
  }, [includeCancelled]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function createTask(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      await api.post('/tasks', {
        shipment_id: Number(form.shipment_id),
        title: form.title,
        description: form.description || null,
        due_date: form.due_date || null,
        priority: form.priority,
        status: 'open',
      });
      setForm(initialTask);
      setNotice('Task created');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create task');
    }
  }

  async function toggleTask(task) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/tasks/${task.id}`, { status: task.status === 'open' ? 'done' : 'open' });
      setNotice('Task updated');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update task');
    }
  }

  async function cancelTask(task) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/tasks/${task.id}/cancel`);
      setNotice('Task cancelled');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to cancel task');
    }
  }

  async function restoreTask(task) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/tasks/${task.id}/restore`);
      setNotice('Task restored');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to restore task');
    }
  }

  async function deleteManualTask(task) {
    if (!window.confirm(`Delete manual task "${task.title}" permanently?`)) return;
    setError('');
    setNotice('');
    try {
      await api.delete(`/tasks/${task.id}`);
      setNotice('Manual task deleted');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete task');
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Work Queue</p>
          <h1>Tasks</h1>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {notice && <p className="success-text">{notice}</p>}

      {canWrite && (
        <form className="panel form-grid" onSubmit={createTask}>
          <label>
            Shipment
            <select required value={form.shipment_id} onChange={(event) => updateField('shipment_id', event.target.value)}>
              <option value="">Select shipment</option>
              {shipments.map((shipment) => (
                <option key={shipment.id} value={shipment.id}>
                  {shipment.shipment_code}
                </option>
              ))}
            </select>
          </label>
          <label>
            Title
            <input required value={form.title} onChange={(event) => updateField('title', event.target.value)} />
          </label>
          <label>
            Due Date
            <input type="date" value={form.due_date} onChange={(event) => updateField('due_date', event.target.value)} />
          </label>
          <label>
            Priority
            <select value={form.priority} onChange={(event) => updateField('priority', event.target.value)}>
              <option value="critical">critical</option>
              <option value="warning">warning</option>
              <option value="info">info</option>
            </select>
          </label>
          <label className="span-2">
            Description
            <textarea value={form.description} onChange={(event) => updateField('description', event.target.value)} />
          </label>
          <div className="form-actions span-2">
            <button className="primary-button" type="submit">
              <Plus size={18} />
              <span>Create Task</span>
            </button>
          </div>
        </form>
      )}

      <section className="panel">
        <div className="panel-header">
          <h2>Task List</h2>
          <label className="checkbox-label compact-toggle">
            <input
              type="checkbox"
              checked={includeCancelled}
              onChange={(event) => setIncludeCancelled(event.target.checked)}
            />
            Include Cancelled
          </label>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Shipment ID</th>
                <th>Due Date</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id}>
                  <td>{task.title}</td>
                  <td>#{task.shipment_id}</td>
                  <td>{task.due_date || '-'}</td>
                  <td>
                    <span className={`badge priority-${task.priority}`}>{task.priority}</span>
                  </td>
                  <td>
                    <span className={`badge task-${task.status}`}>{task.status}</span>
                  </td>
                  <td>
                    {canWrite && (
                      <div className="row-actions">
                        {task.status === 'cancelled' ? (
                          <button className="secondary-button" type="button" onClick={() => restoreTask(task)}>
                            <RotateCcw size={17} />
                            <span>Restore Task</span>
                          </button>
                        ) : (
                          <>
                            <button className="secondary-button" type="button" onClick={() => toggleTask(task)}>
                              {task.status === 'open' ? <ToggleRight size={17} /> : <RotateCcw size={17} />}
                              <span>{task.status === 'open' ? 'Mark done' : 'Reopen'}</span>
                            </button>
                            <button className="secondary-button danger-text" type="button" onClick={() => cancelTask(task)}>
                              <Ban size={17} />
                              <span>Cancel Task</span>
                            </button>
                          </>
                        )}
                        {!task.auto_generated && (
                          <button className="secondary-button danger-text" type="button" onClick={() => deleteManualTask(task)}>
                            <Trash2 size={17} />
                            <span>Delete Manual Task</span>
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {!tasks.length && (
                <tr>
                  <td colSpan="6">No tasks yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default TasksPage;
