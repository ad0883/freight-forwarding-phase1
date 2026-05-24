import { Database, Download } from 'lucide-react';
import { useState } from 'react';
import api from '../api/client.js';
import { ConfirmDialog, ErrorState } from '../components/States.jsx';

const exports = [
  { path: '/exports/shipments.csv', filename: 'shipments.csv', label: 'Shipments' },
  { path: '/exports/parties.csv', filename: 'parties.csv', label: 'Parties' },
  { path: '/exports/charges.csv', filename: 'charges.csv', label: 'Charges' },
  { path: '/exports/tasks.csv', filename: 'tasks.csv', label: 'Tasks' },
  { path: '/exports/audit-logs.csv', filename: 'audit-logs.csv', label: 'Audit Logs' },
];

function AdminToolsPage() {
  const [cleanup, setCleanup] = useState(null);
  const [confirmCleanup, setConfirmCleanup] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function runCleanupDryRun() {
    setError('');
    setNotice('');
    try {
      const response = await api.post('/admin/cleanup-test-data', null, { params: { dry_run: true } });
      setCleanup(response.data);
      setNotice('Dry-run scan complete');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to run cleanup dry-run');
    } finally {
      setConfirmCleanup(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Admin Tools</h1>
        </div>
      </div>
      <ErrorState message={error} />
      {notice && <p className="success-text">{notice}</p>}

      <section className="panel">
        <div className="panel-header">
          <h2>CSV Exports</h2>
        </div>
        <p className="muted" style={{ marginBottom: '0.75rem' }}>Download data exports as CSV files.</p>
        <div className="button-grid">
          {exports.map((item) => (
            <button className="secondary-button" type="button" key={item.path} onClick={() => downloadExport(item.path, item.filename)}>
              <Download size={18} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Test Data Cleanup</h2>
        </div>
        <p className="muted">Cleanup is dry-run only and does not modify records.</p>
        <div className="row-actions" style={{ marginTop: '0.75rem' }}>
          <button className="primary-button" type="button" onClick={() => setConfirmCleanup(true)}>
            <Database size={18} />
            <span>Run Dry-Run</span>
          </button>
        </div>
        {cleanup && (
          <div className="cleanup-grid">
            {Object.entries(cleanup.candidates || {}).map(([key, value]) => (
              <article className="info-item" key={key}>
                <span>{key}</span>
                <strong>{value.count}</strong>
                <p className="muted" style={{ fontSize: '0.8rem' }}>{(value.sample || []).map((item) => item.label).join(', ') || 'No matches'}</p>
              </article>
            ))}
          </div>
        )}
      </section>
      <ConfirmDialog
        open={confirmCleanup}
        title="Run Cleanup Dry-Run"
        message="Scan for test-data candidates without deleting or changing any records?"
        confirmLabel="Run Dry-Run"
        onCancel={() => setConfirmCleanup(false)}
        onConfirm={runCleanupDryRun}
      />
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

export default AdminToolsPage;
