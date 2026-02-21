import { useState, useEffect, useRef, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { Search, FileText, Eye, EyeOff, AlertCircle, X, Calendar, Building, Users, Scale, ExternalLink, Bell, Check, Sparkles } from 'lucide-react'
import { processoApi, pessoaMonitoradaApi, semanticApi, SemanticResult, ProcessoPublicacao } from '../services/api'

export default function Busca() {
  const navigate = useNavigate()
  const location = useLocation()
  const [nome, setNome] = useState('')
  const [tribunal, setTribunal] = useState('Todos')
  const [loading, setLoading] = useState(false)
  const [resultados, setResultados] = useState<any[]>([])
  const [buscou, setBuscou] = useState(false)
  const [error, setError] = useState('')
  const [monitorando, setMonitorando] = useState(false)
  const [monitoradoSucesso, setMonitoradoSucesso] = useState(false)
  const [ultimoTermoBuscado, setUltimoTermoBuscado] = useState('')
  const [hideMonitorar, setHideMonitorar] = useState(false)

  // Agrupa resultados da busca exata por processo, ordenando publicações por data desc
  const resultadosAgrupados = useMemo(() => {
    const parseDate = (d?: string) => {
      if (!d) return 0
      const p = d.split('/')
      return p.length === 3 ? new Date(`${p[2]}-${p[1]}-${p[0]}`).getTime() : 0
    }
    const map: Record<string, any[]> = {}
    for (const item of resultados) {
      const key = item.processo || item.numero_processo || '__sem_proc__'
      if (!map[key]) map[key] = []
      map[key].push(item)
    }
    return Object.entries(map).map(([proc, pubs]) => {
      const sorted = [...pubs].sort((a, b) => parseDate(b.data_disponibilizacao) - parseDate(a.data_disponibilizacao))
      return { processo: proc === '__sem_proc__' ? '' : proc, publicacoes: sorted, latest: sorted[0] }
    })
  }, [resultados])

  // Modo de busca unificado: exata | sem-publicacoes | sem-processos
  const [modoBusca, setModoBuscaRaw] = useState<'exata' | 'sem-publicacoes' | 'sem-processos'>('exata')
  const [resultadosSemanticos, setResultadosSemanticos] = useState<SemanticResult[]>([])
  const [loadingSemantico, setLoadingSemantico] = useState(false)
  const [buscouSemantico, setBuscouSemantico] = useState(false)
  const [errorSemantico, setErrorSemantico] = useState('')
  const isSemantico = modoBusca.startsWith('sem-')

  const setModoBusca = (modo: 'exata' | 'sem-publicacoes' | 'sem-processos') => {
    setModoBuscaRaw(modo)
    // Limpar resultados ao trocar de aba
    setBuscou(false)
    setResultados([])
    setBuscouSemantico(false)
    setResultadosSemanticos([])
    setError('')
    setErrorSemantico('')
    setMonitoradoSucesso(false)
  }

  const tribunais = [
    'Todos', // Adicionado opção Todos
    'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDFT', 'TJES', 'TJGO', 'TJMA',
    'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE', 'TJPI', 'TJPR', 'TJRJ', 'TJRN',
    'TJRO', 'TJRR', 'TJRS', 'TJSC', 'TJSE', 'TJSP', 'TJTO',
  ]

  // Estados para o Drawer de Histórico
  const [processoSelecionado, setProcessoSelecionado] = useState<string | null>(null)
  const [historicoProcesso, setHistoricoProcesso] = useState<any[]>([])
  const [loadingHistorico, setLoadingHistorico] = useState(false)

  const executarBusca = async (termoBusca: string, filtroTribunal: string) => {
    setError('')
    setLoading(true)
    setBuscou(true)
    setMonitoradoSucesso(false)
    setUltimoTermoBuscado(termoBusca)

    try {
      const params = { nome: termoBusca, tribunal: filtroTribunal === 'Todos' ? undefined : filtroTribunal }
      const response = await processoApi.buscar(params)
      setResultados(response.data || [])
    } catch (err: any) {
      console.error('Erro na busca:', err)
      setError(err.response?.data?.message || 'Erro ao buscar processos')
      setResultados([])
    } finally {
      setLoading(false)
    }
  }

  const handleMonitorar = async () => {
    if (!ultimoTermoBuscado) return
    setMonitorando(true)
    try {
      await pessoaMonitoradaApi.criar({
        nome: ultimoTermoBuscado,
        tribunal_filtro: tribunal === 'Todos' ? undefined : tribunal,
      })
      setMonitoradoSucesso(true)
    } catch (err: any) {
      console.error('Erro ao monitorar:', err)
      setError(err.response?.data?.detail || 'Erro ao adicionar monitoramento')
    } finally {
      setMonitorando(false)
    }
  }

  const buscarHistoricoProcesso = async (proc: string) => {
      setLoadingHistorico(true);
      setHistoricoProcesso([]);
      try {
          // Busca específica pelo número do processo (usando 'nome' pois o backend detecta)
          const params = { nome: proc };
          const response = await processoApi.buscar(params);
          setHistoricoProcesso(response.data || []);
      } catch (err: any) {
          console.error('Erro ao buscar histórico:', err);
          // Opcional: mostrar erro no drawer
      } finally {
          setLoadingHistorico(false);
      }
  }

  const executarBuscaSemantica = async (query: string, filtroTribunal: string) => {
    setErrorSemantico('')
    setLoadingSemantico(true)
    setBuscouSemantico(true)
    try {
      const resp = await semanticApi.search({
        q: query,
        tribunal: filtroTribunal === 'Todos' ? undefined : filtroTribunal,
        tipo: modoBusca === 'sem-publicacoes' ? 'publicacoes' : 'processos',
      })
      setResultadosSemanticos(resp.results)
    } catch (err: any) {
      setErrorSemantico(err.response?.data?.detail || 'Erro na busca semântica')
      setResultadosSemanticos([])
    } finally {
      setLoadingSemantico(false)
    }
  }

  const handleBuscar = async (e: React.FormEvent) => {
    e.preventDefault()

    const termo = nome
    if (!termo) return

    if (isSemantico) {
      await executarBuscaSemantica(termo, tribunal)
    } else {
      await executarBusca(termo, tribunal)
    }
  }

  const handleProcessoClick = (proc: string) => {
      if (!proc) return;
      setProcessoSelecionado(proc);
      buscarHistoricoProcesso(proc);
  }

  const fecharHistorico = () => {
      setProcessoSelecionado(null);
      setHistoricoProcesso([]);
  }

  // Auto-busca ao navegar de outra página com state { nome, tribunal, autoSearch, hideMonitorar }
  useEffect(() => {
    // 1. Navegação na mesma aba (ex: Monitorados → Busca) via router state
    const state = location.state as { nome?: string; tribunal?: string; autoSearch?: boolean; hideMonitorar?: boolean } | null
    if (state?.autoSearch && state.nome) {
      setNome(state.nome)
      const trib = state.tribunal || 'Todos'
      setTribunal(trib)
      if (state.hideMonitorar) setHideMonitorar(true)
      executarBusca(state.nome, trib)
      navigate(location.pathname, { replace: true, state: {} })
      return
    }

    // 2. Navegação em nova aba (ex: Oportunidades → Busca) via query params
    const params = new URLSearchParams(location.search)
    const nomeParam = params.get('nome')
    if (nomeParam) {
      const trib = params.get('tribunal') || 'Todos'
      setNome(nomeParam)
      setTribunal(trib)
      executarBusca(nomeParam, trib)
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Guardar posição do scroll ao abrir o drawer
  const scrollPosRef = useRef(0);

  // Travar scroll do body quando o drawer está aberto (sem pular posição)
  useEffect(() => {
      if (processoSelecionado) {
          // Salvar posição atual do scroll
          scrollPosRef.current = window.scrollY;
          // Travar o body na posição atual
          document.body.style.position = 'fixed';
          document.body.style.top = `-${scrollPosRef.current}px`;
          document.body.style.left = '0';
          document.body.style.right = '0';
          document.body.style.overflow = 'hidden';
      } else {
          // Restaurar posição do scroll
          document.body.style.position = '';
          document.body.style.top = '';
          document.body.style.left = '';
          document.body.style.right = '';
          document.body.style.overflow = '';
          window.scrollTo(0, scrollPosRef.current);
      }
      return () => {
          document.body.style.position = '';
          document.body.style.top = '';
          document.body.style.left = '';
          document.body.style.right = '';
          document.body.style.overflow = '';
          window.scrollTo(0, scrollPosRef.current);
      };
  }, [processoSelecionado]);

  return (
    <div className="container py-8 max-w-5xl mx-auto animate-fadeIn">
      <header className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {modoBusca === 'exata'
            ? <Search size={28} style={{ color: 'var(--primary)' }} />
            : <Sparkles size={28} style={{ color: 'var(--accent)' }} />}
          {modoBusca === 'exata' ? 'Buscar Processo' : 'Busca Semântica'}
        </h1>
        <p className="page-subtitle">
          {modoBusca === 'exata'
            ? 'Pesquise processos por número ou nome da parte'
            : modoBusca === 'sem-publicacoes'
              ? 'Pesquise publicações por contexto e significado'
              : 'Pesquise processos por contexto e significado'}
        </p>
      </header>
      <div className="search-section">

        {/* Abas de modo de busca */}
        <div style={{ display: 'flex', gap: '4px', background: 'var(--surface)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border)', marginBottom: '16px' }}>
          <button
            type="button"
            onClick={() => setModoBusca('exata')}
            className={`btn btn-sm ${modoBusca === 'exata' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, justifyContent: 'center' }}
          >
            <Search size={14} />
            Busca por Nome
          </button>
          <button
            type="button"
            onClick={() => setModoBusca('sem-publicacoes')}
            className={`btn btn-sm ${modoBusca === 'sem-publicacoes' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, justifyContent: 'center' }}
          >
            <Sparkles size={14} />
            Semântica: Publicações
          </button>
          <button
            type="button"
            onClick={() => setModoBusca('sem-processos')}
            className={`btn btn-sm ${modoBusca === 'sem-processos' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, justifyContent: 'center' }}
          >
            <Sparkles size={14} />
            Semântica: Processos
          </button>
        </div>

        <form onSubmit={handleBuscar} className="search-form-row">
            <>
              <div className="search-input-wrapper">
                <label className="search-field-label">Termo</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder={
                    modoBusca === 'exata'
                      ? 'Digite o Nome da Parte ou Número do Processo (CNJ)'
                      : modoBusca === 'sem-publicacoes'
                        ? 'Descreva o que procura nas publicações (ex: execução fiscal, dívida tributária)'
                        : 'Descreva o que procura nos processos (ex: dano moral, cumprimento de sentença)'
                  }
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                />
              </div>
              
              <div className="search-input-wrapper tribunal">
                <label className="search-field-label">Tribunal</label>
                <div style={{ position: 'relative' }}>
                    <select
                      className="input-field"
                      style={{ appearance: 'none', cursor: 'pointer', paddingRight: '32px' }}
                      value={tribunal}
                      onChange={(e) => setTribunal(e.target.value)}
                    >
                      {tribunais.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <div style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }}>
                        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                </div>
              </div>
            </>

          <div className="search-actions">
            <button 
                type="submit" 
                className="btn btn-primary search-btn-large" 
                disabled={loading}
            >
              {loading ? <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} /> : <Search size={18} />}
              {loading ? '' : 'Buscar'}
            </button>
          </div>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="card mb-6 flex items-center gap-3" style={{ borderColor: 'var(--danger)' }}>
          <AlertCircle size={20} color="var(--danger)" />
          <span className="text-danger">{error}</span>
        </div>
      )}

      {/* Resultados busca exata */}
      {buscou && modoBusca === 'exata' && (
        <div className="results-section">
          <div className="results-header">
            {/* Mantemos cabeçalho simples pois o detalhe vai pro drawer */}
            <div className="flex items-center gap-2">
                 <Search size={20} className="text-secondary" />
                 <h2 className="results-title">Resultados da Busca</h2>
            </div>
            <span className="results-count bg-surface border border-border px-3 py-1 rounded-full text-xs font-medium">
                {resultadosAgrupados.length} processo(s) encontrado(s)
            </span>
          </div>

          {/* Banner de monitoramento */}
          {!loading && ultimoTermoBuscado && !hideMonitorar && (
            <div className="card mb-4" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', padding: '14px 20px' }}>
              {monitoradoSucesso ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--success)' }}>
                  <Check size={18} />
                  <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                    <strong>{ultimoTermoBuscado}</strong> adicionado ao monitoramento! Publicações futuras gerarão alertas.
                  </span>
                </div>
              ) : (
                <>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    Deseja monitorar automaticamente novas publicações de <strong style={{ color: 'var(--text-primary)' }}>{ultimoTermoBuscado}</strong>?
                  </span>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleMonitorar}
                    disabled={monitorando}
                    style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    {monitorando
                      ? <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />
                      : <Bell size={15} />
                    }
                    {monitorando ? 'Adicionando...' : 'Monitorar'}
                  </button>
                </>
              )}
            </div>
          )}

          {loading ? (
            <div className="loading">
              <div className="spinner" />
              <span className="loading-text">Buscando...</span>
            </div>
          ) : resultadosAgrupados.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <FileText size={32} />
              </div>
              <h3 className="empty-title">Nenhum registro encontrado</h3>
              <p className="empty-description">
                Tente buscar com outros termos ou verifique se as informações estão corretas.
              </p>
            </div>
          ) : (
            <ul className="processo-list">
              {resultadosAgrupados.map((grupo, idx) => (
                <ResultadoItem key={grupo.processo || idx} grupo={grupo} onBuscaProcesso={handleProcessoClick} />
              ))}
            </ul>
          )}
        </div>
      )}
      
      {/* Resultados Semânticos */}
      {isSemantico && buscouSemantico && (
        <div className="results-section">
          <div className="results-header">
            <div className="flex items-center gap-2">
              <Sparkles size={20} className="text-secondary" />
              <h2 className="results-title">Resultados Semânticos</h2>
            </div>
            <span className="results-count bg-surface border border-border px-3 py-1 rounded-full text-xs font-medium">
              {resultadosSemanticos.length} resultado(s)
            </span>
          </div>

          {errorSemantico && (
            <div className="card mb-4 flex items-center gap-3" style={{ borderColor: 'var(--danger)' }}>
              <AlertCircle size={20} color="var(--danger)" />
              <span className="text-danger">{errorSemantico}</span>
            </div>
          )}

          {loadingSemantico ? (
            <div className="loading">
              <div className="spinner" />
              <span className="loading-text">Buscando semanticamente...</span>
            </div>
          ) : resultadosSemanticos.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><Sparkles size={32} /></div>
              <h3 className="empty-title">Nenhum resultado semântico</h3>
              <p className="empty-description">Tente outras palavras ou reduza o threshold de similaridade.</p>
            </div>
          ) : (
            <ul className="processo-list">
              {resultadosSemanticos.map((item, idx) => (
                <SemanticResultItem key={item.pub_id ?? item.processo_id ?? idx} item={item} tipo={modoBusca === 'sem-publicacoes' ? 'publicacoes' : 'processos'} onBuscaProcesso={handleProcessoClick} />
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Drawer Lateral de Detalhe do Processo */}
      {processoSelecionado && createPortal(
          <>
            <div className="drawer-overlay" onClick={fecharHistorico} />
            <div className="drawer-container animate-slideInRight">
                {/* Header do Drawer */}
                <div className="drawer-header">
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', flex: 1 }}>
                        <div className="drawer-header-icon">
                            <Scale size={22} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <h3 className="drawer-title">Detalhe do Processo</h3>
                            <p className="drawer-processo-numero">{processoSelecionado}</p>
                        </div>
                    </div>
                    <button
                        onClick={fecharHistorico}
                        className="drawer-close-btn"
                        title="Fechar"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Conteúdo do Drawer */}
                <div className="drawer-body custom-scrollbar">
                    {loadingHistorico ? (
                        <div className="loading" style={{ padding: '64px 0' }}>
                            <div className="spinner" />
                            <span className="loading-text">Buscando publicações do processo...</span>
                        </div>
                    ) : historicoProcesso.length === 0 ? (
                        <div className="empty-state" style={{ padding: '48px 24px' }}>
                            <div className="empty-icon"><FileText size={32} /></div>
                            <h3 className="empty-title">Nenhuma publicação encontrada</h3>
                            <p className="empty-description">Não foram encontradas publicações para este processo no DJe.</p>
                        </div>
                    ) : (
                        <>
                            {/* Resumo do Processo - extraído da primeira publicação */}
                            <DrawerResumo items={historicoProcesso} />

                            {/* Lista de Publicações */}
                            <div className="drawer-section">
                                <div className="drawer-section-header">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <FileText size={16} />
                                        <span>{historicoProcesso.length} Publicações Encontradas</span>
                                    </div>
                                </div>
                                <div className="drawer-publicacoes">
                                    {historicoProcesso.map((item, idx) => (
                                        <DrawerPublicacaoItem key={idx} item={item} index={idx} />
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
          </>,
          document.body     
      )}
    </div>
  )
}

// Componente de resumo do processo no drawer
function DrawerResumo({ items }: { items: any[] }) {
    // Coletar informações únicas de todas as publicações
    const tribunais = [...new Set(items.map(i => i.tribunal).filter(Boolean))];
    const orgaos = [...new Set(items.map(i => i.orgao).filter(Boolean))];
    const tiposComunicacao = [...new Set(items.map(i => i.tipo_comunicacao).filter(Boolean))];

    // Coletar todas as partes de todos os items
    const todosAtivos = [...new Set(items.flatMap(i => i.polos?.ativo || []))];
    const todosPassivos = [...new Set(items.flatMap(i => i.polos?.passivo || []))];

    // Datas (primeira e última)
    const datas = items
        .map(i => i.data_disponibilizacao)
        .filter(Boolean)
        .sort();

    return (
        <div className="drawer-resumo">
            {/* Cards de info */}
            <div className="drawer-info-grid">
                <div className="drawer-info-card">
                    <div className="drawer-info-card-icon">
                        <Building size={16} />
                    </div>
                    <div>
                        <span className="drawer-info-label">Tribunal</span>
                        <span className="drawer-info-value">{tribunais.join(', ') || '-'}</span>
                    </div>
                </div>
                <div className="drawer-info-card">
                    <div className="drawer-info-card-icon">
                        <Building size={16} />
                    </div>
                    <div>
                        <span className="drawer-info-label">Órgão</span>
                        <span className="drawer-info-value">{orgaos[0] || '-'}</span>
                    </div>
                </div>
                <div className="drawer-info-card">
                    <div className="drawer-info-card-icon">
                        <Calendar size={16} />
                    </div>
                    <div>
                        <span className="drawer-info-label">Período</span>
                        <span className="drawer-info-value">
                            {datas.length > 1 ? `${datas[0]} a ${datas[datas.length - 1]}` : datas[0] || '-'}
                        </span>
                    </div>
                </div>
                <div className="drawer-info-card">
                    <div className="drawer-info-card-icon">
                        <FileText size={16} />
                    </div>
                    <div>
                        <span className="drawer-info-label">Tipo</span>
                        <span className="drawer-info-value">{tiposComunicacao[0] || '-'}</span>
                    </div>
                </div>
            </div>

            {/* Partes */}
            {(todosAtivos.length > 0 || todosPassivos.length > 0) && (
                <div className="drawer-partes">
                    <div className="drawer-partes-header">
                        <Users size={16} />
                        <span>Partes do Processo</span>
                    </div>
                    <div className="drawer-partes-grid">
                        {todosAtivos.length > 0 && (
                            <div className="drawer-polo">
                                <span className="drawer-polo-label polo-ativo">Polo Ativo</span>
                                {todosAtivos.map((nome, i) => (
                                    <span key={i} className="drawer-parte-nome">{nome}</span>
                                ))}
                            </div>
                        )}
                        {todosPassivos.length > 0 && (
                            <div className="drawer-polo">
                                <span className="drawer-polo-label polo-passivo">Polo Passivo</span>
                                {todosPassivos.map((nome, i) => (
                                    <span key={i} className="drawer-parte-nome">{nome}</span>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// Componente de cada publicação no drawer
function DrawerPublicacaoItem({ item, index }: { item: any; index: number; key?: string | number }) {
    const [expandido, setExpandido] = useState(false);
    const texto = item.texto || "";

    return (
        <div className="drawer-pub-item" style={{ animationDelay: `${index * 0.05}s` }}>
            <div className="drawer-pub-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span className="processo-tribunal">{item.tribunal}</span>
                    <span className="drawer-pub-orgao">{item.orgao}</span>
                    {item.tipo_comunicacao && (
                        <span className="drawer-pub-tipo">{item.tipo_comunicacao}</span>
                    )}
                </div>
                <span className="drawer-pub-data">
                    <Calendar size={13} />
                    {item.data_disponibilizacao}
                </span>
            </div>

            {/* Partes inline */}
            {(item.polos?.ativo?.length > 0 || item.polos?.passivo?.length > 0) && (
                <div className="drawer-pub-partes">
                    {item.polos.ativo?.map((p: string, i: number) => (
                        <span key={`A${i}`} className="parte-tag" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#059669', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '0.7rem' }}>{p}</span>
                    ))}
                    {item.polos.ativo?.length > 0 && item.polos.passivo?.length > 0 && (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontWeight: 600 }}>vs</span>
                    )}
                    {item.polos.passivo?.map((p: string, i: number) => (
                        <span key={`P${i}`} className="parte-tag" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#dc2626', border: '1px solid rgba(239, 68, 68, 0.2)', fontSize: '0.7rem' }}>{p}</span>
                    ))}
                </div>
            )}

            {/* Botão expandir + conteúdo */}
            <div className="drawer-pub-content-area">
                <button
                    onClick={() => setExpandido(!expandido)}
                    className="drawer-pub-toggle"
                >
                    {expandido ? <EyeOff size={15} /> : <Eye size={15} />}
                    {expandido ? 'Ocultar conteúdo' : 'Ler conteúdo da publicação'}
                </button>

                {expandido && (
                    <div className="drawer-pub-texto animate-fadeIn">
                        <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: '1.7', color: 'var(--text-secondary)', fontFamily: 'Inter, sans-serif' }}>
                            {texto}
                        </p>
                        {item.link && (
                            <a href={item.link} target="_blank" rel="noreferrer" className="drawer-pub-link">
                                <ExternalLink size={12} />
                                Ver documento original
                            </a>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

// Componente de card para resultado semântico
function PublicacaoItem({ pub }: { pub: ProcessoPublicacao; key?: string | number }) {
    const [expandido, setExpandido] = useState(false);
    const texto = pub.texto_completo || pub.texto_resumo || '';
    const PREVIEW_LEN = 200;
    const temMais = texto.length > PREVIEW_LEN;

    return (
        <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}>
                    {pub.data_disponibilizacao && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>
                            <Calendar size={12} />
                            {pub.data_disponibilizacao}
                        </span>
                    )}
                    {pub.orgao && <span style={{ color: 'var(--text-secondary)' }}>{pub.orgao}</span>}
                    {pub.tipo_comunicacao && <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>({pub.tipo_comunicacao})</span>}
                </div>
                {pub.link && (
                    <a
                        href={pub.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--primary)', fontSize: '0.8rem', textDecoration: 'none', whiteSpace: 'nowrap' }}
                    >
                        <ExternalLink size={13} />
                        Ver original
                    </a>
                )}
            </div>
            {(pub.polo_ativo || pub.polo_passivo) && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
                    {pub.polo_ativo && (
                        <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '3px', background: 'rgba(16, 185, 129, 0.1)', color: '#059669', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                            {pub.polo_ativo}
                        </span>
                    )}
                    {pub.polo_ativo && pub.polo_passivo && (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', alignSelf: 'center' }}>vs</span>
                    )}
                    {pub.polo_passivo && (
                        <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '3px', background: 'rgba(239, 68, 68, 0.1)', color: '#dc2626', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                            {pub.polo_passivo}
                        </span>
                    )}
                </div>
            )}
            {texto && (
                <div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.4', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {expandido ? texto : texto.slice(0, PREVIEW_LEN)}{!expandido && temMais ? '...' : ''}
                    </p>
                    {temMais && (
                        <button
                            onClick={() => setExpandido(!expandido)}
                            style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: '0.75rem', padding: '2px 0', marginTop: '2px' }}
                        >
                            {expandido ? 'Ver menos' : 'Ver texto completo'}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

function SemanticResultItem({ item, tipo, onBuscaProcesso }: {
    item: SemanticResult;
    tipo: 'publicacoes' | 'processos';
    onBuscaProcesso: (proc: string) => void;
    key?: string | number;
}) {
    const [expandido, setExpandido] = useState(false);
    const [pubsExpandidas, setPubsExpandidas] = useState(false);
    const scorePercent = Math.round(item.score * 100);
    const scoreColor = scorePercent >= 70 ? '#10b981' : scorePercent >= 50 ? '#f59e0b' : '#ef4444';
    const textoCompleto = item.texto_completo || item.texto_resumo || '';
    const PREVIEW_LEN = 300;
    const temMais = textoCompleto.length > PREVIEW_LEN;
    const publicacoes = item.publicacoes || [];

    return (
        <li className="processo-item">
            <div className="processo-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {item.tribunal && <span className="processo-tribunal">{item.tribunal}</span>}
                    {item.numero_processo && (
                        <button
                            onClick={() => item.numero_processo && onBuscaProcesso(item.numero_processo)}
                            className="processo-numero"
                            style={{ fontSize: '1rem', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--primary)', fontWeight: 600 }}
                            onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                            onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                        >
                            {item.numero_processo}
                        </button>
                    )}
                </div>
                {/* Badge de score */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '80px', height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${scorePercent}%`, height: '100%', background: scoreColor, borderRadius: '3px', transition: 'width 0.3s' }} />
                    </div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: scoreColor }}>{scorePercent}%</span>
                </div>
            </div>

            <div className="processo-info" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {tipo === 'publicacoes' && (
                    <>
                        {item.orgao && (
                            <div className="processo-info-item">
                                <span className="processo-info-label">Órgão</span>
                                <span className="processo-info-value">{item.orgao}{item.tipo_comunicacao ? ` • ${item.tipo_comunicacao}` : ''}</span>
                            </div>
                        )}
                        {(item.polo_ativo || item.polo_passivo) && (
                            <div className="processo-partes" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                                {item.polo_ativo && (
                                    <span className="parte-tag" style={{ fontSize: '0.75rem', background: 'rgba(16, 185, 129, 0.1)', color: '#059669', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                                        {item.polo_ativo}
                                    </span>
                                )}
                                {item.polo_ativo && item.polo_passivo && (
                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontWeight: 600, alignSelf: 'center' }}>vs</span>
                                )}
                                {item.polo_passivo && (
                                    <span className="parte-tag" style={{ fontSize: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: '#dc2626', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                                        {item.polo_passivo}
                                    </span>
                                )}
                            </div>
                        )}
                        {textoCompleto && (
                            <div>
                                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: '4px 0 0 0', fontStyle: 'italic', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                    "{expandido ? textoCompleto : textoCompleto.slice(0, PREVIEW_LEN)}{!expandido && temMais ? '...' : ''}"
                                </p>
                                {temMais && (
                                    <button
                                        onClick={() => setExpandido(!expandido)}
                                        style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: '0.8rem', padding: '4px 0', marginTop: '2px' }}
                                    >
                                        {expandido ? 'Ver menos' : 'Ver texto completo'}
                                    </button>
                                )}
                            </div>
                        )}
                        {item.link && (
                            <a
                                href={item.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--primary)', fontSize: '0.8rem', textDecoration: 'none', marginTop: '4px' }}
                            >
                                <ExternalLink size={13} />
                                Ver documento original
                            </a>
                        )}
                        {item.data_disponibilizacao && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '4px' }}>
                                <Calendar size={13} />
                                {item.data_disponibilizacao}
                            </div>
                        )}
                    </>
                )}

                {tipo === 'processos' && (
                    <>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                {publicacoes.length} publicação{publicacoes.length !== 1 ? 'ões' : ''}
                            </span>
                            {publicacoes.length > 0 && (
                                <button
                                    onClick={() => setPubsExpandidas(!pubsExpandidas)}
                                    style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: '0.8rem', padding: '2px 0', display: 'flex', alignItems: 'center', gap: '4px' }}
                                >
                                    <FileText size={13} />
                                    {pubsExpandidas ? 'Ocultar publicações' : 'Ver publicações'}
                                </button>
                            )}
                        </div>
                        {pubsExpandidas && publicacoes.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                                {[...publicacoes].sort((a, b) => {
                                    const parseDate = (d?: string) => {
                                        if (!d) return 0
                                        const [dd, mm, yyyy] = d.split('/')
                                        return new Date(`${yyyy}-${mm}-${dd}`).getTime() || 0
                                    }
                                    return parseDate(b.data_disponibilizacao) - parseDate(a.data_disponibilizacao)
                                }).map((pub, idx) => (
                                    <PublicacaoItem key={pub.id ?? idx} pub={pub} />
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>
        </li>
    );
}

// Componente de resultado agrupado por processo
function ResultadoItem({ grupo, onBuscaProcesso }: {
    grupo: { processo: string; publicacoes: any[]; latest: any };
    key?: string | number;
    onBuscaProcesso: (proc: string) => void;
}) {
    const [expandido, setExpandido] = useState(false)
    const { processo, publicacoes, latest } = grupo
    const texto = latest.texto || ""
    const polos = latest.polos || {}
    const temPolos = polos.ativo?.length > 0 || polos.passivo?.length > 0 || polos.outros?.length > 0

    return (
        <li className="processo-item">
            {/* Cabeçalho: tribunal + número do processo + data mais recente */}
            <div className="processo-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className="processo-tribunal">{latest.tribunal}</span>
                    <button
                        onClick={(e) => { e.stopPropagation(); if (processo) onBuscaProcesso(processo) }}
                        className="processo-numero"
                        style={{ fontSize: '1.1rem', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--primary)', fontWeight: 600 }}
                        onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                        onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                        title="Ver histórico completo do processo"
                    >
                        {processo || 'S/N'}
                    </button>
                    {publicacoes.length > 1 && (
                        <span style={{ fontSize: '0.72rem', background: 'rgba(99,102,241,0.12)', color: 'var(--primary)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                            {publicacoes.length} publicações
                        </span>
                    )}
                </div>
                <div className="text-sm text-muted">{latest.data_disponibilizacao}</div>
            </div>

            {/* Info: órgão + tipo */}
            <div className="processo-info" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {latest.orgao && (
                    <div className="processo-info-item">
                        <span className="processo-info-label">Órgão / Tipo</span>
                        <span className="processo-info-value" style={{ fontWeight: 500 }}>
                            {latest.orgao}{latest.tipo_comunicacao ? ` • ${latest.tipo_comunicacao}` : ''}
                        </span>
                    </div>
                )}

                {/* Polos */}
                {temPolos && (
                    <div className="processo-partes" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                        {polos.ativo?.map((parte: string, i: number) => (
                            <span key={`a${i}`} className="parte-tag" style={{ fontSize: '0.75rem', background: 'rgba(16,185,129,0.1)', color: '#059669', border: '1px solid rgba(16,185,129,0.2)' }}>{parte}</span>
                        ))}
                        {polos.ativo?.length > 0 && polos.passivo?.length > 0 && (
                            <span className="text-muted text-xs font-semibold mx-1">vs</span>
                        )}
                        {polos.passivo?.map((parte: string, i: number) => (
                            <span key={`p${i}`} className="parte-tag" style={{ fontSize: '0.75rem', background: 'rgba(239,68,68,0.1)', color: '#dc2626', border: '1px solid rgba(239,68,68,0.2)' }}>{parte}</span>
                        ))}
                        {polos.outros?.map((parte: string, i: number) => (
                            <span key={`o${i}`} className="parte-tag" style={{ fontSize: '0.75rem' }}>{parte}</span>
                        ))}
                    </div>
                )}

                {/* Publicação mais recente (expandível) */}
                <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <button
                        onClick={() => setExpandido(!expandido)}
                        className="btn btn-ghost btn-sm"
                        style={{ padding: 0, fontSize: '0.85rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '6px', background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 500 }}
                    >
                        {expandido ? <><EyeOff size={16} />Ocultar publicação mais recente</> : <><Eye size={16} />Ler publicação mais recente</>}
                    </button>

                    {expandido && (
                        <div className="animate-fadeIn" style={{ marginTop: '12px' }}>
                            <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6', fontFamily: 'Inter, sans-serif', padding: '8px', background: 'var(--background)', borderRadius: '4px', margin: 0 }}>
                                {texto}
                            </p>
                            {latest.link && (
                                <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                                    <a href={latest.link} target="_blank" rel="noreferrer" className="text-primary text-xs hover:underline flex items-center gap-1">
                                        <FileText size={12} />
                                        Ver Documento Original
                                    </a>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </li>
    )
}
