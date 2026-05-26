import { Check, Filter, RefreshCcw, Search, ShieldAlert, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const initialFilters = {
  status: 'open',
  severity: '',
  rule_key: '',
  entity_type: '',
  search: '',
};

const SEVERITY_BADGE = {
  critical: 'priority-critical',
  warning: 'priority-warning',
  info: 'priority-info',
};

function ValidationIssuesPage() {
  const [issues, setIssues] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState('');

  async function load() {
    setError('');
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, value]) => value !== '')
      );
      const response = await api.get('/validation-issues', { params: { ...params, limit: 100 } });
      setIssues(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load validation issues');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filters.status, filters.severity, filters.rule_key, filters.entity_type]);

  function searchSubmit(event) {
    event.preventDefault();
    load();
  }

  async function applyAction(issueId, action) {
    setActionMessage('');
    try {
      await api.patch(`/validation-issues/${issueId}/${action}`);
      setActionMessage(`Issue ${issueId} ${action}d.`);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Action failed');
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operational Brain</p>
          <h1>Validation Issues</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCcw size={16} />
            Refresh
          </button>
        </div>
      </div>
      <p className="muted">
        Validation issues are non-blocking warnings unless explicitly marked critical
        or escalated. Acknowledge, resolve, or dismiss as you triage.
      </p>

      <form className="toolbar filter-toolbar" onSubmit={searchSubmit}>
        <div className="search-box">
          <Search size={16} />
          <input
            value={filters.search}
            onChange={(event) => setFilters((value) => ({ ...value, search: event.target.value }))}
            placeholder="Search issue message or entity"
          />
        </div>
        <select
          value={filters.status}
          onChange={(event) => setFilters((value) => ({ ...value, status: event.target.value }))}
          title="Status"
        >
          <option value="">All statuses</option>
          {['open', 'acknowledged', 'resolved', 'dismissed'].map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <select
          value={filters.severity}
          onChange={(event) => setFilters((value) => ({ ...value, severity: event.target.value }))}
          title="Severity"
        >
          <option value="">All severities</option>
          {['critical', 'warning', 'info'].map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <input
          value={filters.rule_key}
          onChange={(event) => setFilters((value) => ({ ...value, rule_key: event.target.value }))}
          placeholder="Rule key filter"
        />
        <input
          value={filters.entity_type}
          onChange={(event) => setFilters((value) => ({ ...value, entity_type: event.target.value }))}
          placeholder="Entity type filter"
        />
        <button className="secondary-button" type="submit">
          <Filter size={16} />
          Apply
        </button>
      </form>

      <ErrorState message={error} onRetry={load} />
      {actionMessage && <p className="success-text">{actionMessage}</p>}

      {loading ? (
        <LoadingState label="Loading validation issues..." />
      ) : (
        <section className="panel">
          {issues.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Created</th>
                    <th>Severity</th>
                    <th>Rule</th>
                    <th>Entity</th>
                    <th>Message</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((issue) => (
                    <tr key={issue.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>{new Date(issue.created_at).toLocaleString()}</td>
                      <td>
                        <span className={`badge ${SEVERITY_BADGE[issue.severity] || 'priority-info'}`}>
                          <ShieldAlert size={12} /> {issue.severity}
                        </span>
                      </td>
                      <td>{issue.rule_key}</td>
                      <td>
                        {issue.entity_type}
                        {issue.entity_label ? `: ${issue.entity_label}` : issue.entity_id ? ` #${issue.entity_id}` : ''}
                      </td>
                      <td>
                        <strong>{issue.message}</strong>
                        {issue.recommended_action && <p className="muted">{issue.recommended_action}</p>}
                      </td>
                      <td><span className="badge">{issue.status}</span></td>
                      <td>
                        <div className="row-actions">
                          {issue.status !== 'acknowledged' && issue.status !== 'resolved' && issue.status !== 'dismissed' && (
                            <button className="secondary-button" type="button" onClick={() => applyAction(issue.id, 'acknowledge')}>
                              Acknowledge
                            </button>
                          )}
                          {issue.status !== 'resolved' && (
                            <button className="secondary-button" type="button" onClick={() => applyAction(issue.id, 'resolve')}>
                              <Check size={15} />
                              Resolve
                            </button>
                          )}
                          {issue.status !== 'dismissed' && (
                            <button className="secondary-button" type="button" onClick={() => applyAction(issue.id, 'dismiss')}>
                              <X size={15} />
                              Dismiss
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
            <EmptyState title="No validation issues" detail="Adjust filters or run notification checks to refresh data." />
          )}
        </section>
      )}
    </div>
  );
}

export default ValidationIssuesPage;
