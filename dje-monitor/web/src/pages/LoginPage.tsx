import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Radar, Lock, Mail, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Credenciais inválidas. Verifique email e senha.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <Radar size={32} color="var(--primary)" />
          <h1 style={styles.title}>RadarJud</h1>
        </div>

        <p style={styles.subtitle}>Faça login para continuar</p>

        {error && (
          <div style={styles.error}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>
              <Mail size={14} style={{ marginRight: 6 }} />
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
              style={styles.input}
              autoComplete="email"
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>
              <Lock size={14} style={{ marginRight: 6 }} />
              Senha
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={styles.input}
              autoComplete="current-password"
            />
          </div>

          <button type="submit" disabled={loading} style={styles.button}>
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <p style={styles.footer}>
          Problemas para entrar? Contate o administrador do sistema.
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--gradient-bg)',
    padding: '1rem',
  },
  card: {
    background: 'var(--surface)',
    borderRadius: '1rem',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '400px',
    boxShadow: 'var(--shadow-lg)',
    border: '1px solid var(--glass-border)',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '0.5rem',
  },
  title: {
    color: 'var(--text-primary)',
    fontSize: '1.5rem',
    fontWeight: 700,
    margin: 0,
  },
  subtitle: {
    color: 'var(--text-secondary)',
    marginBottom: '1.5rem',
    fontSize: '0.9rem',
  },
  error: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    background: 'var(--danger-muted)',
    border: '1px solid var(--danger)',
    borderRadius: '0.5rem',
    color: 'var(--danger)',
    padding: '0.75rem 1rem',
    marginBottom: '1rem',
    fontSize: '0.875rem',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.375rem',
  },
  label: {
    display: 'flex',
    alignItems: 'center',
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
    fontWeight: 500,
  },
  input: {
    background: 'var(--background-secondary)',
    border: '1px solid var(--border)',
    borderRadius: '0.5rem',
    color: 'var(--text-primary)',
    padding: '0.625rem 0.875rem',
    fontSize: '0.9rem',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  },
  button: {
    background: 'var(--primary)',
    color: '#fff',
    border: 'none',
    borderRadius: '0.5rem',
    padding: '0.75rem',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: '0.5rem',
    transition: 'background 0.2s',
  },
  footer: {
    color: 'var(--text-muted)',
    fontSize: '0.75rem',
    marginTop: '1.5rem',
    textAlign: 'center',
  },
};
