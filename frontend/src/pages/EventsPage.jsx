import { Filter, RefreshCcw, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

const initialFilters = {
  event_type: '',
  entity_type: '',
  source: '',
  validation_status: '',
  search: '',
};

const VALIDATION_STATUS_BADGE = {
  passed: 'status-active',
  not_checked: 'status-inactive',
  warning: 'status-pending',
  failed: 'status-cancelled',
  manual_review_required: 'status-cancelled',
};

function statusBadgeClass(value) {
  return VALIDATION_STATUS_BADGE[value] || 'status-pending';
}

function EventsPage() {
  const [events, setEvents] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  async function load() {
    setError('');
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, value]) => value !== '')
      );
      const response = await api.get('/events', { params: { ...params, limit: 100 } });
      setEvents(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load events');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filters.event_type, filters.entity_type, filters.source, filters.validation_status]);

  function searchSubmit(event) {
    event.preventDefault();
    load();
  }

  const eventCount = useMemo(() => events.length, [events]);

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operational Brain</p>
          <h1>Events</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCcw size={16} />
            Refresh
          </button>
        </div>
      </div>
      <p className="muted">
        Operational events recorded by Phase 9. Each event captures actor, source,
        and validation status. Phase 9 events are non-blocking by default.
      </p>

      <form className="toolbar filter-toolbar" onSubmit={searchSubmit}>
        <div className="search-box">
          <Search size={16} />
          <input
            value={filters.search}
            onChange={(event) => setFilters((value) => ({ ...value, search: event.target.value }))}
            placeholder="Search by event type or entity label"
          />
        </div>
        <input
          value={filters.event_type}
          onChange={(event) => setFilters((value) => ({ ...value, event_type: event.target.value }))}
          placeholder="Event type filter"
        />
        <input
          value={filters.entity_type}
          onChange={(event) => setFilters((value) => ({ ...value, entity_type: event.target.value }))}
          placeholder="Entity type filter"
        />
        <select
          value={filters.source}
          onChange={(event) => setFilters((value) => ({ ...value, source: event.target.value }))}
          title="Source"
        >
          <option value="">All sources</option>
          {['user', 'system', 'gmail', 'ai', 'scheduler', 'workflow', 'finance', 'notification'].map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <select
          value={filters.validation_status}
          onChange={(event) => setFilters((value) => ({ ...value, validation_status: event.target.value }))}
          title="Validation"
        >
          <option value="">All validation statuses</option>
          {['not_checked', 'passed', 'warning', 'failed', 'manual_review_required'].map((item) => (
            <option key={item} value={item}>{item.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <button className="secondary-button" type="submit">
          <Filter size={16} />
          Apply
        </button>
      </form>

      <ErrorState message={error} onRetry={load} />

      {loading ? (
        <LoadingState label="Loading events..." />
      ) : (
        <section className="panel">
          {eventCount ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Event</th>
                    <th>Entity</th>
                    <th>Source</th>
                    <th>Actor</th>
                    <th>Validation</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>{new Date(event.created_at).toLocaleString()}</td>
                      <td>{event.event_type}</td>
                      <td>
                        {event.entity_type}
                        {event.entity_label ? `: ${event.entity_label}` : event.entity_id ? ` #${event.entity_id}` : ''}
                      </td>
                      <td><span className="badge">{event.source}</span></td>
                      <td>{event.actor_email || event.actor_name || '-'}</td>
                      <td>
                        <span className={`badge ${statusBadgeClass(event.validation_status)}`}>
                          {event.validation_status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>
                        <button className="secondary-button" type="button" onClick={() => setSelected(event)}>
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No events found" detail="Adjust filters or perform a tracked action." />
          )}
        </section>
      )}

      {selected && (
        <div className="dialog-backdrop" role="presentation" onClick={() => setSelected(null)}>
          <section
            className="dialog-panel wide"
            role="dialog"
            aria-modal="true"
            aria-label="Event details"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-header">
              <h2>{selected.event_type}</h2>
              <button className="icon-button" type="button" onClick={() => setSelected(null)}>
                Close
              </button>
            </div>
            <p className="muted">
              {new Date(selected.created_at).toLocaleString()} - {selected.source} - {selected.validation_status.replace(/_/g, ' ')}
            </p>
            <div className="event-detail-grid">
              <div>
                <h3>Entity</h3>
                <p>{selected.entity_type}{selected.entity_label ? `: ${selected.entity_label}` : ''}</p>
                <p className="muted">id={selected.entity_id ?? '-'}</p>
              </div>
              <div>
                <h3>Actor</h3>
                <p>{selected.actor_name || '-'}</p>
                <p className="muted">{selected.actor_email || ''} {selected.actor_role ? `(${selected.actor_role})` : ''}</p>
              </div>
              <div>
                <h3>Previous state</h3>
                <pre>{JSON.stringify(selected.previous_state_json || {}, null, 2)}</pre>
              </div>
              <div>
                <h3>New state</h3>
                <pre>{JSON.stringify(selected.new_state_json || {}, null, 2)}</pre>
              </div>
              <div className="span-2">
                <h3>Metadata</h3>
                <pre>{JSON.stringify(selected.metadata_json || {}, null, 2)}</pre>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default EventsPage;
