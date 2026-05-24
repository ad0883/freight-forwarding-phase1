import { KeyRound } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function SettingsPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get('/auth/me')
      .then((response) => setCurrentUser(response.data))
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load account settings'));
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    if (form.new_password !== form.confirm_password) {
      setError('New passwords do not match');
      return;
    }
    setSaving(true);
    try {
      await api.post('/auth/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setForm({ current_password: '', new_password: '', confirm_password: '' });
      setNotice('Password changed');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to change password');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Settings</h1>
        </div>
      </div>
      {!currentUser ? (
        <LoadingState label="Loading account..." />
      ) : (
        <section className="panel">
          <div className="info-grid">
            <div className="info-item">
              <span>Name</span>
              <strong>{currentUser.name}</strong>
            </div>
            <div className="info-item">
              <span>Email</span>
              <strong>{currentUser.email}</strong>
            </div>
            <div className="info-item">
              <span>Role</span>
              <strong>{currentUser.role}</strong>
            </div>
            <div className="info-item">
              <span>Status</span>
              <strong>{currentUser.is_active ? 'Active' : 'Inactive'}</strong>
            </div>
          </div>
        </section>
      )}
      <form className="panel form-grid settings-form" onSubmit={submit}>
        <label>
          Current Password
          <input
            type="password"
            value={form.current_password}
            onChange={(event) => setForm((current) => ({ ...current, current_password: event.target.value }))}
            required
          />
        </label>
        <label>
          New Password
          <input
            type="password"
            minLength="6"
            value={form.new_password}
            onChange={(event) => setForm((current) => ({ ...current, new_password: event.target.value }))}
            required
          />
        </label>
        <label>
          Confirm New Password
          <input
            type="password"
            minLength="6"
            value={form.confirm_password}
            onChange={(event) => setForm((current) => ({ ...current, confirm_password: event.target.value }))}
            required
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={saving}>
            <KeyRound size={18} />
            <span>{saving ? 'Saving...' : 'Change Password'}</span>
          </button>
        </div>
      </form>
      <ErrorState message={error} />
      {notice && <p className="success-text">{notice}</p>}
    </div>
  );
}

export default SettingsPage;
