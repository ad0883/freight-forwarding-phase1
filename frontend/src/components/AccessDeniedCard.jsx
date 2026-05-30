import { ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

/**
 * S2 — Access Denied Card
 * Shown when a user reaches a route/page their role cannot access.
 */
function AccessDeniedCard({ title, message }) {
  return (
    <div className="access-denied-card">
      <ShieldAlert size={36} />
      <h2>{title || 'Access restricted'}</h2>
      <p>{message || 'Your current role does not include this permission. Contact your admin if you need access.'}</p>
      <Link to="/today" className="primary-button">Back to Today</Link>
    </div>
  );
}

export default AccessDeniedCard;
