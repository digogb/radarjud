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
          <Radar size={32} color="#3b82f6" />
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
    background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
    padding: '1rem',
  },
  card: {
    background: '#1e293b',
    borderRadius: '1rem',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '400px',
    boxShadow: '0 25px 50px rgba(0,0,0,0.4)',
    border: '1px solid #334155',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '0.5rem',
  },
  title: {
    color: '#f1f5f9',
    fontSize: '1.5rem',
    fontWeight: 700,
    margin: 0,
  },
  subtitle: {
    color: '#94a3b8',
    marginBottom: '1.5rem',
    fontSize: '0.9rem',
  },
  error: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    background: '#450a0a',
    border: '1px solid #7f1d1d',
    borderRadius: '0.5rem',
    color: '#fca5a5',
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
    color: '#cbd5e1',
    fontSize: '0.875rem',
    fontWeight: 500,
  },
  input: {
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '0.5rem',
    color: '#f1f5f9',
    padding: '0.625rem 0.875rem',
    fontSize: '0.9rem',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  },
  button: {
    background: '#3b82f6',
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
    color: '#475569',
    fontSize: '0.75rem',
    marginTop: '1.5rem',
    textAlign: 'center',
  },
};
