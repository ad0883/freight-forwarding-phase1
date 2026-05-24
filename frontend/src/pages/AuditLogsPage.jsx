import { Download, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({ search: '', action: '', entity_type: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
      const response = await api.get('/audit-logs', { params });
      setLogs(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load audit logs');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timeout = setTimeout(load, 250);
    return () => clearTimeout(timeout);
  }, [filters.search, filters.action, filters.entity_type]);

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Audit Logs</h1>
        </div>
        <button className="secondary-button" type="button" onClick={() => downloadExport('/exports/audit-logs.csv', 'audit-logs.csv')}>
          <Download size={18} />
          <span>Export CSV</span>
        </button>
      </div>
      <div className="toolbar filter-toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            value={filters.search}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            placeholder="Search actor, action, entity, description"
          />
        </div>
        <input
          value={filters.action}
          onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value }))}
          placeholder="Action"
        />
        <input
          value={filters.entity_type}
          onChange={(event) => setFilters((current) => ({ ...current, entity_type: event.target.value }))}
          placeholder="Entity type"
        />
      </div>
      <ErrorState message={error} />
      {loading ? (
        <LoadingState label="Loading audit logs..." />
      ) : (
        <section className="panel">
          {logs.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Entity</th>
                    <th>Description</th>
                    <th>Metadata</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td>{new Date(log.created_at).toLocaleString()}</td>
                      <td>{log.actor_email || 'system'}</td>
                      <td>{log.action}</td>
                      <td>{log.entity_type}{log.entity_label ? `: ${log.entity_label}` : ''}</td>
                      <td>{log.description || '-'}</td>
                      <td className="metadata-cell">{JSON.stringify(log.metadata_json || {})}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No audit logs found" detail="Adjust filters or perform an audited action." />
          )}
        </section>
      )}
    </div>
  );
}

async function downloadExport(path, filename) {
  const response = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default AuditLogsPage;
