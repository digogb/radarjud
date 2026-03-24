import { useState } from 'react'
import { authApi } from '../services/api'

export default function AlterarSenha() {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    if (form.new_password !== form.confirm) {
      setError('A nova senha e a confirmação não coincidem.')
      return
    }
    if (form.new_password.length < 8) {
      setError('A nova senha deve ter pelo menos 8 caracteres.')
      return
    }

    setLoading(true)
    try {
      await authApi.changePassword(form.current_password, form.new_password)
      setSuccess(true)
      setForm({ current_password: '', new_password: '', confirm: '' })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(msg || 'Erro ao alterar senha.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '0.6rem 0.75rem',
    background: 'var(--background-secondary)', border: '1px solid var(--border)',
    borderRadius: 6, color: 'var(--text-primary)', fontSize: '0.9rem', boxSizing: 'border-box',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.85rem',
  }

  return (
    <div style={{ padding: '2rem', maxWidth: 400 }}>
      <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-primary)' }}>Alterar Senha</h2>

      {success && (
        <div style={{ background: 'var(--success-muted)', color: 'var(--success)', padding: '0.75rem 1rem', borderRadius: 6, marginBottom: '1rem', fontSize: '0.9rem' }}>
          Senha alterada com sucesso.
        </div>
      )}
      {error && (
        <div style={{ background: 'var(--danger-muted)', color: 'var(--danger)', padding: '0.75rem 1rem', borderRadius: 6, marginBottom: '1rem', fontSize: '0.9rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <label style={labelStyle}>Senha atual</label>
          <input
            type="password"
            value={form.current_password}
            onChange={e => setForm(f => ({ ...f, current_password: e.target.value }))}
            required
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelStyle}>Nova senha</label>
          <input
            type="password"
            value={form.new_password}
            onChange={e => setForm(f => ({ ...f, new_password: e.target.value }))}
            required
            minLength={8}
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelStyle}>Confirmar nova senha</label>
          <input
            type="password"
            value={form.confirm}
            onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
            required
            style={inputStyle}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          style={{ padding: '0.65rem', background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer', fontSize: '0.9rem', opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Salvando…' : 'Alterar Senha'}
        </button>
      </form>
    </div>
  )
}
