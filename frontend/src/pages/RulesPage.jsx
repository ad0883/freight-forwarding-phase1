import { AlertTriangle, RefreshCcw, Settings2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const SEVERITY_OPTIONS = ['info', 'warning', 'critical'];

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

function RulesPage() {
  const [user] = useState(cachedUser);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const canEdit = user?.role === 'ADMIN';

  async function load() {
    setError('');
    setLoading(true);
    try {
      const response = await api.get('/rules');
      setRules(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load rules');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function updateRule(rule, patch) {
    try {
      const response = await api.patch(`/rules/${rule.id}`, patch);
      setRules((items) => items.map((item) => (item.id === rule.id ? response.data : item)));
      setActionMessage(`Updated ${rule.rule_key}.`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Update failed');
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operational Brain</p>
          <h1>Validation Rules</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCcw size={16} />
            Refresh
          </button>
        </div>
      </div>
      <p className="muted">
        Phase 9 validation rules. New rules default to non-blocking warnings. Blocking
        rules can affect operations - keep blocking off unless tested.
      </p>

      <ErrorState message={error} onRetry={load} />
      {actionMessage && <p className="success-text">{actionMessage}</p>}

      {loading ? (
        <LoadingState label="Loading rules..." />
      ) : (
        <section className="panel">
          {rules.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Entity</th>
                    <th>Severity</th>
                    <th>Enabled</th>
                    <th>Blocking</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id}>
                      <td>
                        <strong>{rule.name}</strong>
                        <p className="muted">{rule.description}</p>
                        <code className="muted">{rule.rule_key}</code>
                      </td>
                      <td>{rule.entity_type || '-'}</td>
                      <td>
                        {canEdit ? (
                          <select
                            value={rule.severity}
                            onChange={(event) => updateRule(rule, { severity: event.target.value })}
                          >
                            {SEVERITY_OPTIONS.map((item) => (
                              <option key={item} value={item}>{item}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="badge">{rule.severity}</span>
                        )}
                      </td>
                      <td>
                        {canEdit ? (
                          <label className="compact-toggle">
                            <input
                              type="checkbox"
                              checked={rule.is_enabled}
                              onChange={(event) => updateRule(rule, { is_enabled: event.target.checked })}
                            />
                            Enabled
                          </label>
                        ) : (
                          <span className="badge">{rule.is_enabled ? 'enabled' : 'disabled'}</span>
                        )}
                      </td>
                      <td>
                        {canEdit ? (
                          <label className="compact-toggle">
                            <input
                              type="checkbox"
                              checked={rule.is_blocking}
                              onChange={(event) => updateRule(rule, { is_blocking: event.target.checked })}
                            />
                            <AlertTriangle size={14} /> Blocking
                          </label>
                        ) : (
                          <span className={`badge ${rule.is_blocking ? 'priority-critical' : ''}`}>
                            {rule.is_blocking ? 'blocking' : 'non-blocking'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No rules" detail="Default rules are seeded on backend startup." />
          )}
        </section>
      )}

      {canEdit && (
        <p className="muted">
          <Settings2 size={14} /> Blocking rules are not enforced anywhere in Phase 9 routes
          - they only mark intent. Use them after Phase 10 introduces guarded write actions.
        </p>
      )}
    </div>
  );
}

export default RulesPage;
