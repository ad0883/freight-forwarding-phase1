import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, Lock, RefreshCcw, ShieldAlert } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from './States.jsx';

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

const STATUS_BADGE = {
  applied: 'status-active',
  blocked: 'status-cancelled',
  manual_review_required: 'priority-critical',
  failed: 'status-cancelled',
  requested: 'status-pending',
};

function WorkflowPanel({ shipmentId }) {
  const [user] = useState(cachedUser);
  const [state, setState] = useState(null);
  const [transitions, setTransitions] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [acting, setActing] = useState(false);
  const canTransition = user?.role !== 'VIEW_ONLY';

  async function load() {
    setError('');
    setLoading(true);
    try {
      const [stateResp, availableResp, timelineResp] = await Promise.all([
        api.get(`/workflow/shipments/${shipmentId}/state`),
        api.get(`/workflow/shipments/${shipmentId}/available-transitions`),
        api.get(`/workflow/shipments/${shipmentId}/timeline`),
      ]);
      setState(stateResp.data);
      setTransitions(availableResp.data.transitions || []);
      setTimeline(timelineResp.data.entries || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load workflow data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (shipmentId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipmentId]);

  async function applyTransition(transition) {
    if (!canTransition || !transition.permitted) return;
    if (transition.is_sensitive) {
      const ok = window.confirm(
        `${transition.label}\nThis is a sensitive transition. Apply now?`
      );
      if (!ok) return;
    }
    const reason = transition.requires_reason
      ? window.prompt(`Reason for ${transition.label}`)
      : null;
    if (transition.requires_reason && !reason) {
      setError('Reason is required for this transition.');
      return;
    }
    setActing(true);
    setActionMessage('');
    setError('');
    try {
      const response = await api.post(`/workflow/shipments/${shipmentId}/transition`, {
        to_state: transition.to_state,
        reason: reason || null,
        confirm_sensitive: transition.is_sensitive ? true : false,
      });
      setActionMessage(
        `${response.data.status.replace(/_/g, ' ')}: ${response.data.from_state || 'unset'} -> ${response.data.to_state}`
      );
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Transition failed');
    } finally {
      setActing(false);
    }
  }

  if (loading) {
    return (
      <section className="panel">
        <div className="panel-header">
          <h2>Workflow State</h2>
        </div>
        <LoadingState label="Loading workflow data..." />
      </section>
    );
  }

  return (
    <section className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <h2>Workflow State</h2>
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCcw size={15} />
            Refresh
          </button>
        </div>
        <ErrorState message={error} onRetry={load} />
        {actionMessage && <p className="success-text">{actionMessage}</p>}

        {state && (
          <div className="workflow-state-grid">
            <div>
              <p className="muted">Flow type</p>
              <strong>{state.flow_type}</strong>
            </div>
            <div>
              <p className="muted">Current state</p>
              <strong>
                {state.workflow_state_label || state.workflow_state || 'Unset'}
                {state.inferred && <span className="badge"> inferred</span>}
              </strong>
            </div>
            <div>
              <p className="muted">Updated at</p>
              <strong>
                {state.workflow_state_updated_at
                  ? new Date(state.workflow_state_updated_at).toLocaleString()
                  : '-'}
              </strong>
            </div>
            <div>
              <p className="muted">Manual review</p>
              <strong>
                {state.manual_review_required ? (
                  <span className="badge priority-critical">
                    <ShieldAlert size={12} /> required
                  </span>
                ) : (
                  <span className="badge status-active">clear</span>
                )}
              </strong>
              {state.manual_review_reason && (
                <p className="muted">{state.manual_review_reason}</p>
              )}
            </div>
          </div>
        )}

        {!canTransition && (
          <p className="muted">
            <Lock size={14} /> View-only role cannot transition workflow state.
          </p>
        )}

        <div className="panel-header no-margin">
          <h3>Available next transitions</h3>
        </div>
        {transitions.length ? (
          <div className="workflow-transition-list">
            {transitions.map((transition) => (
              <article className="workflow-transition-card" key={transition.transition_key}>
                <div>
                  <strong>{transition.label}</strong>
                  <p className="muted">
                    {transition.to_state_label || transition.to_state}
                  </p>
                  <div className="row-actions">
                    {transition.is_sensitive && (
                      <span className="badge priority-critical">
                        <AlertTriangle size={12} /> sensitive
                      </span>
                    )}
                    {transition.requires_confirmation && (
                      <span className="badge">requires confirmation</span>
                    )}
                    {transition.requires_reason && (
                      <span className="badge">requires reason</span>
                    )}
                  </div>
                </div>
                <button
                  className={transition.is_sensitive ? 'primary-button danger-button' : 'primary-button'}
                  type="button"
                  onClick={() => applyTransition(transition)}
                  disabled={!canTransition || !transition.permitted || acting}
                  title={transition.permission_reason || ''}
                >
                  <ArrowRight size={15} />
                  Transition
                </button>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No transitions available" detail="The shipment has reached a terminal state, or no rule chain matches the current state." />
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Workflow Timeline</h2>
          <Link to="/events">View all events</Link>
        </div>
        {timeline.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Status</th>
                  <th>Validation</th>
                  <th>Actor</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {timeline.map((row) => (
                  <tr key={row.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <Clock3 size={12} /> {new Date(row.created_at).toLocaleString()}
                    </td>
                    <td>{row.from_state || '-'}</td>
                    <td>{row.to_state}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[row.status] || ''}`}>
                        {row.status === 'applied' && <CheckCircle2 size={12} />}
                        {row.status === 'manual_review_required' && <ShieldAlert size={12} />}
                        {row.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>{row.validation_status.replace(/_/g, ' ')}</td>
                    <td>{row.actor_email || row.actor_name || '-'}</td>
                    <td>{row.reason || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No workflow history yet" detail="Transitions you apply will appear here." />
        )}
      </section>
    </section>
  );
}

export default WorkflowPanel;
