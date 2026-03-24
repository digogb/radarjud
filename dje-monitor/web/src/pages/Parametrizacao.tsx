import { useState, useEffect } from 'react'
import { Settings, Plus, Trash2, Loader2, AlertTriangle, Check, X, ChevronUp, ChevronDown, TrendingUp, ShieldOff } from 'lucide-react'
import { padroesApi, PadraoOportunidade } from '../services/api'

type Tipo = 'positivo' | 'negativo'

function TabelaPadroes({
  padroes,
  todos,
  reordenando,
  salvando,
  deletando,
  confirmandoDeletar,
  onToggle,
  onMover,
  onDeletar,
  onConfirmarDeletar,
}: {
  padroes: PadraoOportunidade[]
  todos: PadraoOportunidade[]
  reordenando: boolean
  salvando: number | null
  deletando: number | null
  confirmandoDeletar: number | null
  onToggle: (p: PadraoOportunidade) => void
  onMover: (globalIdx: number, direcao: 'cima' | 'baixo') => void
  onDeletar: (id: number) => void
  onConfirmarDeletar: (id: number | null) => void
}) {
  if (padroes.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
        Nenhum padrão cadastrado nesta seção.
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 540 }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--glass-border)' }}>
          {['Ordem', 'Label', 'Expressão', 'Ativo', ''].map(h => (
            <th key={h} style={{
              padding: '10px 16px',
              textAlign: 'left',
              fontSize: '0.78rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {padroes.map((padrao, localIdx) => {
          const globalIdx = todos.findIndex(p => p.id === padrao.id)
          return (
            <tr
              key={padrao.id}
              style={{
                borderBottom: localIdx < padroes.length - 1 ? '1px solid var(--glass-border)' : 'none',
                opacity: padrao.ativo ? 1 : 0.45,
              }}
            >
              <td style={{ padding: '10px 16px', width: 64 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <button
                    onClick={() => onMover(globalIdx, 'cima')}
                    disabled={localIdx === 0 || reordenando}
                    style={{
                      background: 'none', border: 'none', cursor: localIdx === 0 ? 'default' : 'pointer',
                      color: localIdx === 0 ? 'var(--glass-border)' : 'var(--text-muted)',
                      padding: 2, lineHeight: 1,
                    }}
                  >
                    <ChevronUp size={15} />
                  </button>
                  <button
                    onClick={() => onMover(globalIdx, 'baixo')}
                    disabled={localIdx === padroes.length - 1 || reordenando}
                    style={{
                      background: 'none', border: 'none', cursor: localIdx === padroes.length - 1 ? 'default' : 'pointer',
                      color: localIdx === padroes.length - 1 ? 'var(--glass-border)' : 'var(--text-muted)',
                      padding: 2, lineHeight: 1,
                    }}
                  >
                    <ChevronDown size={15} />
                  </button>
                </div>
              </td>

              <td style={{ padding: '14px 16px', fontWeight: 500, color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                {padrao.nome}
              </td>
              <td style={{ padding: '14px 16px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {padrao.expressao}
              </td>

              <td style={{ padding: '14px 16px' }}>
                <button
                  onClick={() => onToggle(padrao)}
                  disabled={salvando === padrao.id}
                  style={{
                    width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer',
                    background: padrao.ativo ? 'var(--success)' : 'var(--glass-border)',
                    position: 'relative', transition: 'background var(--transition-fast)', flexShrink: 0,
                  }}
                >
                  {salvando === padrao.id ? (
                    <Loader2 size={12} style={{ animation: 'spin 1s linear infinite', color: '#fff', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
                  ) : (
                    <span style={{
                      display: 'block', width: 18, height: 18, borderRadius: '50%', background: '#fff',
                      position: 'absolute', top: 3, left: padrao.ativo ? 23 : 3,
                      transition: 'left var(--transition-fast)',
                    }} />
                  )}
                </button>
              </td>

              <td style={{ padding: '14px 16px', textAlign: 'right', minWidth: 160 }}>
                {confirmandoDeletar === padrao.id ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Remover?</span>
                    <button
                      onClick={() => onDeletar(padrao.id)}
                      disabled={deletando === padrao.id}
                      className="btn btn-secondary"
                      style={{ padding: '4px 12px', fontSize: '0.8rem', color: 'var(--danger)', borderColor: 'var(--danger)' }}
                    >
                      {deletando === padrao.id ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : 'Sim'}
                    </button>
                    <button
                      onClick={() => onConfirmarDeletar(null)}
                      className="btn btn-secondary"
                      style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                    >
                      Não
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => onConfirmarDeletar(padrao.id)}
                    disabled={deletando === padrao.id}
                    className="btn btn-secondary"
                    style={{ padding: '5px 10px', fontSize: '0.8rem', color: 'var(--danger)', borderColor: 'var(--danger)' }}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
    </div>
  )
}

export default function Parametrizacao() {
  const [padroes, setPadroes] = useState<PadraoOportunidade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [novoNome, setNovoNome] = useState('')
  const [novaExpressao, setNovaExpressao] = useState('')
  const [novoTipo, setNovoTipo] = useState<Tipo>('positivo')
  const [adicionando, setAdicionando] = useState(false)
  const [salvando, setSalvando] = useState<number | null>(null)
  const [deletando, setDeletando] = useState<number | null>(null)
  const [reordenando, setReordenando] = useState(false)
  const [abaAtiva, setAbaAtiva] = useState<Tipo>('positivo')
  const [mostrarForm, setMostrarForm] = useState<Tipo | null>(null)
  const [confirmandoDeletar, setConfirmandoDeletar] = useState<number | null>(null)

  const padroesPos = padroes.filter(p => p.tipo === 'positivo')
  const padroesNeg = padroes.filter(p => p.tipo === 'negativo')

  const carregar = async () => {
    setError('')
    try {
      const data = await padroesApi.listar()
      setPadroes(data)
    } catch {
      setError('Erro ao carregar padrões. Verifique se a API está disponível.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { carregar() }, [])

  const toggleAtivo = async (padrao: PadraoOportunidade) => {
    setSalvando(padrao.id)
    try {
      const atualizado = await padroesApi.atualizar(padrao.id, { ativo: !padrao.ativo })
      setPadroes(prev => prev.map(p => p.id === padrao.id ? atualizado : p))
    } catch {
      setError('Erro ao atualizar padrão.')
    } finally {
      setSalvando(null)
    }
  }

  const mover = async (globalIdx: number, direcao: 'cima' | 'baixo') => {
    const tipo = padroes[globalIdx].tipo
    const grupo = padroes.filter(p => p.tipo === tipo)
    const localIdx = grupo.findIndex(p => p.id === padroes[globalIdx].id)
    const troca = direcao === 'cima' ? localIdx - 1 : localIdx + 1
    if (troca < 0 || troca >= grupo.length) return

    const novoGrupo = [...grupo]
    ;[novoGrupo[localIdx], novoGrupo[troca]] = [novoGrupo[troca], novoGrupo[localIdx]]

    // Reconstrói padroes mantendo a ordem do outro grupo intacta
    const outro = padroes.filter(p => p.tipo !== tipo)
    const novaLista = tipo === 'positivo' ? [...novoGrupo, ...outro] : [...outro, ...novoGrupo]
    setPadroes(novaLista)
    setReordenando(true)
    try {
      const atualizados = await padroesApi.reordenar(novoGrupo.map(p => p.id))
      // Aplica apenas os do grupo reordenado, mantendo o resto
      setPadroes(prev => prev.map(p => {
        const atualizado = atualizados.find(a => a.id === p.id)
        return atualizado ?? p
      }))
    } catch {
      setError('Erro ao reordenar padrões.')
      await carregar()
    } finally {
      setReordenando(false)
    }
  }

  const deletar = async (id: number) => {
    setDeletando(id)
    setConfirmandoDeletar(null)
    try {
      await padroesApi.deletar(id)
      setPadroes(prev => prev.filter(p => p.id !== id))
    } catch {
      setError('Erro ao deletar padrão.')
    } finally {
      setDeletando(null)
    }
  }

  const adicionar = async () => {
    if (!novoNome.trim() || !novaExpressao.trim()) return
    setAdicionando(true)
    try {
      const novo = await padroesApi.criar({ nome: novoNome.trim(), expressao: novaExpressao.trim(), tipo: novoTipo })
      setPadroes(prev => [...prev, novo])
      setNovoNome('')
      setNovaExpressao('')
      setMostrarForm(null)
    } catch {
      setError('Erro ao adicionar padrão.')
    } finally {
      setAdicionando(false)
    }
  }

  const abrirForm = (tipo: Tipo) => {
    setNovoTipo(tipo)
    setNovoNome('')
    setNovaExpressao('')
    setMostrarForm(tipo)
  }

  const [togglando, setTogglando] = useState(false)

  const toggleTodos = async () => {
    const grupo = abaAtiva === 'positivo' ? padroesPos : padroesNeg
    if (grupo.length === 0) return
    const novoEstado = !grupo.every(p => p.ativo)
    const paraAtualizar = grupo.filter(p => p.ativo !== novoEstado)
    setTogglando(true)
    try {
      const atualizados = await Promise.all(
        paraAtualizar.map(p => padroesApi.atualizar(p.id, { ativo: novoEstado }))
      )
      setPadroes(prev => prev.map(p => {
        const atualizado = atualizados.find(a => a.id === p.id)
        return atualizado ?? p
      }))
    } catch {
      setError('Erro ao atualizar padrões.')
    } finally {
      setTogglando(false)
    }
  }

  const secaoProps = {
    todos: padroes,
    reordenando,
    salvando,
    deletando,
    confirmandoDeletar,
    onToggle: toggleAtivo,
    onMover: mover,
    onDeletar: deletar,
    onConfirmarDeletar: setConfirmandoDeletar,
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Settings size={28} style={{ color: 'var(--primary)' }} />
          Parametrização
        </h1>
        <p className="page-subtitle">
          Configure as palavras-chave utilizadas na detecção de oportunidades de crédito.
        </p>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <AlertTriangle size={20} color="var(--danger)" />
          <span style={{ color: 'var(--danger)' }}>{error}</span>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-secondary)' }}>
          <Loader2 size={28} style={{ animation: 'spin 1s linear infinite' }} />
        </div>
      ) : (
        <>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {/* Abas */}
            <div style={{
              display: 'flex',
              alignItems: 'stretch',
              borderBottom: '1px solid var(--glass-border)',
              flexWrap: 'wrap',
            }}>
              {(['positivo', 'negativo'] as Tipo[]).map(tipo => {
                const ativa = abaAtiva === tipo
                const grupo = tipo === 'positivo' ? padroesPos : padroesNeg
                const Icon = tipo === 'positivo' ? TrendingUp : ShieldOff
                const cor = tipo === 'positivo' ? 'var(--success)' : 'var(--danger)'
                const label = tipo === 'positivo' ? 'Padrões Positivos' : 'Padrões Negativos'
                return (
                  <button
                    key={tipo}
                    onClick={() => { setAbaAtiva(tipo); setMostrarForm(null) }}
                    style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '16px 24px',
                      background: 'none',
                      border: 'none',
                      borderBottom: ativa ? `2px solid ${cor}` : '2px solid transparent',
                      cursor: 'pointer',
                      color: ativa ? cor : 'var(--text-muted)',
                      fontWeight: ativa ? 600 : 400,
                      fontSize: '0.92rem',
                      transition: 'color var(--transition-fast)',
                      marginBottom: -1,
                    }}
                  >
                    <Icon size={15} />
                    {label}
                    <span style={{
                      marginLeft: 4,
                      fontSize: '0.78rem',
                      color: 'var(--text-muted)',
                      fontWeight: 400,
                    }}>
                      {grupo.filter(p => p.ativo).length}/{grupo.length}
                    </span>
                    {reordenando && ativa && <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />}
                  </button>
                )
              })}

              {/* Botões à direita */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 24px' }}>
                {(() => {
                  const grupo = abaAtiva === 'positivo' ? padroesPos : padroesNeg
                  const todosAtivos = grupo.length > 0 && grupo.every(p => p.ativo)
                  return (
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '0.85rem', padding: '7px 16px', whiteSpace: 'nowrap' }}
                      onClick={toggleTodos}
                      disabled={togglando || grupo.length === 0}
                    >
                      {togglando
                        ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                        : null}
                      {todosAtivos ? 'Desmarcar todos' : 'Marcar todos'}
                    </button>
                  )
                })()}
                <button
                  className={abaAtiva === 'positivo' ? 'btn btn-primary' : 'btn btn-danger'}
                  style={{ fontSize: '0.85rem', padding: '7px 16px' }}
                  onClick={() => mostrarForm === abaAtiva ? setMostrarForm(null) : abrirForm(abaAtiva)}
                >
                  <Plus size={15} />
                  Adicionar
                </button>
              </div>
            </div>

            {/* Formulário */}
            {mostrarForm === abaAtiva && (
              <FormAdição
                nome={novoNome} expressao={novaExpressao} adicionando={adicionando}
                onNome={setNovoNome} onExpressao={setNovaExpressao}
                onSalvar={adicionar}
                onCancelar={() => setMostrarForm(null)}
              />
            )}

            {/* Conteúdo da aba */}
            {abaAtiva === 'positivo'
              ? <TabelaPadroes padroes={padroesPos} {...secaoProps} />
              : <TabelaPadroes padroes={padroesNeg} {...secaoProps} />
            }
          </div>

          <p style={{ marginTop: 16, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <strong>Positivos:</strong> publicações que contêm estas expressões são marcadas como oportunidade.
            A ordem define qual label aparece quando múltiplos padrões coincidem.{' '}
            <strong>Negativos:</strong> se uma publicação <em>posterior</em> contiver estas expressões,
            o processo é removido automaticamente dos resultados.
            Padrões inativos são ignorados.
          </p>
        </>
      )}
    </div>
  )
}

function FormAdição({
  nome, expressao, adicionando,
  onNome, onExpressao, onSalvar, onCancelar,
}: {
  nome: string; expressao: string; adicionando: boolean
  onNome: (v: string) => void; onExpressao: (v: string) => void
  onSalvar: () => void; onCancelar: () => void
}) {
  return (
    <div style={{
      padding: '16px 24px',
      borderBottom: '1px solid var(--glass-border)',
      background: 'var(--glass-border)',
      display: 'flex',
      gap: 12,
      alignItems: 'flex-end',
      flexWrap: 'wrap',
    }}>
      <div style={{ flex: '1 1 180px' }}>
        <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>
          Nome (label exibido)
        </label>
        <input
          className="input-field"
          style={{ margin: 0 }}
          placeholder="ex: Acordo Homologado"
          value={nome}
          onChange={e => onNome(e.target.value)}
        />
      </div>
      <div style={{ flex: '2 1 260px' }}>
        <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>
          Expressão buscada no texto
        </label>
        <input
          className="input-field"
          style={{ margin: 0 }}
          placeholder="ex: acordo homologado"
          value={expressao}
          onChange={e => onExpressao(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onSalvar()}
        />
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          className="btn btn-primary"
          onClick={onSalvar}
          disabled={adicionando || !nome.trim() || !expressao.trim()}
          style={{ fontSize: '0.85rem', padding: '8px 16px' }}
        >
          {adicionando
            ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
            : <Check size={14} />}
          Salvar
        </button>
        <button
          className="btn btn-secondary"
          onClick={onCancelar}
          style={{ fontSize: '0.85rem', padding: '8px 16px' }}
        >
          <X size={14} />
          Cancelar
        </button>
      </div>
    </div>
  )
}
