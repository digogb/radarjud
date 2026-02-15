import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff, Users, FileText, Clock, DollarSign, Building, ChevronDown, ChevronUp } from 'lucide-react'
import { processoApi, Processo, Movimentacao } from '../services/api'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function ProcessoDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [processo, setProcesso] = useState<Processo | null>(null)
  const [movimentacoes, setMovimentacoes] = useState<Movimentacao[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'info' | 'partes' | 'movimentacoes'>('info')
  const [instanciasExpandidas, setInstanciasExpandidas] = useState<Set<string>>(new Set(['G1', 'G2'])) // Todas expandidas por padrão

  useEffect(() => {
    if (id) {
      loadProcesso()
    }
  }, [id])

  const loadProcesso = async () => {
    try {
      setLoading(true)
      const [processoData, movimentacoesData] = await Promise.all([
        processoApi.obterPorId(id!),
        processoApi.obterMovimentacoes(id!),
      ])
      setProcesso(processoData)
      setMovimentacoes(movimentacoesData)
    } catch (error) {
      console.error('Erro ao carregar processo:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleMonitoramento = async () => {
    if (!processo) return

    try {
      if (processo.id) {
        if (processo.monitorado) {
          await processoApi.desmonitorar(processo.id)
        } else {
          await processoApi.monitorar(processo.id)
        }
        setProcesso({ ...processo, monitorado: !processo.monitorado })
      }
    } catch (err) {
      console.error('Erro ao atualizar monitoramento:', err)
    }
  }

  const toggleInstancia = (grau: string) => {
    setInstanciasExpandidas(prev => {
      const newSet = new Set(prev)
      if (newSet.has(grau)) {
        newSet.delete(grau)
      } else {
        newSet.add(grau)
      }
      return newSet
    })
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span className="loading-text">Carregando processo...</span>
      </div>
    )
  }

  if (!processo) {
    return (
      <div className="empty-state">
        <div className="empty-icon">
          <FileText size={32} />
        </div>
        <h3 className="empty-title">Processo não encontrado</h3>
        <button className="btn btn-primary" onClick={() => navigate('/busca')}>
          Voltar para busca
        </button>
      </div>
    )
  }

  const autores = processo.partes?.filter((p) => p.polo === 'ATIVO') || []
  const reus = processo.partes?.filter((p) => p.polo === 'PASSIVO') || []

  return (
    <div className="animate-fadeIn">
      {/* Header */}
      <header className="page-header">
        <button className="btn btn-ghost mb-4" onClick={() => navigate(-1)}>
          <ArrowLeft size={18} />
          Voltar
        </button>

        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="page-title" style={{ marginBottom: 0 }}>
                {processo.numeroUnificado || processo.numeroProcesso}
              </h1>
              <span className="processo-tribunal">{processo.tribunal}</span>
            </div>
            <p className="page-subtitle">{processo.instancias?.[0]?.classe || processo.classeNome || 'Não informado'}</p>
          </div>

          <button
            className={`btn ${processo.monitorado ? 'btn-primary' : 'btn-secondary'}`}
            onClick={handleToggleMonitoramento}
          >
            {processo.monitorado ? <Eye size={18} /> : <EyeOff size={18} />}
            {processo.monitorado ? 'Monitorando' : 'Monitorar'}
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { id: 'info', label: 'Informações', icon: FileText },
          { id: 'partes', label: 'Partes', icon: Users },
          { id: 'movimentacoes', label: 'Movimentações', icon: Clock },
        ].map((t) => (
          <button
            key={t.id}
            className={`btn ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(t.id as any)}
          >
            <t.icon size={18} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'info' && (
        <div className="card">
          <div className="grid gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
            <div className="processo-info-item">
              <span className="processo-info-label">
                <Building size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Órgão Julgador
              </span>
              <span className="processo-info-value">{processo.instancias?.[0]?.orgao || processo.orgaoJulgadorNome || '-'}</span>
            </div>

            <div className="processo-info-item">
              <span className="processo-info-label">
                <Clock size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Data de Distribuição
              </span>
              <span className="processo-info-value">
                {processo.dataAjuizamento || processo.dataDistribuicao
                  ? format(new Date(processo.dataAjuizamento || processo.dataDistribuicao!), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })
                  : '-'}
              </span>
            </div>

            <div className="processo-info-item">
              <span className="processo-info-label">
                <DollarSign size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Valor da Causa
              </span>
              <span className="processo-info-value">
                {processo.valorCausa
                  ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(processo.valorCausa)
                  : '-'}
              </span>
            </div>

            <div className="processo-info-item">
              <span className="processo-info-label">Instância</span>
              <span className="processo-info-value">
                {processo.instancia 
                  ? (typeof processo.instancia === 'string' ? processo.instancia.replace('G', '') : processo.instancia) + 'º Grau'
                  : processo.instancias?.[0]?.descricaoGrau || '-'}
              </span>
            </div>

            <div className="processo-info-item">
              <span className="processo-info-label">Sistema</span>
              <span className="processo-info-value">{processo.sistema || '-'}</span>
            </div>

            <div className="processo-info-item">
              <span className="processo-info-label">Formato</span>
              <span className="processo-info-value">{processo.formato || 'Eletrônico'}</span>
            </div>
          </div>

          {processo.assunto && (
            <div style={{ marginTop: '24px' }}>
              <span className="processo-info-label">Assunto Principal</span>
              <div className="flex gap-2 mt-2" style={{ flexWrap: 'wrap' }}>
                <span className="badge badge-primary">
                  {processo.assunto}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'partes' && (
        <div className="grid gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))' }}>
          {/* Autores */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className="badge badge-success">Polo Ativo</span>
              Autores ({autores.length})
            </h3>
            {autores.length === 0 ? (
              <p className="text-secondary text-sm">Nenhum autor cadastrado</p>
            ) : (
              <div className="flex flex-col gap-4">
                {autores.map((parte, idx) => (
                  <div key={idx} className="p-4 bg-surface rounded-md" style={{ background: 'var(--surface)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
                    <div className="font-medium text-primary">{parte.nome}</div>
                    {parte.documento && (
                      <div className="text-sm text-secondary mt-1">
                        {parte.tipoPessoa === 'JURIDICA' ? 'CNPJ' : 'CPF'}: {parte.documento}
                      </div>
                    )}
                    {parte.advogados && parte.advogados.length > 0 && (
                      <div className="mt-2 text-sm">
                        <span className="text-muted">Advogados: </span>
                        <span className="text-secondary">
                          {parte.advogados.map((a) => `${a.nome} (${a.oab || a.inscricao || 'N/D'})`).join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Réus */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className="badge badge-danger">Polo Passivo</span>
              Réus ({reus.length})
            </h3>
            {reus.length === 0 ? (
              <p className="text-secondary text-sm">Nenhum réu cadastrado</p>
            ) : (
              <div className="flex flex-col gap-4">
                {reus.map((parte, idx) => (
                  <div key={idx} className="p-4 bg-surface rounded-md" style={{ background: 'var(--surface)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
                    <div className="font-medium text-primary">{parte.nome}</div>
                    {parte.documento && (
                      <div className="text-sm text-secondary mt-1">
                        {parte.tipoPessoa === 'JURIDICA' ? 'CNPJ' : 'CPF'}: {parte.documento}
                      </div>
                    )}
                    {parte.advogados && parte.advogados.length > 0 && (
                      <div className="mt-2 text-sm">
                        <span className="text-muted">Advogados: </span>
                        <span className="text-secondary">
                          {parte.advogados.map((a) => `${a.nome} (${a.oab})`).join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'movimentacoes' && (
        <div className="space-y-6">
          {/* Verifica se tem o novo formato (instancias) */}
          {processo.instancias && processo.instancias.length > 0 ? (
            // Novo formato: Organizado por instâncias
            processo.instancias.map((instancia, instanciaIdx) => {
              const isExpanded = instanciasExpandidas.has(instancia.grau)
              
              return (
              <div key={instancia.grau} className="card">
                <div 
                  className="flex items-center gap-3 pb-4 border-b cursor-pointer hover:opacity-80 transition-opacity" 
                  style={{ borderColor: 'var(--border)', marginBottom: isExpanded ? '24px' : '0' }}
                  onClick={() => toggleInstancia(instancia.grau)}
                >
                  <div className={`badge ${instanciaIdx === 0 ? 'badge-primary' : 'badge-accent'}`}>
                    {instancia.grau}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold">{instancia.descricaoGrau}</h3>
                    <p className="text-sm text-secondary">{instancia.orgao}</p>
                    {instancia.classe && (
                      <p className="text-sm text-muted">Classe: {instancia.classe}</p>
                    )}
                  </div>
                  {instancia.statusAtual && (
                    <span className="badge badge-success">
                      Status: {instancia.statusAtual}
                    </span>
                  )}
                  <button 
                    className="btn btn-ghost p-2"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleInstancia(instancia.grau)
                    }}
                  >
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>
                </div>

                {isExpanded && (
                  <>
                    {instancia.ultimasMovimentacoes && instancia.ultimasMovimentacoes.length > 0 ? (
                  <div className="timeline">
                    {instancia.ultimasMovimentacoes.map((mov, idx) => (
                      <div 
                        key={idx} 
                        className="timeline-item animate-fadeIn" 
                        style={{ animationDelay: `${idx * 0.03}s` }}
                      >
                        <div className={`timeline-dot ${idx === 0 ? 'new' : ''}`}>
                          <Clock size={12} color={idx === 0 ? 'white' : 'var(--primary)'} />
                        </div>
                        <div className="timeline-content">
                          <div className="timeline-date">
                            {format(new Date(mov.data), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                          </div>
                          <div className="timeline-title">{mov.movimentacao}</div>
                          {mov.detalhes && (
                            <div className="timeline-description">{mov.detalhes}</div>
                          )}
                          {mov.codigoNacional && (
                            <div className="text-xs text-muted mt-1">
                              Código: {mov.codigoNacional}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-secondary text-sm">Nenhuma movimentação nesta instância</p>
                )}
                  </>
                )}
              </div>
              )
            })
          ) : (
            // Formato antigo: Lista única de movimentações
            <div className="card">
              <h3 className="text-lg font-semibold mb-6">
                Timeline de Movimentações ({movimentacoes.length})
              </h3>

              {movimentacoes.length === 0 ? (
                <p className="text-secondary text-sm">Nenhuma movimentação registrada</p>
              ) : (
                <div className="timeline">
                  {movimentacoes.map((mov, idx) => (
                    <div key={mov.id} className="timeline-item animate-fadeIn" style={{ animationDelay: `${idx * 0.05}s` }}>
                      <div className={`timeline-dot ${idx === 0 ? 'new' : ''}`}>
                        <Clock size={12} color={idx === 0 ? 'white' : 'var(--primary)'} />
                      </div>
                      <div className="timeline-content">
                        <div className="timeline-date">
                          {format(new Date(mov.dataHora || mov.data!), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                        </div>
                        <div className="timeline-title">{mov.descricao || mov.movimentacao}</div>
                        {(mov.complemento || mov.detalhes) && (
                          <div className="timeline-description">{mov.complemento || mov.detalhes}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
