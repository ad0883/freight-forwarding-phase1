import { KeyRound, Plus, ShieldCheck, UserCheck, UserX } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ConfirmDialog, EmptyState, ErrorState, LoadingState, RoleBadge } from '../components/States.jsx';

const initialForm = {
  name: '',
  email: '',
  password: '',
  role: 'STAFF',
  is_active: true,
};

function UsersAdminPage() {
  const [users, setUsers] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [form, setForm] = useState(initialForm);
  const [reset, setReset] = useState({ user: null, password: '', confirm_password: '' });
  const [confirm, setConfirm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/users');
      setUsers(response.data);
      setDrafts(
        Object.fromEntries(
          response.data.map((user) => [
            user.id,
            {
              name: user.name,
              role: user.role,
            },
          ])
        )
      );
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load users');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createUser(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      await api.post('/users', form);
      setForm(initialForm);
      setNotice('User created');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create user');
    }
  }

  async function updateUser(user, patch) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/users/${user.id}`, patch);
      setNotice('User updated');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update user');
    }
  }

  async function setActive(user, active) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/users/${user.id}/${active ? 'reactivate' : 'deactivate'}`);
      setNotice(active ? 'User reactivated' : 'User deactivated');
      setConfirm(null);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update user status');
      setConfirm(null);
    }
  }

  async function resetPassword(event) {
    event.preventDefault();
    if (!reset.user) return;
    setError('');
    setNotice('');
    if (reset.password !== reset.confirm_password) {
      setError('New passwords do not match');
      return;
    }
    try {
      await api.patch(`/users/${reset.user.id}/password-reset`, { new_password: reset.password });
      setReset({ user: null, password: '', confirm_password: '' });
      setNotice('Password reset');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to reset password');
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Users</h1>
        </div>
      </div>
      <ErrorState message={error} />
      {notice && <p className="success-text">{notice}</p>}

      <form className="panel form-grid" onSubmit={createUser}>
        <div className="panel-header span-2 no-margin">
          <h2>Create User</h2>
        </div>
        <label>
          Name <span style={{ color: 'var(--color-danger)' }}>*</span>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required placeholder="Full name" />
        </label>
        <label>
          Email <span style={{ color: 'var(--color-danger)' }}>*</span>
          <input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} type="email" required placeholder="user@company.com" />
        </label>
        <label>
          Password <span style={{ color: 'var(--color-danger)' }}>*</span>
          <input value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} type="password" minLength="6" required placeholder="Minimum 6 characters" />
        </label>
        <label>
          Role
          <select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>
            <option value="ADMIN">ADMIN</option>
            <option value="STAFF">STAFF</option>
            <option value="VIEW_ONLY">VIEW_ONLY</option>
          </select>
        </label>
        <div className="form-actions span-2">
          <button className="primary-button" type="submit">
            <Plus size={18} />
            <span>Create User</span>
          </button>
        </div>
      </form>

      <section className="panel">
        <div className="panel-header">
          <h2>User Directory</h2>
        </div>
        {loading ? (
          <LoadingState label="Loading users..." />
        ) : users.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <input
                        value={drafts[user.id]?.name || ''}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [user.id]: { ...(current[user.id] || {}), name: event.target.value },
                          }))
                        }
                      />
                    </td>
                    <td>{user.email}</td>
                    <td>
                      <select
                        value={drafts[user.id]?.role || user.role}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [user.id]: { ...(current[user.id] || {}), role: event.target.value },
                          }))
                        }
                      >
                        <option value="ADMIN">ADMIN</option>
                        <option value="STAFF">STAFF</option>
                        <option value="VIEW_ONLY">VIEW_ONLY</option>
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${user.is_active ? 'status-completed' : 'state-inactive'}`}>
                        {user.is_active ? 'active' : 'inactive'}
                      </span>
                    </td>
                    <td style={{ whiteSpace: 'nowrap' }}>{new Date(user.created_at).toLocaleString()}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() =>
                            updateUser(user, {
                              name: drafts[user.id]?.name || user.name,
                              role: drafts[user.id]?.role || user.role,
                            })
                          }
                        >
                          <UserCheck size={16} />
                          <span>Save</span>
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => setReset({ user, password: '', confirm_password: '' })}
                        >
                          <KeyRound size={16} />
                          <span>Reset</span>
                        </button>
                        {user.is_active ? (
                          <button
                            className="secondary-button danger-text"
                            type="button"
                            onClick={() => setConfirm({ user, active: false })}
                          >
                            <UserX size={16} />
                            <span>Deactivate</span>
                          </button>
                        ) : (
                          <button className="secondary-button" type="button" onClick={() => setConfirm({ user, active: true })}>
                            <UserCheck size={16} />
                            <span>Reactivate</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No users found" />
        )}
      </section>

      {reset.user && (
        <form className="panel form-grid" onSubmit={resetPassword}>
          <div className="panel-header span-2 no-margin">
            <h2>Reset Password: {reset.user.email}</h2>
          </div>
          <label>
            New Password <span style={{ color: 'var(--color-danger)' }}>*</span>
            <input value={reset.password} onChange={(event) => setReset((current) => ({ ...current, password: event.target.value }))} type="password" minLength="6" required placeholder="Minimum 6 characters" />
          </label>
          <label>
            Confirm New Password <span style={{ color: 'var(--color-danger)' }}>*</span>
            <input
              value={reset.confirm_password}
              onChange={(event) => setReset((current) => ({ ...current, confirm_password: event.target.value }))}
              type="password"
              minLength="6"
              required
              placeholder="Repeat new password"
            />
          </label>
          <div className="form-actions span-2">
            <button className="secondary-button" type="button" onClick={() => setReset({ user: null, password: '', confirm_password: '' })}>
              Cancel
            </button>
            <button className="primary-button" type="submit">
              <ShieldCheck size={18} />
              <span>Save Password</span>
            </button>
          </div>
        </form>
      )}
      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.active ? 'Reactivate User' : 'Deactivate User'}
        message={confirm ? `${confirm.active ? 'Reactivate' : 'Deactivate'} ${confirm.user.email}?` : ''}
        confirmLabel={confirm?.active ? 'Reactivate' : 'Deactivate'}
        danger={!confirm?.active}
        onCancel={() => setConfirm(null)}
        onConfirm={() => setActive(confirm.user, confirm.active)}
      />
    </div>
  );
}

export default UsersAdminPage;
