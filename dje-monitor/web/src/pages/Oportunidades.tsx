import { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import ReactMarkdown from 'react-markdown'
import { TrendingUp, Search, ExternalLink, FileText, AlertTriangle, Loader2, Clock, X, Calendar, ChevronDown, ChevronUp, Sparkles, UserX, RotateCcw } from 'lucide-react'
import api, { oportunidadesApi, OportunidadeItem } from '../services/api'

const PADROES_LABEL: Record<string, string> = {
  'mandado de levantamento': 'Mandado de Levantamento',
  'alvará de levantamento': 'Alvará de Levantamento',
  'alvará de pagamento': 'Alvará de Pagamento',
  'expedição de precatório': 'Expedição de Precatório',
  'precatório': 'Precatório',
  'rpv': 'RPV',
  'acordo homologado': 'Acordo Homologado',
  'desbloqueio': 'Desbloqueio',
  'ordem de pagamento': 'Ordem de Pagamento',
  'sinal de recebimento': 'Sinal de Recebimento',
}

const PADROES_COR: Record<string, { bg: string; color: string }> = {
  'mandado de levantamento':   { bg: 'var(--success-muted)', color: 'var(--success)' },
  'alvará de levantamento':    { bg: 'var(--success-muted)', color: 'var(--success)' },
  'alvará de pagamento':       { bg: 'var(--success-muted)', color: 'var(--success)' },
  'expedição de precatório':   { bg: 'var(--warning-muted)', color: 'var(--warning)' },
  'precatório':                { bg: 'var(--warning-muted)', color: 'var(--warning)' },
  'rpv':                       { bg: 'var(--success-muted)', color: 'var(--success)' },
  'acordo homologado':         { bg: 'var(--warning-muted)', color: 'var(--warning)' },
  'desbloqueio':               { bg: 'var(--accent-muted)',  color: 'var(--accent)'  },
  'ordem de pagamento':        { bg: 'var(--success-muted)', color: 'var(--success)' },
  'sinal de recebimento':      { bg: 'var(--accent-muted)',  color: 'var(--accent)'  },
}

const PERIODOS = [
  { label: 'Últimos 7 dias',  value: 7  },
  { label: 'Últimos 30 dias', value: 30 },
  { label: 'Últimos 60 dias', value: 60 },
  { label: 'Últimos 90 dias', value: 90 },
]

// ---------------------------------------------------------------------------
// Tipo e função de agrupamento
// ---------------------------------------------------------------------------

interface OportunidadeGrupo {
  key: string
  pessoa_id: number
  pessoa_nome: string
  tribunal: string
  numero_processo: string | null
  padroes: string[]
  polo_pessoa: string
  data_mais_recente: string
  total: number
  itens: OportunidadeItem[]
  // Classificação IA
  ia_papel: string | null
  ia_veredicto: string | null
  ia_valor: string | null
  ia_justificativa: string | null
  // Descarte manual
  descartado_por_usuario: boolean
}

function agruparPorProcesso(itens: OportunidadeItem[]): OportunidadeGrupo[] {
  const mapa = new Map<string, OportunidadeGrupo>()
  for (const item of itens) {
    const key = `${item.pessoa_id}__${item.numero_processo ?? ''}__${item.tribunal}`
    if (!mapa.has(key)) {
      mapa.set(key, {
        key,
        pessoa_id: item.pessoa_id,
        pessoa_nome: item.pessoa_nome,
        tribunal: item.tribunal,
        numero_processo: item.numero_processo ?? null,
        padroes: [],
        polo_pessoa: item.polo_pessoa ?? 'indefinido',
        data_mais_recente: item.data_disponibilizacao,
        total: 0,
        itens: [],
        ia_papel: item.ia_papel ?? null,
        ia_veredicto: item.ia_veredicto ?? null,
        ia_valor: item.ia_valor ?? null,
        ia_justificativa: item.ia_justificativa ?? null,
        descartado_por_usuario: item.descartado_por_usuario ?? false,
      })
    }
    const grupo = mapa.get(key)!
    grupo.itens.push(item)
    grupo.total++
    if (!grupo.padroes.includes(item.padrao_detectado)) {
      grupo.padroes.push(item.padrao_detectado)
    }
    if (item.data_disponibilizacao > grupo.data_mais_recente) {
      grupo.data_mais_recente = item.data_disponibilizacao
    }
  }
  return Array.from(mapa.values())
}

// ---------------------------------------------------------------------------
// Componentes auxiliares
// ---------------------------------------------------------------------------

function PadraoBadge({ padrao }: { padrao: string }) {
  const cor = PADROES_COR[padrao] ?? { bg: 'var(--accent-muted)', color: 'var(--accent)' }
  return (
    <span style={{
      padding: '3px 10px',
      borderRadius: 20,
      fontSize: '0.75rem',
      fontWeight: 600,
      background: cor.bg,
      color: cor.color,
      whiteSpace: 'nowrap',
    }}>
      {PADROES_LABEL[padrao] ?? padrao}
    </span>
  )
}

function GrupoCard({
  grupo,
  selecionado,
  onClick,
  formatarData,
  onDescartar,
  onRestaurar,
}: {
  grupo: OportunidadeGrupo
  selecionado: boolean
  onClick: () => void
  formatarData: (data: string) => string
  onDescartar: (grupo: OportunidadeGrupo) => void
  onRestaurar: (grupo: OportunidadeGrupo) => void
}) {
  const [hovered, setHovered] = useState(false)
  const primeiroItem = grupo.itens[0]
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--glass-bg)',
        border: `1px solid ${selecionado ? 'var(--warning)' : 'var(--glass-border)'}`,
        borderRadius: 'var(--radius-lg)',
        padding: '18px 24px',
        cursor: 'pointer',
        transition: 'border-color var(--transition-fast), background var(--transition-fast)',
        position: 'relative',
      }}
      onMouseEnter={e => { if (!selecionado) e.currentTarget.style.borderColor = 'var(--warning)'; setHovered(true) }}
      onMouseLeave={e => { if (!selecionado) e.currentTarget.style.borderColor = 'var(--glass-border)'; setHovered(false) }}
    >
      {/* Cabeçalho */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: '0.97rem', color: 'var(--text-primary)' }}>
              {grupo.pessoa_nome}
            </span>
            {grupo.tribunal && (
              <span style={{
                background: 'var(--primary-muted)',
                color: 'var(--primary)',
                borderRadius: 6,
                padding: '2px 8px',
                fontSize: '0.73rem',
                fontWeight: 600,
              }}>
                {grupo.tribunal}
              </span>
            )}
            {(() => {
              // Usa classificação IA quando disponível, senão fallback polo_pessoa
              const papelIA = grupo.ia_papel
              const info = papelIA
                ? PAPEL_INFO[papelIA] ?? { label: papelIA, bg: 'var(--glass-border)', color: 'var(--text-muted)' }
                : grupo.polo_pessoa === 'ativo'
                  ? { label: 'Credor', bg: 'var(--success-muted)', color: 'var(--success)' }
                  : { label: 'Polo indefinido', bg: 'var(--glass-border)', color: 'var(--text-muted)' }
              return (
                <span style={{
                  background: info.bg,
                  color: info.color,
                  borderRadius: 6,
                  padding: '2px 8px',
                  fontSize: '0.73rem',
                  fontWeight: 600,
                }}>
                  {papelIA ? `${info.label} (IA)` : info.label}
                </span>
              )
            })()}
            {grupo.ia_veredicto && (() => {
              const vInfo = VEREDICTO_INFO[grupo.ia_veredicto]
              return vInfo ? (
                <span style={{
                  background: vInfo.bg,
                  color: vInfo.color,
                  borderRadius: 6,
                  padding: '2px 8px',
                  fontSize: '0.73rem',
                  fontWeight: 600,
                }}>
                  {vInfo.label}
                </span>
              ) : null
            })()}
            {grupo.total > 1 && (
              <span style={{
                background: 'var(--glass-border)',
                color: 'var(--text-secondary)',
                borderRadius: 6,
                padding: '2px 8px',
                fontSize: '0.73rem',
                fontWeight: 600,
              }}>
                {grupo.total} publicações
              </span>
            )}
          </div>
          {grupo.numero_processo && (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.83rem', fontFamily: 'monospace' }}>
              {grupo.numero_processo}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {grupo.padroes.map(p => <PadraoBadge key={p} padrao={p} />)}
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {formatarData(grupo.data_mais_recente)}
          </span>
        </div>
      </div>

      {/* Trecho do texto mais recente */}
      {primeiroItem.texto_resumo && (
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '0.86rem',
          lineHeight: 1.6,
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          marginBottom: 10,
        }}>
          {primeiroItem.texto_resumo}
        </p>
      )}

      {/* Rodapé */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{primeiroItem.orgao}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {hovered && (
            grupo.descartado_por_usuario ? (
              <button
                onClick={e => { e.stopPropagation(); onRestaurar(grupo) }}
                title="Restaurar processo"
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '3px 9px', borderRadius: 6,
                  border: '1px solid var(--glass-border)',
                  background: 'var(--glass-bg)', color: 'var(--text-secondary)',
                  fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                }}
              >
                <RotateCcw size={12} /> Restaurar
              </button>
            ) : (
              <button
                onClick={e => { e.stopPropagation(); onDescartar(grupo) }}
                title="Descartar este processo"
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '3px 9px', borderRadius: 6,
                  border: '1px solid var(--danger, #dc2626)',
                  background: 'var(--danger-muted, #fee2e2)', color: 'var(--danger, #dc2626)',
                  fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                }}
              >
                <UserX size={12} /> Descartar
              </button>
            )
          )}
          <span style={{ fontSize: '0.78rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: 4 }}>
            {grupo.total > 1 ? `Ver ${grupo.total} publicações →` : 'Ver detalhes →'}
          </span>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Item expansível no drawer
// ---------------------------------------------------------------------------

function PublicacaoDrawerItem({
  item,
  formatarData,
  abrirProcesso,
}: {
  item: OportunidadeItem
  formatarData: (data: string) => string
  abrirProcesso: (numero: string, tribunal: string) => void
}) {
  const [expandido, setExpandido] = useState(false)
  const cor = PADROES_COR[item.padrao_detectado] ?? { bg: 'var(--warning-muted)', color: 'var(--warning)' }

  return (
    <div style={{
      border: '1px solid var(--glass-border)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
    }}>
      {/* Header do item */}
      <div
        onClick={() => setExpandido(v => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          padding: '12px 16px',
          cursor: 'pointer',
          background: expandido ? 'var(--glass-border)' : 'transparent',
          transition: 'background var(--transition-fast)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>
          <span style={{
            padding: '2px 9px',
            borderRadius: 20,
            fontSize: '0.72rem',
            fontWeight: 600,
            background: cor.bg,
            color: cor.color,
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}>
            {PADROES_LABEL[item.padrao_detectado] ?? item.padrao_detectado}
          </span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Calendar size={12} />
            {formatarData(item.data_disponibilizacao)}
          </span>
          {item.score_semantico !== undefined && item.score_semantico > 0 && (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }} title="Relevância semântica">
              {Math.round(item.score_semantico * 100)}%
            </span>
          )}
          {item.orgao && (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {item.orgao}
            </span>
          )}
        </div>
        {expandido ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
      </div>

      {/* Conteúdo expandido */}
      {expandido && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--glass-border)' }}>
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '0.86rem',
            lineHeight: 1.75,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            marginBottom: 12,
          }}>
            {item.texto_completo || item.texto_resumo || '—'}
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            {item.link && (
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
                style={{ fontSize: '0.8rem', padding: '5px 12px' }}
                onClick={e => e.stopPropagation()}
              >
                <FileText size={13} />
                Ver publicação
              </a>
            )}
            {item.numero_processo && (
              <button
                onClick={e => { e.stopPropagation(); abrirProcesso(item.numero_processo, item.tribunal) }}
                className="btn btn-secondary"
                style={{ fontSize: '0.8rem', padding: '5px 12px' }}
              >
                <ExternalLink size={13} />
                Abrir processo
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Resumo IA — card com badges e markdown
// ---------------------------------------------------------------------------

const VEREDICTO_INFO: Record<string, { label: string; bg: string; color: string }> = {
  CREDITO_IDENTIFICADO: { label: 'Crédito Identificado', bg: 'var(--success-muted)', color: 'var(--success)' },
  CREDITO_POSSIVEL:     { label: 'Crédito Possível',     bg: 'var(--warning-muted)', color: 'var(--warning)' },
  SEM_CREDITO:          { label: 'Sem Crédito',          bg: 'var(--danger-muted, #fee2e2)', color: 'var(--danger, #dc2626)' },
}

const PAPEL_INFO: Record<string, { label: string; bg: string; color: string }> = {
  CREDOR:    { label: 'Credor',          bg: 'var(--success-muted)',        color: 'var(--success)'        },
  DEVEDOR:   { label: 'Devedor',         bg: 'var(--danger-muted, #fee2e2)', color: 'var(--danger, #dc2626)' },
  INDEFINIDO: { label: 'Papel indefinido', bg: 'var(--glass-border)',       color: 'var(--text-muted)'     },
}

function ResumoCard({
  resumo,
  meta,
  fromCache,
}: {
  resumo: string
  meta: { veredicto: string | null; papel: string | null; valor: string | null } | null
  fromCache: boolean
}) {
  const veredictoInfo = meta?.veredicto ? VEREDICTO_INFO[meta.veredicto] : null
  const papelInfo = meta?.papel ? PAPEL_INFO[meta.papel] : null
  const temValor = meta?.valor && meta.valor.toLowerCase() !== 'não identificado'

  return (
    <div style={{ marginTop: 14 }}>
      {/* Badges de metadados */}
      {(veredictoInfo || papelInfo || temValor || fromCache) && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10, alignItems: 'center' }}>
          {veredictoInfo && (
            <span style={{
              padding: '3px 10px', borderRadius: 20,
              fontSize: '0.73rem', fontWeight: 700,
              background: veredictoInfo.bg, color: veredictoInfo.color,
            }}>
              {veredictoInfo.label}
            </span>
          )}
          {papelInfo && (
            <span style={{
              padding: '3px 10px', borderRadius: 20,
              fontSize: '0.73rem', fontWeight: 600,
              background: papelInfo.bg, color: papelInfo.color,
            }}>
              {papelInfo.label}
            </span>
          )}
          {temValor && (
            <span style={{
              padding: '3px 10px', borderRadius: 20,
              fontSize: '0.73rem', fontWeight: 600,
              background: 'var(--primary-muted)', color: 'var(--primary)',
            }}>
              {meta!.valor}
            </span>
          )}
          {fromCache && (
            <span style={{
              marginLeft: 'auto',
              fontSize: '0.7rem', color: 'var(--text-muted)',
              display: 'flex', alignItems: 'center', gap: 4,
            }} title="Resultado salvo em cache — nenhuma chamada à OpenAI foi feita">
              ⚡ cache
            </span>
          )}
        </div>
      )}

      {/* Resumo em Markdown */}
      <div
        className="resumo-ia"
        style={{
          background: 'var(--glass-bg)',
          border: '1px solid var(--glass-border)',
          borderRadius: 10,
          padding: '14px 18px',
        }}
      >
        <ReactMarkdown>{resumo}</ReactMarkdown>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

type Ordenacao = 'data_desc' | 'data_asc' | 'nome' | 'publicacoes'

const ORDENACOES: { value: Ordenacao; label: string }[] = [
  { value: 'data_desc', label: 'Mais recente' },
  { value: 'data_asc',  label: 'Mais antigo'  },
  { value: 'nome',      label: 'Nome (A→Z)'   },
  { value: 'publicacoes', label: 'Mais publicações' },
]

/** Converte dd/mm/yyyy ou yyyy-mm-dd para yyyy-mm-dd (comparável como string). */
function dataSortavel(d: string): string {
  if (!d) return '0000-00-00'
  if (d.length === 10 && d[4] === '-') return d // já yyyy-mm-dd
  const p = d.split('/')
  if (p.length === 3) return `${p[2]}-${p[1]}-${p[0]}`
  return d
}

function ordenarGrupos(grupos: OportunidadeGrupo[], ord: Ordenacao): OportunidadeGrupo[] {
  return [...grupos].sort((a, b) => {
    if (ord === 'data_desc') return dataSortavel(b.data_mais_recente).localeCompare(dataSortavel(a.data_mais_recente))
    if (ord === 'data_asc')  return dataSortavel(a.data_mais_recente).localeCompare(dataSortavel(b.data_mais_recente))
    if (ord === 'nome')      return a.pessoa_nome.localeCompare(b.pessoa_nome, 'pt-BR')
    if (ord === 'publicacoes') return b.total - a.total
    return 0
  })
}

export default function Oportunidades() {
  const [dias, setDias] = useState(30)
  const [itens, setItens] = useState<OportunidadeItem[]>([])
  const [loading, setLoading] = useState(false)
  const [varrendo, setVarrendo] = useState(false)
  const [error, setError] = useState('')
  const [buscou, setBuscou] = useState(false)
  const [novasOportunidades, setNovasOportunidades] = useState(0)
  const [grupoSelecionado, setGrupoSelecionado] = useState<OportunidadeGrupo | null>(null)
  const [resumo, setResumo] = useState<string | null>(null)
  const [resumoMeta, setResumoMeta] = useState<{ veredicto: string | null; papel: string | null; valor: string | null } | null>(null)
  const [resumoFromCache, setResumoFromCache] = useState<boolean | null>(null)
  const [resumoLoading, setResumoLoading] = useState(false)
  const [resumoErro, setResumoErro] = useState('')
  const [filtroNome, setFiltroNome] = useState('')
  const [filtroProcesso, setFiltroProcesso] = useState('')
  const [ordenacao, setOrdenacao] = useState<Ordenacao>('data_desc')
  const [abaAtiva, setAbaAtiva] = useState<'oportunidades' | 'descartados' | 'descartados_usuario'>('oportunidades')
  const scrollPosRef = useRef(0)

  const todosGrupos = agruparPorProcesso(itens).filter(g => {
    const nome = filtroNome.trim().toLowerCase()
    const proc = filtroProcesso.trim().toLowerCase()
    if (nome && !g.pessoa_nome.toLowerCase().includes(nome)) return false
    if (proc && !(g.numero_processo ?? '').toLowerCase().includes(proc)) return false
    return true
  })

  // Três categorias: descartado pelo usuário > descartado pela IA > oportunidade
  const isDescartadoUsuario = (g: OportunidadeGrupo) => g.descartado_por_usuario === true
  const isDescartadoIA = (g: OportunidadeGrupo) =>
    !isDescartadoUsuario(g) && (g.ia_papel === 'DEVEDOR' || g.ia_veredicto === 'SEM_CREDITO')

  const gruposOportunidades = todosGrupos.filter(g => !isDescartadoUsuario(g) && !isDescartadoIA(g))
  const gruposDescartados = todosGrupos.filter(g => isDescartadoIA(g))
  const gruposDescartadosUsuario = todosGrupos.filter(g => isDescartadoUsuario(g))

  const grupos = ordenarGrupos(
    abaAtiva === 'oportunidades'
      ? gruposOportunidades
      : abaAtiva === 'descartados'
        ? gruposDescartados
        : gruposDescartadosUsuario,
    ordenacao
  )

  // Lock/unlock scroll quando o drawer está aberto
  useEffect(() => {
    if (grupoSelecionado) {
      scrollPosRef.current = window.scrollY
      document.body.style.position = 'fixed'
      document.body.style.top = `-${scrollPosRef.current}px`
      document.body.style.left = '0'
      document.body.style.right = '0'
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.left = ''
      document.body.style.right = ''
      document.body.style.overflow = ''
      window.scrollTo(0, scrollPosRef.current)
    }
    return () => {
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.left = ''
      document.body.style.right = ''
      document.body.style.overflow = ''
    }
  }, [grupoSelecionado])

  const buscar = useCallback(async (diasSelecionados: number) => {
    setError('')
    setLoading(true)
    setBuscou(true)
    try {
      const resp = await oportunidadesApi.buscar({ dias: diasSelecionados, limit: 200, semantico: true })
      setItens(resp.items)
    } catch {
      setError('Erro ao buscar oportunidades. Verifique se a API está disponível.')
    } finally {
      setLoading(false)
    }
  }, [])

  const varrerAgora = async () => {
    setVarrendo(true)
    setError('')
    try {
      await oportunidadesApi.varrer()
      // Aguardar classificação LLM processar (varredura + classificação ~10-15s)
      await new Promise(r => setTimeout(r, 12000))
      await buscar(dias)
    } catch {
      setError('Erro ao iniciar varredura.')
    } finally {
      setVarrendo(false)
    }
  }

  const handleDescartar = async (grupo: OportunidadeGrupo) => {
    if (!grupo.numero_processo) return
    try {
      await oportunidadesApi.descartar(grupo.pessoa_id, grupo.numero_processo)
      setItens(prev => prev.map(item =>
        item.pessoa_id === grupo.pessoa_id && item.numero_processo === grupo.numero_processo
          ? { ...item, descartado_por_usuario: true }
          : item
      ))
      if (grupoSelecionado?.key === grupo.key) setGrupoSelecionado(null)
    } catch {
      setError('Erro ao descartar processo.')
    }
  }

  const handleRestaurar = async (grupo: OportunidadeGrupo) => {
    if (!grupo.numero_processo) return
    try {
      await oportunidadesApi.restaurar(grupo.pessoa_id, grupo.numero_processo)
      setItens(prev => prev.map(item =>
        item.pessoa_id === grupo.pessoa_id && item.numero_processo === grupo.numero_processo
          ? { ...item, descartado_por_usuario: false }
          : item
      ))
      if (grupoSelecionado?.key === grupo.key) setGrupoSelecionado(null)
    } catch {
      setError('Erro ao restaurar processo.')
    }
  }

  // Badge de novas oportunidades
  useEffect(() => {
    api.get<{ count: number }>('/v1/alertas/nao-lidos/count', { params: { tipo: 'OPORTUNIDADE_CREDITO' } })
      .then(r => setNovasOportunidades(r.data.count ?? 0))
      .catch(() => {})
  }, [])

  // Carrega automaticamente ao montar
  useEffect(() => { buscar(dias) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const formatarData = (data: string) => {
    if (!data) return '—'
    if (data.includes('/')) return data
    const [y, m, d] = data.split('-')
    return `${d}/${m}/${y}`
  }

  const abrirProcesso = (numero: string, tribunal: string) => {
    const params = new URLSearchParams({ nome: numero, tribunal })
    window.open(`/busca?${params.toString()}`, '_blank')
  }

  const corDrawer = grupoSelecionado
    ? (PADROES_COR[grupoSelecionado.padroes[0]] ?? { bg: 'var(--warning-muted)', color: 'var(--warning)' })
    : { bg: 'var(--warning-muted)', color: 'var(--warning)' }

  return (
    <div className="animate-fadeIn">
      {/* Cabeçalho */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <TrendingUp size={28} style={{ color: 'var(--warning)' }} />
              Oportunidades de Crédito
              {novasOportunidades > 0 && (
                <span style={{
                  background: 'var(--warning)',
                  color: '#000',
                  borderRadius: 20,
                  padding: '2px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}>
                  {novasOportunidades} nova{novasOportunidades > 1 ? 's' : ''}
                </span>
              )}
            </h1>
            <p className="page-subtitle">
              Publicações de devedores monitorados com sinais de recebimento de valores —
              alvarás, mandados de levantamento e precatórios.
            </p>
          </div>
          <button
            onClick={varrerAgora}
            disabled={varrendo}
            className="btn btn-secondary"
            style={{ whiteSpace: 'nowrap', flexShrink: 0 }}
          >
            {varrendo
              ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
              : <Sparkles size={16} />}
            {varrendo ? 'Analisando...' : 'Analisar processos'}
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div className="search-section">
        <div className="search-form-row">
          <div className="search-input-wrapper tribunal" style={{ flex: '0 0 200px' }}>
            <label className="search-field-label">
              <Clock size={13} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
              Período
            </label>
            <div style={{ position: 'relative' }}>
              <select
                className="input-field"
                style={{ appearance: 'none', cursor: 'pointer', paddingRight: 32 }}
                value={dias}
                onChange={e => setDias(Number(e.target.value))}
              >
                {PERIODOS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }}>
                <svg width="10" height="6" viewBox="0 0 10 6" fill="none"><path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </div>
            </div>
          </div>

          <div className="search-input-wrapper" style={{ flex: 1 }}>
            <label className="search-field-label">Nome da parte</label>
            <input
              className="input-field"
              type="text"
              placeholder="Filtrar por nome..."
              value={filtroNome}
              onChange={e => setFiltroNome(e.target.value)}
            />
          </div>

          <div className="search-input-wrapper" style={{ flex: 1 }}>
            <label className="search-field-label">Número do processo</label>
            <input
              className="input-field"
              type="text"
              placeholder="Filtrar por processo..."
              value={filtroProcesso}
              onChange={e => setFiltroProcesso(e.target.value)}
            />
          </div>

          <div className="search-actions">
            <button
              onClick={() => buscar(dias)}
              disabled={loading}
              className="btn btn-primary search-btn-large"
            >
              {loading ? <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : <Search size={18} />}
              {loading ? '' : 'Buscar'}
            </button>
          </div>
        </div>
      </div>

      {/* Erro */}
      {error && (
        <div className="card mb-6" style={{ borderColor: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <AlertTriangle size={20} color="var(--danger)" />
          <span style={{ color: 'var(--danger)' }}>{error}</span>
        </div>
      )}

      {/* Abas */}
      {buscou && !loading && todosGrupos.length > 0 && (
        <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '2px solid var(--glass-border)' }}>
          <button
            onClick={() => setAbaAtiva('oportunidades')}
            style={{
              padding: '10px 20px',
              fontSize: '0.9rem',
              fontWeight: abaAtiva === 'oportunidades' ? 700 : 500,
              color: abaAtiva === 'oportunidades' ? 'var(--warning)' : 'var(--text-muted)',
              background: 'transparent',
              border: 'none',
              borderBottom: abaAtiva === 'oportunidades' ? '2px solid var(--warning)' : '2px solid transparent',
              marginBottom: -2,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <TrendingUp size={16} />
            Oportunidades
            <span style={{
              background: abaAtiva === 'oportunidades' ? 'var(--warning)' : 'var(--glass-border)',
              color: abaAtiva === 'oportunidades' ? '#000' : 'var(--text-muted)',
              borderRadius: 10,
              padding: '1px 8px',
              fontSize: '0.75rem',
              fontWeight: 700,
            }}>
              {gruposOportunidades.length}
            </span>
          </button>
          <button
            onClick={() => setAbaAtiva('descartados')}
            style={{
              padding: '10px 20px',
              fontSize: '0.9rem',
              fontWeight: abaAtiva === 'descartados' ? 700 : 500,
              color: abaAtiva === 'descartados' ? 'var(--danger, #dc2626)' : 'var(--text-muted)',
              background: 'transparent',
              border: 'none',
              borderBottom: abaAtiva === 'descartados' ? '2px solid var(--danger, #dc2626)' : '2px solid transparent',
              marginBottom: -2,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <AlertTriangle size={16} />
            Descartados pela IA
            {gruposDescartados.length > 0 && (
              <span style={{
                background: abaAtiva === 'descartados' ? 'var(--danger-muted, #fee2e2)' : 'var(--glass-border)',
                color: abaAtiva === 'descartados' ? 'var(--danger, #dc2626)' : 'var(--text-muted)',
                borderRadius: 10,
                padding: '1px 8px',
                fontSize: '0.75rem',
                fontWeight: 700,
              }}>
                {gruposDescartados.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setAbaAtiva('descartados_usuario')}
            style={{
              padding: '10px 20px',
              fontSize: '0.9rem',
              fontWeight: abaAtiva === 'descartados_usuario' ? 700 : 500,
              color: abaAtiva === 'descartados_usuario' ? 'var(--text-secondary)' : 'var(--text-muted)',
              background: 'transparent',
              border: 'none',
              borderBottom: abaAtiva === 'descartados_usuario' ? '2px solid var(--text-secondary)' : '2px solid transparent',
              marginBottom: -2,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <UserX size={16} />
            Descartados por mim
            {gruposDescartadosUsuario.length > 0 && (
              <span style={{
                background: 'var(--glass-border)',
                color: 'var(--text-muted)',
                borderRadius: 10,
                padding: '1px 8px',
                fontSize: '0.75rem',
                fontWeight: 700,
              }}>
                {gruposDescartadosUsuario.length}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Resultados */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-secondary)' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Varrendo publicações...</p>
        </div>
      ) : buscou && grupos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-secondary)' }}>
          {abaAtiva === 'descartados' ? (
            <>
              <AlertTriangle size={40} style={{ marginBottom: 16, opacity: 0.3 }} />
              <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>Nenhum processo descartado pela IA</p>
              <p style={{ fontSize: '0.9rem', opacity: 0.7 }}>
                Processos classificados como "Devedor" ou "Sem Crédito" aparecerão aqui.
              </p>
            </>
          ) : abaAtiva === 'descartados_usuario' ? (
            <>
              <UserX size={40} style={{ marginBottom: 16, opacity: 0.3 }} />
              <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>Nenhum processo descartado por você</p>
              <p style={{ fontSize: '0.9rem', opacity: 0.7 }}>
                Passe o mouse sobre um card e clique em "Descartar" para mover processos irrelevantes para cá.
              </p>
            </>
          ) : (
            <>
              <TrendingUp size={40} style={{ marginBottom: 16, opacity: 0.3 }} />
              <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>Nenhuma oportunidade detectada</p>
              <p style={{ fontSize: '0.9rem', opacity: 0.7 }}>
                Nenhuma publicação no período selecionado contém sinais de recebimento de valores.
              </p>
            </>
          )}
        </div>
      ) : grupos.length > 0 ? (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {abaAtiva === 'oportunidades'
                ? <TrendingUp size={16} style={{ color: 'var(--warning)' }} />
                : abaAtiva === 'descartados'
                  ? <AlertTriangle size={16} style={{ color: 'var(--danger, #dc2626)' }} />
                  : <UserX size={16} style={{ color: 'var(--text-secondary)' }} />}
              <span>
                <strong style={{ color: abaAtiva === 'oportunidades' ? 'var(--warning)' : abaAtiva === 'descartados' ? 'var(--danger, #dc2626)' : 'var(--text-secondary)' }}>{grupos.length}</strong> processo{grupos.length !== 1 ? 's' : ''} {abaAtiva === 'oportunidades' ? 'com oportunidades' : abaAtiva === 'descartados' ? 'descartados pela IA' : 'descartados por você'}
                {(() => {
                  const totalPubs = grupos.reduce((acc, g) => acc + g.total, 0)
                  return totalPubs !== grupos.length
                    ? <span style={{ marginLeft: 6, color: 'var(--text-muted)' }}>({totalPubs} publicações)</span>
                    : null
                })()}
                {(filtroNome || filtroProcesso) && (
                  <span style={{ marginLeft: 8, color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                    — filtrado de {todosGrupos.length} processos
                  </span>
                )}
              </span>
            </div>
            <div style={{ position: 'relative' }}>
              <select
                className="input-field"
                style={{ appearance: 'none', cursor: 'pointer', paddingRight: 32, fontSize: '0.82rem', padding: '6px 32px 6px 12px' }}
                value={ordenacao}
                onChange={e => setOrdenacao(e.target.value as Ordenacao)}
              >
                {ORDENACOES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <div style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }}>
                <svg width="10" height="6" viewBox="0 0 10 6" fill="none"><path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {grupos.map(grupo => (
              <GrupoCard
                key={grupo.key}
                grupo={grupo}
                selecionado={grupoSelecionado?.key === grupo.key}
                onClick={() => { setGrupoSelecionado(grupo); setResumo(null); setResumoMeta(null); setResumoFromCache(null); setResumoErro('') }}
                formatarData={formatarData}
                onDescartar={handleDescartar}
                onRestaurar={handleRestaurar}
              />
            ))}
          </div>
        </>
      ) : null}

      {/* Drawer lateral */}
      {grupoSelecionado && createPortal(
        <>
          <div className="drawer-overlay" onClick={() => setGrupoSelecionado(null)} />
          <div className="drawer-container animate-slideInRight">
            {/* Header */}
            <div className="drawer-header">
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, flex: 1, minWidth: 0 }}>
                <div className="drawer-header-icon" style={{ background: corDrawer.bg, color: corDrawer.color }}>
                  <TrendingUp size={22} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                    <h3 className="drawer-title" style={{ margin: 0 }}>{grupoSelecionado.pessoa_nome}</h3>
                    {grupoSelecionado.tribunal && (
                      <span style={{
                        background: 'var(--primary-muted)',
                        color: 'var(--primary)',
                        borderRadius: 6,
                        padding: '1px 7px',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                      }}>{grupoSelecionado.tribunal}</span>
                    )}
                  </div>
                  <p className="drawer-processo-numero" style={{ margin: 0 }}>
                    {grupoSelecionado.numero_processo || '—'}
                  </p>
                  {/* Badges IA no drawer */}
                  {(grupoSelecionado.ia_papel || grupoSelecionado.ia_veredicto || grupoSelecionado.ia_valor) && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                      {grupoSelecionado.ia_papel && (() => {
                        const info = PAPEL_INFO[grupoSelecionado.ia_papel]
                        return info ? (
                          <span style={{
                            padding: '2px 9px', borderRadius: 20,
                            fontSize: '0.72rem', fontWeight: 600,
                            background: info.bg, color: info.color,
                          }}>
                            {info.label} (IA)
                          </span>
                        ) : null
                      })()}
                      {grupoSelecionado.ia_veredicto && (() => {
                        const info = VEREDICTO_INFO[grupoSelecionado.ia_veredicto]
                        return info ? (
                          <span style={{
                            padding: '2px 9px', borderRadius: 20,
                            fontSize: '0.72rem', fontWeight: 600,
                            background: info.bg, color: info.color,
                          }}>
                            {info.label}
                          </span>
                        ) : null
                      })()}
                      {grupoSelecionado.ia_valor && grupoSelecionado.ia_valor.toLowerCase() !== 'não identificado' && (
                        <span style={{
                          padding: '2px 9px', borderRadius: 20,
                          fontSize: '0.72rem', fontWeight: 600,
                          background: 'var(--primary-muted)', color: 'var(--primary)',
                        }}>
                          {grupoSelecionado.ia_valor}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <button onClick={() => setGrupoSelecionado(null)} className="drawer-close-btn" title="Fechar">
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <div className="drawer-body custom-scrollbar">
              {/* Badges dos padrões */}
              <div style={{ padding: '20px 24px 16px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {grupoSelecionado.padroes.map(p => <PadraoBadge key={p} padrao={p} />)}
              </div>

              {/* Resumo IA */}
              <div style={{ padding: '0 24px 16px' }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 0 }}>
                <button
                  onClick={async () => {
                    if (!grupoSelecionado.numero_processo) return
                    setResumo(null)
                    setResumoErro('')
                    setResumoLoading(true)
                    try {
                      const res = await oportunidadesApi.resumo(
                        grupoSelecionado.pessoa_id,
                        grupoSelecionado.numero_processo,
                      )
                      setResumo(res.resumo)
                      setResumoMeta({ veredicto: res.veredicto, papel: res.papel, valor: res.valor })
                      setResumoFromCache(res.cache ?? false)
                    } catch (e: any) {
                      setResumoErro(e?.response?.data?.detail || 'Erro ao gerar resumo.')
                    } finally {
                      setResumoLoading(false)
                    }
                  }}
                  disabled={resumoLoading || !grupoSelecionado.numero_processo}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 7,
                    padding: '8px 16px',
                    borderRadius: 8,
                    border: '1px solid var(--primary)',
                    background: 'var(--primary-muted)',
                    color: 'var(--primary)',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: resumoLoading ? 'wait' : 'pointer',
                    opacity: resumoLoading ? 0.7 : 1,
                  }}
                >
                  {resumoLoading
                    ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
                    : <Sparkles size={15} />}
                  {resumoLoading ? 'Gerando resumo…' : 'Resumir processo'}
                </button>

                {grupoSelecionado.numero_processo && (
                  <button
                    onClick={() => abrirProcesso(grupoSelecionado.numero_processo!, grupoSelecionado.tribunal)}
                    className="btn btn-secondary"
                    style={{ fontSize: '0.85rem', padding: '8px 16px' }}
                  >
                    <ExternalLink size={15} />
                    Abrir processo
                  </button>
                )}
                {grupoSelecionado.descartado_por_usuario ? (
                  <button
                    onClick={() => handleRestaurar(grupoSelecionado)}
                    className="btn btn-secondary"
                    style={{ fontSize: '0.85rem', padding: '8px 16px' }}
                  >
                    <RotateCcw size={15} />
                    Restaurar
                  </button>
                ) : (
                  <button
                    onClick={() => handleDescartar(grupoSelecionado)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 7,
                      fontSize: '0.85rem', padding: '8px 16px',
                      borderRadius: 8,
                      border: '1px solid var(--danger, #dc2626)',
                      background: 'var(--danger-muted, #fee2e2)',
                      color: 'var(--danger, #dc2626)',
                      fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    <UserX size={15} />
                    Descartar
                  </button>
                )}
                </div>

                {resumoErro && (
                  <div style={{
                    marginTop: 12,
                    padding: '10px 14px',
                    borderRadius: 8,
                    background: 'var(--error-muted, #fee)',
                    color: 'var(--error, #c00)',
                    fontSize: '0.85rem',
                  }}>
                    {resumoErro}
                  </div>
                )}

                {resumo && <ResumoCard resumo={resumo} meta={resumoMeta} fromCache={resumoFromCache ?? false} />}
              </div>

              {/* Lista de publicações */}
              <div className="drawer-section">
                <div className="drawer-section-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FileText size={16} />
                    <span>
                      {grupoSelecionado.total} publicaç{grupoSelecionado.total !== 1 ? 'ões' : 'ão'}
                    </span>
                  </div>
                </div>
                <div style={{ padding: '12px 24px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {[...grupoSelecionado.itens].sort((a, b) => dataSortavel(b.data_disponibilizacao).localeCompare(dataSortavel(a.data_disponibilizacao))).map(item => (
                    <PublicacaoDrawerItem
                      key={item.id}
                      item={item}
                      formatarData={formatarData}
                      abrirProcesso={abrirProcesso}
                    />
                  ))}
                </div>
              </div>

              <div style={{ height: 32 }} />
            </div>
          </div>
        </>,
        document.body
      )}
    </div>
  )
}
