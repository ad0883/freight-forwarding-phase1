import { Activity, Bot, Database, Mail, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { ErrorState, LoadingState } from '../components/States.jsx';

function StatusPage() {
  const [health, setHealth] = useState(null);
  const [gmail, setGmail] = useState(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  async function load() {
    setError('');
    setRefreshing(true);
    try {
      const [healthResponse, gmailResponse] = await Promise.all([
        api.get('/health/details'),
        api.get('/email/debug/config'),
      ]);
      setHealth(healthResponse.data);
      setGmail(gmailResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load system status');
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Status</h1>
        </div>
      </div>
      <ErrorState message={error} onRetry={load} />
    </div>
  );
  if (!health || !gmail) return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Status</h1>
        </div>
      </div>
      <LoadingState label="Loading system status..." />
    </div>
  );

  const cards = [
    { label: 'API', value: health.status, icon: Activity, tone: health.status === 'ok' ? 'success-card' : 'warning-card' },
    { label: 'Database', value: health.database, icon: Database, tone: health.database === 'ok' ? 'success-card' : 'critical-card' },
    { label: 'Gmail', value: gmail.gmail_enabled ? 'enabled' : 'disabled', icon: Mail, tone: gmail.gmail_enabled ? 'success-card' : 'warning-card' },
    { label: 'AI Provider', value: health.ai_enabled ? health.ai_provider : 'disabled', icon: Bot, tone: health.ai_enabled ? 'info-card' : 'warning-card' },
  ];

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Status</h1>
        </div>
        <button className="secondary-button" type="button" onClick={load} disabled={refreshing}>
          <RefreshCw size={18} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>
      <section className="metric-grid">
        {cards.map(({ label, value, icon: Icon, tone }) => (
          <article className={`metric-card ${tone}`} key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>
      <section className="panel">
        <div className="panel-header">
          <h2>Configuration Checks</h2>
        </div>
        <div className="info-grid">
          <Info label="Environment" value={health.environment} />
          <Info label="Version" value={health.version} />
          <Info label="Google Client ID" value={gmail.has_google_client_id ? 'configured' : 'missing'} ok={gmail.has_google_client_id} />
          <Info label="Google Client Secret" value={gmail.has_google_client_secret ? 'configured' : 'missing'} ok={gmail.has_google_client_secret} />
          <Info label="Redirect URI" value={gmail.google_redirect_uri} />
          <Info label="Frontend URL" value={gmail.frontend_base_url} />
          <Info label="Gmail Scopes" value={(gmail.gmail_scopes || []).join(', ')} />
          <Info label="Token Key" value={gmail.token_encryption_key_valid ? 'valid' : 'invalid or missing'} ok={gmail.token_encryption_key_valid} />
        </div>
      </section>
    </div>
  );
}

function Info({ label, value, ok }) {
  return (
    <div className="info-item">
      <span>{label}</span>
      <strong style={ok === false ? { color: 'var(--color-danger)' } : ok === true ? { color: 'var(--color-success)' } : undefined}>
        {value || '-'}
      </strong>
    </div>
  );
}

export default StatusPage;
