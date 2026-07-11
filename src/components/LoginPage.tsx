import { useState } from 'react';
import { Shield } from 'lucide-react';
import { forgotPassword, login, register, resetPassword } from '../lib/api';

interface LoginPageProps {
  onAuth: () => void;
}

const initialResetToken = new URLSearchParams(window.location.search).get('reset_token');

const LoginPage = ({ onAuth }: LoginPageProps) => {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot' | 'reset'>(initialResetToken ? 'reset' : 'login');
  const [resetToken] = useState(initialResetToken ?? '');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
        onAuth();
      } else if (mode === 'register') {
        if (password.length < 8) { setError('Password must be at least 8 characters'); setLoading(false); return; }
        await register(email, password);
        onAuth();
      } else if (mode === 'forgot') {
        const res = await forgotPassword(email);
        setInfo(res.message);
      } else {
        if (newPassword.length < 8) { setError('Password must be at least 8 characters'); setLoading(false); return; }
        await resetPassword(resetToken, newPassword);
        window.history.replaceState({}, '', window.location.pathname);
        onAuth();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (next: typeof mode) => {
    setMode(next);
    setError('');
    setInfo('');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-base)' }}>
      <div style={{ width: '100%', maxWidth: '400px', padding: '0 1.5rem' }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.5rem', justifyContent: 'center' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', backgroundColor: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Shield size={20} color="white" />
          </div>
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>TS-RX</span>
        </div>

        <div className="ts-panel" style={{ padding: '2rem' }}>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.375rem', textAlign: 'center' }}>
            {mode === 'login' && 'Sign in'}
            {mode === 'register' && 'Create account'}
            {mode === 'forgot' && 'Reset password'}
            {mode === 'reset' && 'Set new password'}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center', marginBottom: '1.5rem' }}>
            {mode === 'login' && 'Self-healing network dashboard'}
            {mode === 'register' && 'Monitor your Tailscale services'}
            {mode === 'forgot' && "Enter your email and we'll send you a reset link"}
            {mode === 'reset' && 'Choose a new password for your account'}
          </p>

          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {(mode === 'login' || mode === 'register' || mode === 'forgot') && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
                  Email
                </label>
                <input
                  type="email"
                  className="ts-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoFocus
                />
              </div>
            )}
            {(mode === 'login' || mode === 'register') && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
                  Password
                </label>
                <input
                  type="password"
                  className="ts-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'register' ? 'At least 8 characters' : '••••••••'}
                  required
                />
              </div>
            )}
            {mode === 'reset' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
                  New password
                </label>
                <input
                  type="password"
                  className="ts-input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  required
                  autoFocus
                />
              </div>
            )}

            {mode === 'login' && (
              <button
                type="button"
                onClick={() => switchMode('forgot')}
                style={{ alignSelf: 'flex-end', background: 'none', border: 'none', color: 'var(--accent-text)', cursor: 'pointer', fontSize: '0.75rem', padding: 0, marginTop: '-0.5rem' }}
              >
                Forgot password?
              </button>
            )}

            {error && (
              <div style={{ padding: '0.625rem 0.875rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#FCA5A5', fontSize: '0.8125rem' }}>
                {error}
              </div>
            )}
            {info && (
              <div style={{ padding: '0.625rem 0.875rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', color: '#86EFAC', fontSize: '0.8125rem' }}>
                {info}
              </div>
            )}

            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', padding: '0.625rem', justifyContent: 'center', marginTop: '0.25rem' }}>
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create account' : mode === 'forgot' ? 'Send reset link' : 'Update password'}
            </button>
          </form>

          <div style={{ marginTop: '1.25rem', textAlign: 'center', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            {mode === 'login' && (
              <>Don't have an account?{' '}
                <button onClick={() => switchMode('register')} style={{ background: 'none', border: 'none', color: 'var(--accent-text)', cursor: 'pointer', fontSize: '0.8125rem', padding: 0 }}>
                  Sign up
                </button>
              </>
            )}
            {mode === 'register' && (
              <>Already have an account?{' '}
                <button onClick={() => switchMode('login')} style={{ background: 'none', border: 'none', color: 'var(--accent-text)', cursor: 'pointer', fontSize: '0.8125rem', padding: 0 }}>
                  Sign in
                </button>
              </>
            )}
            {(mode === 'forgot' || mode === 'reset') && (
              <button onClick={() => switchMode('login')} style={{ background: 'none', border: 'none', color: 'var(--accent-text)', cursor: 'pointer', fontSize: '0.8125rem', padding: 0 }}>
                Back to sign in
              </button>
            )}
          </div>
        </div>

        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '1.5rem' }}>
          Connect any Tailscale node via Uptime Kuma webhook
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
