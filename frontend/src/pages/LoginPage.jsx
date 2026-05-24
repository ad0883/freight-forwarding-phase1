import { LogIn } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client.js';

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const body = new URLSearchParams();
      body.append('username', email);
      body.append('password', password);
      const response = await api.post('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      localStorage.setItem('access_token', response.data.access_token);
      const meResponse = await api.get('/auth/me');
      localStorage.setItem('current_user', JSON.stringify(meResponse.data));
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <div className="brand login-brand">
          <div className="brand-mark">LM</div>
          <div>
            <strong>Logistics Manager</strong>
            <span>Freight Operations</span>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="form-card">
          <h1>Sign in</h1>
          <p className="muted" style={{ textAlign: 'center', marginTop: '-0.3rem' }}>
            Enter your credentials to continue
          </p>
          <label>
            Email address
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required placeholder="you@company.com" />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              required
              placeholder="••••••••"
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          <button className="primary-button" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
            <LogIn size={18} />
            <span>{loading ? 'Signing in...' : 'Sign in'}</span>
          </button>
        </form>
      </section>
    </main>
  );
}

export default LoginPage;
