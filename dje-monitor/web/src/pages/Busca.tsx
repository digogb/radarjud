import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, FileText, Eye, EyeOff, AlertCircle, X } from 'lucide-react'
import { processoApi, Processo } from '../services/api'

export default function Busca() {
  const navigate = useNavigate()
  const [tiposBusca, setTipoBusca] = useState<'numero' | 'cpf' | 'nome'>('nome')
  const [numero, setNumero] = useState('')
  const [cpf, setCpf] = useState('')
  const [nome, setNome] = useState('')
  // Estado para tribunal, padrão 'Todos'
  const [tribunal, setTribunal] = useState('Todos')
  const [loading, setLoading] = useState(false)
  const [resultados, setResultados] = useState<any[]>([]) // Use any[] or Processo[] if interface is available
  const [buscou, setBuscou] = useState(false)
  const [error, setError] = useState('')

  const tribunais = [
    'Todos', // Adicionado opção Todos
    'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDFT', 'TJES', 'TJGO', 'TJMA',
    'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE', 'TJPI', 'TJPR', 'TJRJ', 'TJRN',
    'TJRO', 'TJRR', 'TJRS', 'TJSC', 'TJSE', 'TJSP', 'TJTO',
    'TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5',
  ]

  // Estados para o Drawer de Histórico
  const [processoSelecionado, setProcessoSelecionado] = useState<string | null>(null)
  const [historicoProcesso, setHistoricoProcesso] = useState<any[]>([])
  const [loadingHistorico, setLoadingHistorico] = useState(false)

  const executarBusca = async (termoBusca: string, filtroTribunal: string) => {
    setError('')
    setLoading(true)
    setBuscou(true)

    try {
      // Busca principal (geralmente por nome)
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

  // Debug: Monitorar mudanças no estado
  useEffect(() => {
      console.log("🔄 Estado processoSelecionado mudou:", processoSelecionado);
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
              {resultados.map((item: any, idx) => (
                <ResultadoItem key={item.id || idx} item={item} onBuscaProcesso={handleProcessoClick} />
              ))}
            </ul>
          )}
        </div>
      )}
      
      {/* Drawer Lateral de Histórico */}
      {/* Drawer Lateral de Histórico */}
      {processoSelecionado && (
          <>
            {/* Overlay */}
            <div 
                className="drawer-overlay"
                onClick={fecharHistorico}
            />
            
            {/* Drawer */}
            <div className="drawer-container animate-slideInRight">
                <div className="p-4 border-b border-border flex items-center justify-between bg-surface-hover">
                    <div className="flex items-center gap-3">
                        <div className="bg-primary/10 p-2 rounded-lg text-primary">
                            <FileText size={20} />
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg">Histórico do Processo</h3>
                            <p className="text-sm text-muted font-mono">{processoSelecionado}</p>
                        </div>
                    </div>
                    <button 
                        onClick={fecharHistorico}
                        className="text-muted hover:text-foreground transition-colors p-2 hover:bg-surface-active rounded-md"
                        title="Fechar Histórico"
                    >
                        <X size={20} />
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-0 bg-background custom-scrollbar">
                    {loadingHistorico ? (
                        <div className="flex flex-col items-center justify-center h-40 gap-3">
                            <div className="spinner" />
                            <span className="text-muted text-sm">Carregando histórico completo...</span>
                        </div>
                    ) : historicoProcesso.length === 0 ? (
                         <div className="text-center py-10 text-muted flex flex-col items-center gap-2">
                            <FileText size={32} className="opacity-20" />
                            <p>Nenhuma publicação encontrada para este processo.</p>
                         </div>
                    ) : (
                        <div className="flex flex-col">
                             <div className="sticky top-0 bg-background/95 backdrop-blur z-10 px-6 py-3 border-b border-border flex items-center justify-between text-xs text-muted uppercase tracking-wider font-semibold">
                                <span>{historicoProcesso.length} Publicações</span>
                                <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-primary/50"></span>
                                    <span>Ordem Cronológica</span>
                                </div>
                             </div>
                             
                             <div className="p-4 space-y-4">
                                {historicoProcesso.map((item, idx) => (
                                    <HistoricoItem key={idx} item={item} />
                                ))}
                             </div>
                        </div>
                    )}
                </div>
            </div>
          </>
      )}
    </div>
  )
}

function HistoricoItem({ item }: { item: any }) {
    const [expandido, setExpandido] = useState(false);
    const texto = item.texto || "";
    
    // Formatar data para ser mais legível
    const dataDisplay = item.data_disponibilizacao 
        ? new Date(item.data_disponibilizacao.split('/').reverse().join('-')).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })
        : item.data_disponibilizacao;

    return (
        <div className="relative pl-4 border-l-2 border-primary/30 hover:border-primary transition-colors pb-6 last:pb-0">
            {/* Timeline dot */}
            <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-background border-2 border-primary/50 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-primary/50"></div>
            </div>

            <div className="flex flex-col gap-2">
                <div className="flex items-start justify-between">
                    <div>
                        <span className="inline-block px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium mb-1 border border-primary/20">
                            {item.tribunal}
                        </span>
                        <div className="text-sm font-semibold text-text-primary">
                            {item.orgao}
                        </div>
                        {item.tipo_comunicacao && (
                            <div className="text-xs text-muted mt-0.5">
                                {item.tipo_comunicacao}
                            </div>
                        )}
                    </div>
                    <div className="text-xs font-mono text-muted whitespace-nowrap bg-surface px-2 py-1 rounded border border-border">
                        {item.data_disponibilizacao}
                    </div>
                </div>

                {/* Polos / Partes Compactas */}
                {(item.polos?.ativo?.length > 0 || item.polos?.passivo?.length > 0) && (
                     <div className="flex flex-wrap gap-2 text-xs mt-1 items-center opacity-80">
                        {item.polos.ativo?.map((p: string, i: number) => (
                            <span key={`A${i}`} className="text-emerald-500 font-medium truncate max-w-[150px]" title={p}>{p}</span>
                        ))}
                        {item.polos.ativo?.length && item.polos.passivo?.length && <span className="text-muted">vs</span>}
                        {item.polos.passivo?.map((p: string, i: number) => (
                            <span key={`P${i}`} className="text-red-500 font-medium truncate max-w-[150px]" title={p}>{p}</span>
                        ))}
                     </div>
                )}

                {/* Conteúdo Expansível */}
                <div className="mt-2">
                    <button 
                        onClick={() => setExpandido(!expandido)}
                        className="flex items-center gap-2 text-xs font-medium text-primary hover:text-primary-hover transition-colors"
                    >
                        {expandido ? <EyeOff size={14} /> : <Eye size={14} />}
                        {expandido ? "Ocultar conteúdo" : "Ler conteúdo"}
                    </button>

                    {expandido && (
                        <div className="mt-3 bg-surface p-3 rounded-md border border-border animate-fadeIn">
                             <p className="text-sm text-text-secondary leading-relaxed font-mono whitespace-pre-wrap max-h-[400px] overflow-y-auto custom-scrollbar">
                                {texto}
                             </p>
                             {item.link && (
                                <a href={item.link} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-muted hover:text-primary">
                                    <FileText size={12} /> Link Original
                                </a>
                             )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

// Componente legado para lista principal
function ResultadoItem({ item, onBuscaProcesso }: { item: any, onBuscaProcesso: (proc: string) => void }) {
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
