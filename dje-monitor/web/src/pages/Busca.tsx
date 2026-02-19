import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { Search, FileText, Eye, EyeOff, AlertCircle, X, Calendar, Building, Users, Scale, ExternalLink, Bell, Check } from 'lucide-react'
import { processoApi, pessoaMonitoradaApi } from '../services/api'

export default function Busca() {
  const navigate = useNavigate()
  const location = useLocation()
  const [tiposBusca, setTipoBusca] = useState<'numero' | 'cpf' | 'nome'>('nome')
  const [numero] = useState('')
  const [cpf] = useState('')
  const [nome, setNome] = useState('')
  // Estado para tribunal, padrão 'Todos'
  const [tribunal, setTribunal] = useState('Todos')
  const [loading, setLoading] = useState(false)
  const [resultados, setResultados] = useState<any[]>([]) // Use any[] or Processo[] if interface is available
  const [buscou, setBuscou] = useState(false)
  const [error, setError] = useState('')
  const [monitorando, setMonitorando] = useState(false)
  const [monitoradoSucesso, setMonitoradoSucesso] = useState(false)
  const [ultimoTermoBuscado, setUltimoTermoBuscado] = useState('')
  const [hideMonitorar, setHideMonitorar] = useState(false)

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

  const handleBuscar = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Determinar termo
    let termo = ''
    if (tiposBusca === 'numero') termo = numero
    else if (tiposBusca === 'cpf') termo = cpf.replace(/\D/g, '')
    else if (tiposBusca === 'nome') termo = nome

    if (!termo) return

    await executarBusca(termo, tribunal)
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
    const state = location.state as { nome?: string; tribunal?: string; autoSearch?: boolean; hideMonitorar?: boolean } | null
    if (state?.autoSearch && state.nome) {
      setNome(state.nome)
      const trib = state.tribunal || 'Todos'
      setTribunal(trib)
      if (state.hideMonitorar) setHideMonitorar(true)
      executarBusca(state.nome, trib)
      // Limpa o state para evitar re-execução ao recarregar
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
      {/* ... (Header and Search Type buttons remain same) ... */}
      <header className="page-header">
        <h1 className="page-title">Buscar Processo</h1>
        <p className="page-subtitle">Pesquise processos por número, CPF ou nome da parte</p>
      </header>

      {/* Search Form */}
      {/* Search Form */}
      {/* Search Form */}
      <div className="search-section">
        
        <div className="search-type-section">
            <h3 className="search-type-title">Tipo de Busca</h3>
            <div className="flex gap-3">
                <button 
                    type="button"
                    className={`btn ${tiposBusca === 'nome' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                    onClick={() => setTipoBusca('nome')}
                >
                    Nome ou Processo
                </button>
            </div>
        </div>

        <form onSubmit={handleBuscar} className="search-form-row">
          {tiposBusca === 'nome' && (
            <>
              <div className="search-input-wrapper">
                <label className="search-field-label">Termo</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Digite o Nome da Parte ou Número do Processo (CNJ)"
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
          )}

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

      {/* Results */}
      {buscou && (
        <div className="results-section">
          <div className="results-header">
            {/* Mantemos cabeçalho simples pois o detalhe vai pro drawer */}
            <div className="flex items-center gap-2">
                 <Search size={20} className="text-secondary" />
                 <h2 className="results-title">Resultados da Busca</h2>
            </div>
            <span className="results-count bg-surface border border-border px-3 py-1 rounded-full text-xs font-medium">
                {resultados.length} registos encontrados
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
          ) : resultados.length === 0 ? (
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
              {resultados.map((item: any, idx: number) => (
                <ResultadoItem key={item.id || idx} item={item} onBuscaProcesso={handleProcessoClick} />
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

// Componente legado para lista principal
function ResultadoItem({ item, onBuscaProcesso }: { item: any; key?: string | number; onBuscaProcesso: (proc: string) => void }) {
    const [expandido, setExpandido] = useState(false);
    const texto = item.texto || "";
    const numProcesso = item.processo || item.numeroProcesso || item.numero_processo;
    
    return (
        <li className="processo-item">
            <div className="processo-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className="processo-tribunal">{item.tribunal}</span>
                    <button 
                        onClick={(e) => {
                            e.stopPropagation();
                            console.log("🔘 Botão processo clicado. Valor:", numProcesso); 
                            if(numProcesso) onBuscaProcesso(numProcesso);
                        }}
                        className="processo-numero" 
                        style={{ 
                            fontSize: '1.1rem', 
                            background: 'none', 
                            border: 'none', 
                            padding: 0, 
                            cursor: 'pointer',
                            color: 'var(--primary)',
                            textDecoration: 'none',
                            fontWeight: 600
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                        onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                        title="Buscar histórico deste processo"
                    >
                        {numProcesso || "S/N"}
                    </button>
                </div>
                <div className="text-sm text-muted">
                    {item.data_disponibilizacao}
                </div>
            </div>

            <div className="processo-info" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="processo-info-item">
                    <span className="processo-info-label">Órgão / Tipo</span>
                    <span className="processo-info-value" style={{ fontWeight: 500 }}>
                        {item.orgao} {item.tipo_comunicacao ? `• ${item.tipo_comunicacao}` : ''}
                    </span>
                </div>

                {/* Exibição Estruturada de Polos ou Lista Simples */}
                {(item.polos && (item.polos.ativo?.length > 0 || item.polos.passivo?.length > 0 || item.polos.outros?.length > 0)) ? (
                    <div className="processo-partes" style={{ marginTop: '0', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                        {item.polos.ativo?.length > 0 && (
                            item.polos.ativo.map((parte: string, i: number) => (
                                <span key={`ativo-${i}`} className="parte-tag" style={{ 
                                    fontSize: '0.75rem', 
                                    background: 'rgba(16, 185, 129, 0.1)', 
                                    color: '#059669', 
                                    border: '1px solid rgba(16, 185, 129, 0.2)' 
                                }}>{parte}</span>
                            ))
                        )}
                        
                        {(item.polos.ativo?.length > 0 && item.polos.passivo?.length > 0) && (
                            <span className="text-muted text-xs font-semibold mx-1">vs</span>
                        )}

                        {item.polos.passivo?.length > 0 && (
                            item.polos.passivo.map((parte: string, i: number) => (
                                <span key={`passivo-${i}`} className="parte-tag" style={{ 
                                    fontSize: '0.75rem', 
                                    background: 'rgba(239, 68, 68, 0.1)', 
                                    color: '#dc2626', 
                                    border: '1px solid rgba(239, 68, 68, 0.2)' 
                                }}>{parte}</span>
                            ))
                        )}

                        {item.polos.outros?.length > 0 && (
                            <>
                                {((item.polos.ativo?.length > 0 || item.polos.passivo?.length > 0)) && <span className="text-muted text-xs mx-1">•</span>}
                                {item.polos.outros.map((parte: string, i: number) => (
                                    <span key={`outros-${i}`} className="parte-tag" style={{ fontSize: '0.75rem' }}>{parte}</span>
                                ))}
                            </>
                        )}
                    </div>
                ) : (
                    /* Fallback para lista simples antiga */
                    item.partes && item.partes.length > 0 && (
                        <div className="processo-partes" style={{ marginTop: '0' }}>
                            {item.partes.map((parte: string, i: number) => (
                                <span key={i} className="parte-tag" style={{ fontSize: '0.7rem' }}>{parte}</span>
                            ))}
                        </div>
                    )
                )}
                
                <div className="processo-info-item" style={{ 
                    marginTop: '4px', 
                    background: 'var(--surface)', 
                    padding: '12px', 
                    borderRadius: '8px',
                    border: '1px solid var(--border)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <button 
                            onClick={() => setExpandido(!expandido)}
                            className="btn btn-ghost btn-sm"
                            style={{ 
                                padding: '0', 
                                fontSize: '0.85rem',
                                color: 'var(--primary)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                fontWeight: 500
                            }}
                        >
                            {expandido ? (
                                <>
                                    <EyeOff size={16} />
                                    Ocultar conteúdo da publicação
                                </>
                            ) : (
                                <>
                                    <Eye size={16} />
                                    Ler conteúdo da publicação
                                </>
                            )}
                        </button>
                    </div>
                    
                    {expandido && (
                        <div className="animate-fadeIn">
                            <p className="processo-info-value" style={{ 
                                whiteSpace: 'pre-wrap', 
                                fontSize: '0.9rem',
                                color: 'var(--text-secondary)',
                                lineHeight: '1.6',
                                fontFamily: 'Inter, sans-serif',
                                marginTop: '12px',
                                padding: '8px',
                                background: 'var(--background)',
                                borderRadius: '4px'
                            }}>
                                {texto}
                            </p>
                            
                            {item.link && (
                                <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                                    <a href={item.link} target="_blank" rel="noreferrer" className="text-primary text-xs hover:underline flex items-center gap-1">
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
    );
}
