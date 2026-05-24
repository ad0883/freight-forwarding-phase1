import { AlertTriangle, Inbox, Loader2, RefreshCw, X } from 'lucide-react';

export function LoadingState({ label = 'Loading...' }) {
  return (
    <div className="state-box">
      <Loader2 size={18} className="spin-icon" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="state-box error-state">
      <AlertTriangle size={18} />
      <span>{typeof message === 'string' ? message : JSON.stringify(message)}</span>
      {onRetry && (
        <button className="secondary-button" type="button" onClick={onRetry} style={{ marginLeft: 'auto' }}>
          <RefreshCw size={15} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title = 'No records found', detail = '' }) {
  return (
    <div className="state-box empty-state">
      <Inbox size={28} />
      <div>
        <strong>{title}</strong>
        {detail && <p>{detail}</p>}
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  danger = false,
  onConfirm,
  onCancel,
}) {
  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation" onClick={onCancel}>
      <section
        className="dialog-panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="panel-header">
          <h2>{title}</h2>
          <button className="icon-button" type="button" onClick={onCancel} title="Close">
            <X size={18} />
          </button>
        </div>
        <p className="muted">{message}</p>
        <div className="row-actions dialog-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button className={danger ? 'primary-button danger-button' : 'primary-button'} type="button" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

export function StatusBadge({ status, className = '' }) {
  if (!status) return null;
  const slug = String(status).toLowerCase().replace(/\s+/g, '_');
  return <span className={`badge status-${slug} ${className}`.trim()}>{status}</span>;
}

export function RoleBadge({ role }) {
  if (!role) return null;
  const slug = String(role).toLowerCase();
  return <span className={`badge role-${slug}`}>{role}</span>;
}
