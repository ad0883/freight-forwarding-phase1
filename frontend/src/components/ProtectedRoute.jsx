import { Navigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import api from '../api/client.js';
import { LoadingState } from './States.jsx';

function cachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user') || 'null');
  } catch {
    return null;
  }
}

function ProtectedRoute({ children, allowedRoles = null }) {
  const location = useLocation();
  const token = localStorage.getItem('access_token');
  const [currentUser, setCurrentUser] = useState(cachedUser);
  const [loading, setLoading] = useState(Boolean(token));
  const [invalidToken, setInvalidToken] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let alive = true;
    api
      .get('/auth/me')
      .then((response) => {
        if (!alive) return;
        setCurrentUser(response.data);
        localStorage.setItem('current_user', JSON.stringify(response.data));
        setInvalidToken(false);
      })
      .catch(() => {
        if (!alive) return;
        localStorage.removeItem('access_token');
        localStorage.removeItem('current_user');
        setCurrentUser(null);
        setInvalidToken(true);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [token]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (invalidToken) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (loading) {
    return <LoadingState label="Checking permissions..." />;
  }
  if (allowedRoles && !allowedRoles.includes(currentUser?.role)) {
    return (
      <div className="page-stack">
        <section className="panel permission-panel">
          <p className="eyebrow">403</p>
          <h1>Not allowed</h1>
          <p className="muted">Your account does not have permission to open this page.</p>
        </section>
      </div>
    );
  }
  return children;
}

export default ProtectedRoute;
