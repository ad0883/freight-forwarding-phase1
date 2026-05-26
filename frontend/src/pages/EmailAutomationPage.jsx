import {
  CheckCircle2,
  Eraser,
  ExternalLink,
  Eye,
  EyeOff,
  Mail,
  Plug,
  RefreshCw,
  RotateCcw,
  Search,
  Trash2,
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
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState(new Set());
  const [reviewShipmentId, setReviewShipmentId] = useState('');
  const [reviewJson, setReviewJson] = useState('{}');
  const [scanForm, setScanForm] = useState(initialScan);
  const [conflicts, setConflicts] = useState([]);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [confirmCleanup, setConfirmCleanup] = useState(false);
  const [showLowConfidence, setShowLowConfidence] = useState(false);
  const [includeHidden, setIncludeHidden] = useState(false);
  const [currentAccountOnly, setCurrentAccountOnly] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const isAdmin = currentUser?.role === 'ADMIN';
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

  const visibleSuggestions = useMemo(() => {
    if (showLowConfidence) return suggestions;
    return suggestions.filter(
      (suggestion) => suggestion.confidence >= 0.7 || suggestion.shipment_id
    );
  }, [suggestions, showLowConfidence]);

  async function loadBase() {
    setError('');
    const meResponse = await api.get('/auth/me');
    setCurrentUser(meResponse.data);
    if (!['ADMIN', 'STAFF'].includes(meResponse.data.role)) return;
    const [statusResponse, messagesResponse, suggestionsResponse, shipmentsResponse] = await Promise.all([
      api.get('/email/status'),
      api.get('/email/messages', {
        params: {
          current_account_only: currentAccountOnly,
          include_hidden: includeHidden,
        },
      }),
      api.get('/email/suggestions', {
        params: {
          status: 'pending',
          current_account_only: currentAccountOnly,
        },
      }),
      api.get('/shipments', { params: { include_archived: true } }),
    ]);
    setConnection(statusResponse.data);
    setMessages(messagesResponse.data);
    setSuggestions(suggestionsResponse.data);
    setShipments(shipmentsResponse.data);
    setSelectedSuggestionIds(new Set());
  }

  useEffect(() => {
    loadBase()
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load email automation'))
      .finally(() => setInitialLoading(false));
  }, [currentAccountOnly, includeHidden]);

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

  async function disconnectGmail(clearCache) {
    setError('');
    setNotice('');
    try {
      const response = await api.post('/email/disconnect', { clear_cache: clearCache });
      setNotice(
        clearCache
          ? `Gmail disconnected. Cleared ${response.data.suggestions_rejected} suggestion(s) and hid ${response.data.messages_hidden} cached email(s).`
          : 'Gmail disconnected'
      );
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
        `Scan complete: ${response.data.scanned} scanned, ${response.data.cached} new, ${response.data.duplicates_skipped} duplicates skipped, ${response.data.suggestions_created} suggestions created`
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
      await api.patch(`/email/suggestions/${selectedSuggestion.id}/reject`);
      setNotice('Suggestion rejected');
      setSelectedSuggestion(null);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to reject suggestion');
    }
  }

  async function dismissSelected() {
    if (!selectedSuggestion) return;
    setError('');
    setNotice('');
    setConflicts([]);
    try {
      await api.patch(`/email/suggestions/${selectedSuggestion.id}/dismiss`);
      setNotice('Suggestion dismissed');
      setSelectedSuggestion(null);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to dismiss suggestion');
    }
  }

  async function deleteSelected() {
    if (!selectedSuggestion || !isAdmin) return;
    if (!window.confirm('Permanently delete this suggestion? Applied records remain.')) return;
    setError('');
    setNotice('');
    try {
      await api.delete(`/email/suggestions/${selectedSuggestion.id}`);
      setNotice('Suggestion deleted');
      setSelectedSuggestion(null);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete suggestion');
    }
  }

  function toggleSuggestionSelection(id) {
    setSelectedSuggestionIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function selectAllVisible() {
    setSelectedSuggestionIds(new Set(visibleSuggestions.map((suggestion) => suggestion.id)));
  }

  function clearSelection() {
    setSelectedSuggestionIds(new Set());
  }

  async function bulkRejectSelected() {
    if (!selectedSuggestionIds.size) return;
    setError('');
    setNotice('');
    try {
      const response = await api.post('/email/suggestions/bulk-reject', {
        suggestion_ids: Array.from(selectedSuggestionIds),
      });
      setNotice(`${response.data.rejected} suggestion(s) rejected.`);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Bulk reject failed');
    }
  }

  async function clearPending(filters, label) {
    setError('');
    setNotice('');
    try {
      const response = await api.post('/email/suggestions/clear-pending', {
        current_account_only: true,
        ...filters,
      });
      setNotice(`${label}: ${response.data.rejected} suggestion(s) rejected.`);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to clear pending suggestions');
    }
  }

  async function cleanupOldAccounts() {
    setError('');
    setNotice('');
    try {
      const response = await api.post('/email/cleanup', {
        gmail_account_email: null,
        hide_messages: true,
        reject_pending: true,
      });
      setNotice(
        `Cleanup: rejected ${response.data.suggestions_rejected} suggestion(s) and hid ${response.data.messages_hidden} cached email(s).`
      );
      setConfirmCleanup(false);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Cleanup failed');
      setConfirmCleanup(false);
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
            <strong>{connection?.gmail_account_email || connection?.email_address || 'No Gmail account connected'}</strong>
            <p className="muted">
              Provider: gmail · Pending suggestions: {connection?.pending_suggestions ?? 0} · Cached emails: {connection?.cached_messages ?? 0}
            </p>
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
        <div className="row-actions wrap">
          <label className="compact-toggle">
            <input
              type="checkbox"
              checked={currentAccountOnly}
              onChange={(event) => setCurrentAccountOnly(event.target.checked)}
            />
            Show current account only
          </label>
          <label className="compact-toggle">
            <input
              type="checkbox"
              checked={includeHidden}
              onChange={(event) => setIncludeHidden(event.target.checked)}
            />
            Include hidden cached emails
          </label>
          <label className="compact-toggle">
            <input
              type="checkbox"
              checked={showLowConfidence}
              onChange={(event) => setShowLowConfidence(event.target.checked)}
            />
            Show low-confidence / no-shipment suggestions
          </label>
          <button
            className="secondary-button"
            type="button"
            onClick={() =>
              clearPending(
                { low_confidence: true },
                'Cleared low-confidence suggestions'
              )
            }
          >
            <Eraser size={16} />
            <span>Clear low-confidence</span>
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() =>
              clearPending({ no_shipment: true }, 'Cleared no-shipment suggestions')
            }
          >
            <Eraser size={16} />
            <span>Clear no-shipment</span>
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() =>
              clearPending({}, 'Cleared current account pending')
            }
          >
            <Eraser size={16} />
            <span>Clear current account pending</span>
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => setConfirmCleanup(true)}
          >
            <Trash2 size={16} />
            <span>Cleanup old/disconnected data</span>
          </button>
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
              placeholder='"freight invoice" OR "BL draft" OR "arrival notice" OR shipment'
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
            <h2>Pending Suggestions ({visibleSuggestions.length})</h2>
            <div className="row-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={selectAllVisible}
                disabled={!visibleSuggestions.length}
              >
                Select all
              </button>
              <button className="secondary-button" type="button" onClick={clearSelection} disabled={!selectedSuggestionIds.size}>
                Clear
              </button>
              <button
                className="secondary-button danger-text"
                type="button"
                onClick={bulkRejectSelected}
                disabled={!selectedSuggestionIds.size}
              >
                <XCircle size={15} />
                Reject selected ({selectedSuggestionIds.size})
              </button>
            </div>
          </div>
          {!visibleSuggestions.length ? (
            <EmptyState title="No pending suggestions" detail="Run a Gmail scan to generate suggestions." />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Type</th>
                    <th>Shipment</th>
                    <th>Account</th>
                    <th>Confidence</th>
                    <th>Extracted Summary</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleSuggestions.map((suggestion) => (
                    <tr key={suggestion.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedSuggestionIds.has(suggestion.id)}
                          onChange={() => toggleSuggestionSelection(suggestion.id)}
                          aria-label="Select suggestion"
                        />
                      </td>
                      <td>{suggestion.suggestion_type}</td>
                      <td>
                        {suggestion.shipment_code || '-'}
                        {suggestion.shipment_is_archived && <span className="badge status-archived">Archived</span>}
                      </td>
                      <td>{suggestion.gmail_account_email || '-'}</td>
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
                <button className="secondary-button" type="button" onClick={dismissSelected}>
                  <EyeOff size={18} />
                  <span>Dismiss</span>
                </button>
                {isAdmin && (
                  <button className="secondary-button danger-text" type="button" onClick={deleteSelected}>
                    <Trash2 size={18} />
                    <span>Delete</span>
                  </button>
                )}
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
          <h2>Cached Emails ({messages.length})</h2>
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
                  <th>Account</th>
                  <th>Classification</th>
                  <th>Shipment</th>
                  <th>Status</th>
                  <th>Suggestions</th>
                  <th>Open</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((message) => (
                  <tr key={message.id} className={message.visibility === 'hidden' ? 'muted-row' : ''}>
                    <td style={{ whiteSpace: 'nowrap' }}>{formatDate(message.received_at)}</td>
                    <td>{message.sender || '-'}</td>
                    <td>{message.subject || '-'}</td>
                    <td>{message.gmail_account_email || '-'}</td>
                    <td>
                      <span className={`badge email-${message.classification}`}>{message.classification}</span>
                    </td>
                    <td>{message.matched_shipment_code || '-'}</td>
                    <td>
                      {message.visibility === 'hidden' ? (
                        <span className="badge status-archived">hidden</span>
                      ) : (
                        message.processed_status
                      )}
                    </td>
                    <td>{message.suggestion_count}</td>
                    <td>
                      <button className="secondary-button" type="button" onClick={() => openMessage(message)}>
                        <Eye size={16} />
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
        message="Disconnect this Gmail account from email automation? You can also clear the cached emails and pending suggestions for this account."
        confirmLabel="Disconnect & clear cache"
        danger
        onCancel={() => setConfirmDisconnect(false)}
        onConfirm={() => disconnectGmail(true)}
      />
      <ConfirmDialog
        open={confirmCleanup}
        title="Cleanup old / disconnected data"
        message="Hide cached emails and reject pending suggestions for the connected account. Applied charges, tasks, and documents are not affected."
        confirmLabel="Cleanup"
        danger
        onCancel={() => setConfirmCleanup(false)}
        onConfirm={cleanupOldAccounts}
      />
    </div>
  );
}

export default EmailAutomationPage;
