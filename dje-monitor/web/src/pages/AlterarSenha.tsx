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

  return (
    <div style={{ padding: '2rem', maxWidth: 400 }}>
      <h2 style={{ marginBottom: '1.5rem', color: '#f1f5f9' }}>Alterar Senha</h2>

      {success && (
        <div style={{ background: '#065f46', color: '#6ee7b7', padding: '0.75rem 1rem', borderRadius: 6, marginBottom: '1rem', fontSize: '0.9rem' }}>
          Senha alterada com sucesso.
        </div>
      )}
      {error && (
        <div style={{ background: '#450a0a', color: '#fca5a5', padding: '0.75rem 1rem', borderRadius: 6, marginBottom: '1rem', fontSize: '0.9rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', color: '#94a3b8', fontSize: '0.85rem' }}>
            Senha atual
          </label>
          <input
            type="password"
            value={form.current_password}
            onChange={e => setForm(f => ({ ...f, current_password: e.target.value }))}
            required
            style={{ width: '100%', padding: '0.6rem 0.75rem', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', fontSize: '0.9rem', boxSizing: 'border-box' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', color: '#94a3b8', fontSize: '0.85rem' }}>
            Nova senha
          </label>
          <input
            type="password"
            value={form.new_password}
            onChange={e => setForm(f => ({ ...f, new_password: e.target.value }))}
            required
            minLength={8}
            style={{ width: '100%', padding: '0.6rem 0.75rem', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', fontSize: '0.9rem', boxSizing: 'border-box' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', color: '#94a3b8', fontSize: '0.85rem' }}>
            Confirmar nova senha
          </label>
          <input
            type="password"
            value={form.confirm}
            onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
            required
            style={{ width: '100%', padding: '0.6rem 0.75rem', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', fontSize: '0.9rem', boxSizing: 'border-box' }}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          style={{ padding: '0.65rem', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer', fontSize: '0.9rem', opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Salvando…' : 'Alterar Senha'}
        </button>
      </form>
    </div>
  )
}
