import {
  CheckCircle2,
  ExternalLink,
  Mail,
  Plug,
  RefreshCw,
  RotateCcw,
  Search,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client.js';
import { ConfirmDialog, EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const initialScan = {
  query: '',
  lookback_days: '30',
  max_results: '20',
};

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function summarizeData(data) {
  return Object.entries(data || {})
    .filter(([, value]) => value !== null && value !== '')
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ') || '-';
}

function getConflictList(error) {
  const detail = error.response?.data?.detail;
  if (detail?.conflicts) return detail.conflicts;
  return [];
}

function suggestionNeedsShipment(suggestion) {
  return Boolean(suggestion);
}

function EmailAutomationPage() {
  const [searchParams] = useSearchParams();
  const [currentUser, setCurrentUser] = useState(null);
  const [connection, setConnection] = useState(null);
  const [messages, setMessages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [shipments, setShipments] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [reviewShipmentId, setReviewShipmentId] = useState('');
  const [reviewJson, setReviewJson] = useState('{}');
  const [scanForm, setScanForm] = useState(initialScan);
  const [conflicts, setConflicts] = useState([]);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const canUseEmail = currentUser && ['ADMIN', 'STAFF'].includes(currentUser.role);
  const selectedShipment = useMemo(
    () => shipments.find((shipment) => String(shipment.id) === String(reviewShipmentId)) || null,
    [shipments, reviewShipmentId]
  );
  const applyDisabled = suggestionNeedsShipment(selectedSuggestion) && !reviewShipmentId;
  const oauthNotice = useMemo(() => {
    if (searchParams.get('connected')) return 'Gmail connected';
    if (searchParams.get('email_error')) return `Gmail connection failed: ${searchParams.get('email_error')}`;
    return '';
  }, [searchParams]);

  async function loadBase() {
    setError('');
    const meResponse = await api.get('/auth/me');
    setCurrentUser(meResponse.data);
    if (!['ADMIN', 'STAFF'].includes(meResponse.data.role)) return;
    const [statusResponse, messagesResponse, suggestionsResponse, shipmentsResponse] = await Promise.all([
      api.get('/email/status'),
      api.get('/email/messages'),
      api.get('/email/suggestions', { params: { status: 'pending' } }),
      api.get('/shipments', { params: { include_archived: true } }),
    ]);
    setConnection(statusResponse.data);
    setMessages(messagesResponse.data);
    setSuggestions(suggestionsResponse.data);
    setShipments(shipmentsResponse.data);
  }

  useEffect(() => {
    loadBase()
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load email automation'))
      .finally(() => setInitialLoading(false));
  }, []);

  useEffect(() => {
    if (oauthNotice) setNotice(oauthNotice);
  }, [oauthNotice]);

  async function refresh() {
    setLoading(true);
    try {
      await loadBase();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to refresh email automation');
    } finally {
      setLoading(false);
    }
  }

  async function connectGmail() {
    setError('');
    try {
      const response = await api.get('/email/oauth/start');
      window.location.href = response.data.auth_url;
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to start Gmail connection');
    }
  }

  async function disconnectGmail() {
    setError('');
    setNotice('');
    try {
      await api.post('/email/disconnect');
      setNotice('Gmail disconnected');
      setConfirmDisconnect(false);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to disconnect Gmail');
      setConfirmDisconnect(false);
    }
  }

  async function scanEmail(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setNotice('');
    try {
      const payload = {
        query: scanForm.query || null,
        lookback_days: Number(scanForm.lookback_days),
        max_results: Number(scanForm.max_results),
      };
      const response = await api.post('/email/scan', payload);
      setNotice(
        `Scan complete: ${response.data.scanned} scanned, ${response.data.suggestions_created} suggestions created`
      );
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to scan Gmail');
    } finally {
      setLoading(false);
    }
  }

  async function openMessage(message) {
    setSelectedSuggestion(null);
    setConflicts([]);
    try {
      const response = await api.get(`/email/messages/${message.id}`);
      setSelectedMessage(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load email message');
    }
  }

  async function reviewSuggestion(suggestion) {
    setConflicts([]);
    setSelectedSuggestion(suggestion);
    const matchedShipment = shipments.find(
      (shipment) =>
        (suggestion.shipment_id && shipment.id === suggestion.shipment_id) ||
        (suggestion.shipment_code && shipment.shipment_code === suggestion.shipment_code) ||
        (suggestion.extracted_data_json?.shipment_code &&
          shipment.shipment_code === suggestion.extracted_data_json.shipment_code)
    );
    setReviewShipmentId(matchedShipment ? String(matchedShipment.id) : '');
    setReviewJson(JSON.stringify(suggestion.extracted_data_json || {}, null, 2));
    try {
      const response = await api.get(`/email/messages/${suggestion.email_message_id}`);
      setSelectedMessage(response.data);
    } catch (err) {
      setSelectedMessage(null);
    }
  }

  async function saveReviewEdits() {
    if (!selectedSuggestion) return selectedSuggestion;
    let parsed;
    try {
      parsed = JSON.parse(reviewJson);
    } catch {
      setError('Extracted data must be valid JSON');
      return null;
    }
    const response = await api.patch(`/email/suggestions/${selectedSuggestion.id}`, {
      shipment_id: reviewShipmentId ? Number(reviewShipmentId) : null,
      extracted_data_json: parsed,
    });
    setSelectedSuggestion(response.data);
    return response.data;
  }

  async function applySelected(force = false) {
    setError('');
    setNotice('');
    setConflicts([]);
    if (applyDisabled) {
      setError('Select a shipment before applying this suggestion.');
      return;
    }
    const saved = await saveReviewEdits();
    if (!saved) return;
    try {
      await api.post(`/email/suggestions/${saved.id}/apply`, { force });
      setNotice('Suggestion applied');
      setSelectedSuggestion(null);
      await refresh();
    } catch (err) {
      const conflictList = getConflictList(err);
      if (conflictList.length) {
        setConflicts(conflictList);
      } else {
        setError(err.response?.data?.detail || 'Unable to apply suggestion');
      }
    }
  }

  async function rejectSelected() {
    if (!selectedSuggestion) return;
    setError('');
    setNotice('');
    setConflicts([]);
    try {
      await api.post(`/email/suggestions/${selectedSuggestion.id}/reject`);
      setNotice('Suggestion rejected');
      setSelectedSuggestion(null);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to reject suggestion');
    }
  }

  if (initialLoading) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Gmail</p>
            <h1>Email Automation</h1>
          </div>
        </div>
        <LoadingState label="Loading email automation..." />
      </div>
    );
  }

  if (currentUser && !canUseEmail) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Email</p>
            <h1>Email Automation</h1>
          </div>
        </div>
        <section className="panel">
          <p className="muted">Email automation is available to ADMIN and STAFF users.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Gmail</p>
          <h1>Email Automation</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={refresh} disabled={loading}>
            <RefreshCw size={18} />
            <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      <ErrorState message={typeof error === 'string' ? error : JSON.stringify(error)} />
      {notice && <p className="success-text">{notice}</p>}

      <section className="panel">
        <div className="panel-header">
          <h2>Connection Status</h2>
          <span className={`badge ${connection?.connected ? 'status-completed' : 'status-cancelled'}`}>
            {connection?.connected ? 'connected' : 'not connected'}
          </span>
        </div>
        <div className="email-status-row">
          <div>
            <strong>{connection?.email_address || 'No Gmail account connected'}</strong>
            <p className="muted">Provider: gmail</p>
          </div>
          <div className="row-actions">
            {connection?.connected ? (
              <button className="secondary-button danger-text" type="button" onClick={() => setConfirmDisconnect(true)}>
                <Plug size={18} />
                <span>Disconnect</span>
              </button>
            ) : (
              <button className="primary-button" type="button" onClick={connectGmail}>
                <ExternalLink size={18} />
                <span>Connect Gmail</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {connection?.connected && (
        <form className="panel form-grid" onSubmit={scanEmail}>
          <div className="panel-header span-2 no-margin">
            <h2>Scan Settings</h2>
          </div>
          <label className="span-2">
            Search Query
            <input
              value={scanForm.query}
              onChange={(event) => setScanForm((current) => ({ ...current, query: event.target.value }))}
              placeholder='booking OR "BL draft" OR "arrival notice" OR "freight invoice"'
            />
          </label>
          <label>
            Lookback Days
            <input
              min="1"
              type="number"
              value={scanForm.lookback_days}
              onChange={(event) => setScanForm((current) => ({ ...current, lookback_days: event.target.value }))}
            />
          </label>
          <label>
            Max Results
            <input
              min="1"
              type="number"
              value={scanForm.max_results}
              onChange={(event) => setScanForm((current) => ({ ...current, max_results: event.target.value }))}
            />
          </label>
          <div className="form-actions span-2">
            <button className="primary-button" type="submit" disabled={loading}>
              <Search size={18} />
              <span>{loading ? 'Scanning...' : 'Scan Gmail'}</span>
            </button>
          </div>
        </form>
      )}

      <section className="split-grid email-review-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Pending Suggestions</h2>
          </div>
          {!suggestions.length ? (
            <EmptyState title="No pending suggestions" detail="Run a Gmail scan to generate suggestions." />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Shipment</th>
                    <th>Confidence</th>
                    <th>Extracted Summary</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {suggestions.map((suggestion) => (
                    <tr key={suggestion.id}>
                      <td>{suggestion.suggestion_type}</td>
                      <td>
                        {suggestion.shipment_code || '-'}
                        {suggestion.shipment_is_archived && <span className="badge status-archived">Archived</span>}
                      </td>
                      <td>{Math.round(Number(suggestion.confidence || 0) * 100)}%</td>
                      <td>{summarizeData(suggestion.extracted_data_json)}</td>
                      <td>
                        <span className={`badge suggestion-${suggestion.status}`}>{suggestion.status}</span>
                      </td>
                      <td>
                        <button className="secondary-button" type="button" onClick={() => reviewSuggestion(suggestion)}>
                          <Mail size={16} />
                          <span>Review</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Suggestion Review</h2>
          </div>
          {selectedSuggestion ? (
            <div className="review-stack">
              <label>
                Shipment
                <select value={reviewShipmentId} onChange={(event) => setReviewShipmentId(event.target.value)}>
                  <option value="">Select shipment</option>
                  {shipments.map((shipment) => (
                    <option key={shipment.id} value={shipment.id}>
                      {shipment.shipment_code}{shipment.is_archived ? ' (Archived)' : ''}
                    </option>
                  ))}
                </select>
              </label>
              {selectedShipment?.is_archived && (
                <div className="warning-box">
                  <strong>{selectedShipment.shipment_code} is archived.</strong>
                  <p>{selectedShipment.archive_reason || 'Review carefully before force applying this suggestion.'}</p>
                </div>
              )}
              <label>
                Extracted Data
                <textarea
                  className="json-editor"
                  value={reviewJson}
                  onChange={(event) => setReviewJson(event.target.value)}
                />
              </label>
              {conflicts.length > 0 && (
                <div className="conflict-list">
                  {conflicts.map((conflict) => (
                    <p key={`${conflict.field}-${conflict.suggested_value}`}>
                      <strong>{conflict.field}</strong>: {conflict.message}
                    </p>
                  ))}
                </div>
              )}
              <div className="row-actions">
                <button className="primary-button" type="button" onClick={() => applySelected(false)} disabled={applyDisabled}>
                  <CheckCircle2 size={18} />
                  <span>Apply</span>
                </button>
                {conflicts.length > 0 && (
                  <button className="secondary-button" type="button" onClick={() => applySelected(true)} disabled={applyDisabled}>
                    <RotateCcw size={18} />
                    <span>Force Apply</span>
                  </button>
                )}
                <button className="secondary-button danger-text" type="button" onClick={rejectSelected}>
                  <XCircle size={18} />
                  <span>Reject</span>
                </button>
              </div>
            </div>
          ) : (
            <EmptyState title="Select a suggestion" detail="Click Review on a pending suggestion to begin." />
          )}
          {selectedMessage && (
            <div className="email-preview">
              <strong>{selectedMessage.subject || '(no subject)'}</strong>
              <span>{selectedMessage.sender || '-'}</span>
              <p>{selectedMessage.body_preview || selectedMessage.snippet || '-'}</p>
            </div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Cached Emails</h2>
        </div>
        {!messages.length ? (
          <EmptyState title="No cached emails" detail="Run a Gmail scan to cache emails." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Received</th>
                  <th>From</th>
                  <th>Subject</th>
                  <th>Classification</th>
                  <th>Shipment</th>
                  <th>Status</th>
                  <th>Suggestions</th>
                  <th>Open</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((message) => (
                  <tr key={message.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{formatDate(message.received_at)}</td>
                    <td>{message.sender || '-'}</td>
                    <td>{message.subject || '-'}</td>
                    <td>
                      <span className={`badge email-${message.classification}`}>{message.classification}</span>
                    </td>
                    <td>{message.matched_shipment_code || '-'}</td>
                    <td>{message.processed_status}</td>
                    <td>{message.suggestion_count}</td>
                    <td>
                      <button className="secondary-button" type="button" onClick={() => openMessage(message)}>
                        <Mail size={16} />
                        <span>Open</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <ConfirmDialog
        open={confirmDisconnect}
        title="Disconnect Gmail"
        message="Disconnect this Gmail account from email automation?"
        confirmLabel="Disconnect"
        danger
        onCancel={() => setConfirmDisconnect(false)}
        onConfirm={disconnectGmail}
      />
    </div>
  );
}

export default EmailAutomationPage;
