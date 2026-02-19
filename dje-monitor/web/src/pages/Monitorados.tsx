import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Search, Plus, Bell, Clock, FileText, X, ChevronDown, ChevronUp, ExternalLink, Upload, CheckCircle, AlertCircle } from 'lucide-react'
import { pessoaMonitoradaApi, alertaApi, importacaoApi, PessoaMonitorada, PublicacaoResumo, ImportacaoStats } from '../services/api'

export default function Monitorados() {
  const navigate = useNavigate()
  const [pessoas, setPessoas] = useState<PessoaMonitorada[]>([])
  const [loading, setLoading] = useState(true)
  const [pessoaExpandida, setPessoaExpandida] = useState<number | null>(null)
  const [publicacoes, setPublicacoes] = useState<Record<number, PublicacaoResumo[]>>({})
  const [loadingPublicacoes, setLoadingPublicacoes] = useState<Record<number, boolean>>({})

  // Formulário para adicionar pessoa
  const [mostrarForm, setMostrarForm] = useState(false)
  const [formNome, setFormNome] = useState('')
  const [formCpf, setFormCpf] = useState('')
  const [formTribunal, setFormTribunal] = useState('')
  const [formIntervalo, setFormIntervalo] = useState(24)
  const [salvando, setSalvando] = useState(false)
  const [erroForm, setErroForm] = useState('')

  // Importação de planilha
  const [mostrarImport, setMostrarImport] = useState(false)
  const [arquivoImport, setArquivoImport] = useState<File | null>(null)
  const [dryRun, setDryRun] = useState(false)
  const [intervaloImport, setIntervaloImport] = useState(24)
  const [importando, setImportando] = useState(false)
  const [resultadoImport, setResultadoImport] = useState<ImportacaoStats | null>(null)
  const [erroImport, setErroImport] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Filtro de busca
  const [filtro, setFiltro] = useState('')

  const pessoasFiltradas = filtro.trim()
    ? pessoas.filter(p => {
        const q = filtro.trim().toLowerCase().replace(/\D/g, '') || filtro.trim().toLowerCase()
        const cpfLimpo = (p.cpf || '').replace(/\D/g, '')
        return (
          p.nome.toLowerCase().includes(filtro.trim().toLowerCase()) ||
          cpfLimpo.includes(q)
        )
      })
    : pessoas

  const tribunais = [
    '', 'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDFT', 'TJES', 'TJGO', 'TJMA',
    'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE', 'TJPI', 'TJPR', 'TJRJ', 'TJRN',
    'TJRO', 'TJRR', 'TJRS', 'TJSC', 'TJSE', 'TJSP', 'TJTO',
  ]

  useEffect(() => {
    carregarPessoas()
  }, [])

  const carregarPessoas = async () => {
    try {
      setLoading(true)
      const response = await pessoaMonitoradaApi.listar()
      setPessoas(response.items || [])
    } catch (error) {
      console.error('Erro ao carregar pessoas:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRemover = async (id: number) => {
    try {
      await pessoaMonitoradaApi.remover(id)
      setPessoas(prev => prev.filter(p => p.id !== id))
      if (pessoaExpandida === id) setPessoaExpandida(null)
    } catch (err) {
      console.error('Erro ao remover:', err)
    }
  }

  const handleExpandir = async (id: number) => {
    if (pessoaExpandida === id) {
      setPessoaExpandida(null)
      return
    }
    setPessoaExpandida(id)
    if (!publicacoes[id]) {
      setLoadingPublicacoes(prev => ({ ...prev, [id]: true }))
      try {
        const pubs = await pessoaMonitoradaApi.publicacoes(id)
        setPublicacoes(prev => ({ ...prev, [id]: pubs }))
      } catch (err) {
        console.error('Erro ao carregar publicações:', err)
      } finally {
        setLoadingPublicacoes(prev => ({ ...prev, [id]: false }))
      }
    }
  }

  const handleMarcarAlertasLidos = async (pessoaId: number) => {
    try {
      const alertas = await alertaApi.listar({ pessoa_id: pessoaId, lido: false })
      if (alertas.length > 0) {
        await alertaApi.marcarLidos(alertas.map(a => a.id))
      }
      setPessoas(prev =>
        prev.map(p => p.id === pessoaId ? { ...p, total_alertas_nao_lidos: 0 } : p)
      )
    } catch (err) {
      console.error('Erro ao marcar alertas:', err)
    }
  }

  const handleAdicionarPessoa = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formNome.trim()) return
    setSalvando(true)
    setErroForm('')
    try {
      const nova = await pessoaMonitoradaApi.criar({
        nome: formNome.trim(),
        cpf: formCpf.trim() || undefined,
        tribunal_filtro: formTribunal || undefined,
        intervalo_horas: formIntervalo,
      })
      setPessoas(prev => [nova, ...prev])
      setMostrarForm(false)
      setFormNome('')
      setFormCpf('')
      setFormTribunal('')
      setFormIntervalo(24)
    } catch (err: any) {
      setErroForm(err.response?.data?.detail || 'Erro ao adicionar pessoa')
    } finally {
      setSalvando(false)
    }
  }

  const handleImportarPlanilha = async () => {
    if (!arquivoImport) return
    setImportando(true)
    setErroImport('')
    setResultadoImport(null)
    try {
      const stats = await importacaoApi.importarPlanilha(arquivoImport, {
        dryRun,
        desativarExpirados: !dryRun,
        intervaloHoras: intervaloImport,
      })
      if (dryRun) {
        // Dry-run: mostra resultado no painel
        setResultadoImport(stats)
      } else {
        // Importação real: fecha painel e recarrega lista
        setMostrarImport(false)
        setArquivoImport(null)
        setResultadoImport(null)
        await carregarPessoas()
      }
    } catch (err: any) {
      setErroImport(err.response?.data?.detail || 'Erro ao importar planilha')
    } finally {
      setImportando(false)
    }
  }

  const formatarUltimoCheck = (ultimoCheck?: string): string => {
    if (!ultimoCheck) return 'Nunca verificado'
    const diff = Date.now() - new Date(ultimoCheck).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Agora mesmo'
    if (mins < 60) return `Há ${mins} min`
    const horas = Math.floor(mins / 60)
    if (horas < 24) return `Há ${horas}h`
    const dias = Math.floor(horas / 24)
    return `Há ${dias} dia(s)`
  }

  return (
    <div className="animate-fadeIn">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Pessoas Monitoradas</h1>
          <p className="page-subtitle">
            Acompanhe novas publicações no DJe automaticamente
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn btn-secondary"
            onClick={() => { setMostrarImport(!mostrarImport); setMostrarForm(false); setResultadoImport(null); setErroImport('') }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            {mostrarImport ? <X size={16} /> : <Upload size={16} />}
            {mostrarImport ? 'Cancelar' : 'Importar Planilha'}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => { setMostrarForm(!mostrarForm); setMostrarImport(false) }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            {mostrarForm ? <X size={16} /> : <Plus size={16} />}
            {mostrarForm ? 'Cancelar' : 'Adicionar Pessoa'}
          </button>
        </div>
      </header>

      {/* Barra de busca */}
      <div style={{ margin: '0 0 16px', position: 'relative' }}>
        <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
        <input
          type="text"
          className="input-field"
          placeholder="Filtrar por nome ou CPF..."
          value={filtro}
          onChange={e => setFiltro(e.target.value)}
          style={{ paddingLeft: '36px', paddingRight: filtro ? '36px' : undefined }}
        />
        {filtro && (
          <button
            onClick={() => setFiltro('')}
            style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}
          >
            <X size={15} />
          </button>
        )}
      </div>

      {/* Formulário de adição */}
      {mostrarForm && (
        <div className="card mb-6 animate-fadeIn">
          <h3 style={{ marginBottom: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Nova Pessoa para Monitorar
          </h3>
          <form onSubmit={handleAdicionarPessoa}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
              <div>
                <label className="search-field-label">Nome *</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Nome completo da parte"
                  value={formNome}
                  onChange={e => setFormNome(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="search-field-label">CPF (opcional)</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="000.000.000-00"
                  value={formCpf}
                  onChange={e => setFormCpf(e.target.value)}
                />
              </div>
              <div>
                <label className="search-field-label">Tribunal (opcional)</label>
                <select
                  className="input-field"
                  value={formTribunal}
                  onChange={e => setFormTribunal(e.target.value)}
                >
                  <option value="">Todos os tribunais</option>
                  {tribunais.filter(t => t).map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="search-field-label">Verificar a cada</label>
                <select
                  className="input-field"
                  value={formIntervalo}
                  onChange={e => setFormIntervalo(Number(e.target.value))}
                >
                  <option value={6}>6 horas</option>
                  <option value={12}>12 horas</option>
                  <option value={24}>24 horas</option>
                  <option value={48}>48 horas</option>
                </select>
              </div>
            </div>
            {erroForm && (
              <p style={{ color: 'var(--danger)', fontSize: '0.875rem', marginBottom: '12px' }}>{erroForm}</p>
            )}
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setMostrarForm(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary" disabled={salvando || !formNome.trim()}>
                {salvando
                  ? <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />
                  : <Plus size={15} />
                }
                {salvando ? 'Adicionando...' : 'Adicionar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Painel de importação de planilha */}
      {mostrarImport && (
        <div className="card mb-6 animate-fadeIn">
          <h3 style={{ marginBottom: '4px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Importar Planilha de Partes Adversas
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Selecione o arquivo <strong>pessoas.xlsx</strong>. O sistema extrairá automaticamente nome, CPF e data de prazo de cada parte adversa.
          </p>

          {/* Upload area */}
          <div
            style={{
              border: '2px dashed var(--border)',
              borderRadius: '8px',
              padding: '24px',
              textAlign: 'center',
              cursor: 'pointer',
              background: arquivoImport ? 'rgba(99,102,241,0.05)' : 'var(--surface)',
              transition: 'all 0.2s',
              marginBottom: '16px',
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              style={{ display: 'none' }}
              onChange={e => {
                const f = e.target.files?.[0] || null
                setArquivoImport(f)
                setResultadoImport(null)
                setErroImport('')
              }}
            />
            <Upload size={28} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
            {arquivoImport ? (
              <div>
                <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{arquivoImport.name}</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {(arquivoImport.size / 1024).toFixed(1)} KB — clique para trocar
                </p>
              </div>
            ) : (
              <div>
                <p style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Clique para selecionar o arquivo .xlsx</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>Somente arquivos Excel (.xlsx)</p>
              </div>
            )}
          </div>

          {/* Opções */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="checkbox"
                id="dryRun"
                checked={dryRun}
                onChange={e => setDryRun(e.target.checked)}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <label htmlFor="dryRun" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                Simulação (dry-run) — valida sem gravar no banco
              </label>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                Verificar a cada
              </label>
              <select
                className="input-field"
                value={intervaloImport}
                onChange={e => setIntervaloImport(Number(e.target.value))}
                style={{ width: 'auto', padding: '4px 8px' }}
              >
                <option value={6}>6 horas</option>
                <option value={12}>12 horas</option>
                <option value={24}>24 horas</option>
                <option value={48}>48 horas</option>
              </select>
            </div>
          </div>

          {/* Resultado */}
          {resultadoImport && (
            <div style={{
              background: erroImport ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
              border: `1px solid ${erroImport ? 'var(--danger)' : 'var(--success, #10b981)'}`,
              borderRadius: '8px',
              padding: '12px 16px',
              marginBottom: '16px',
              fontSize: '0.875rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
                <CheckCircle size={16} style={{ color: '#10b981' }} />
                {resultadoImport.dry_run ? 'Simulação concluída' : 'Importação concluída'}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '8px' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Total: </span><strong>{resultadoImport.total}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Importados: </span><strong style={{ color: '#10b981' }}>{resultadoImport.importados}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Pulados: </span><strong>{resultadoImport.pulados}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Erros: </span><strong style={{ color: resultadoImport.erros > 0 ? 'var(--danger)' : undefined }}>{resultadoImport.erros}</strong></div>
                {resultadoImport.expirados_desativados !== undefined && (
                  <div><span style={{ color: 'var(--text-muted)' }}>Expirados desativados: </span><strong>{resultadoImport.expirados_desativados}</strong></div>
                )}
              </div>
              {resultadoImport.dry_run && (
                <p style={{ marginTop: '8px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  Desmarque "Simulação" e clique em Importar para gravar os dados.
                </p>
              )}
            </div>
          )}

          {erroImport && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--danger)', fontSize: '0.875rem', marginBottom: '12px' }}>
              <AlertCircle size={15} />
              {erroImport}
            </div>
          )}

          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary" onClick={() => { setMostrarImport(false); setArquivoImport(null); setResultadoImport(null) }}>
              Fechar
            </button>
            <button
              className="btn btn-primary"
              onClick={handleImportarPlanilha}
              disabled={!arquivoImport || importando}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {importando
                ? <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />
                : <Upload size={15} />
              }
              {importando ? 'Importando...' : dryRun ? 'Simular' : 'Importar'}
            </button>
          </div>
        </div>
      )}

      <div className="results-section">
        <div className="results-header">
          <h2 className="results-title">Em Monitoramento</h2>
          <span className="results-count">
            {filtro ? `${pessoasFiltradas.length} de ${pessoas.length}` : `${pessoas.length}`} pessoa(s)
          </span>
        </div>

        {loading ? (
          <div className="loading">
            <div className="spinner" />
            <span className="loading-text">Carregando...</span>
          </div>
        ) : pessoas.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <Eye size={32} />
            </div>
            <h3 className="empty-title">Nenhuma pessoa monitorada</h3>
            <p className="empty-description">
              Busque uma pessoa e clique em "Monitorar", ou adicione manualmente acima.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => navigate('/busca')}
              style={{ marginTop: '16px' }}
            >
              <Search size={18} />
              Ir para Busca
            </button>
          </div>
        ) : pessoasFiltradas.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <Search size={32} />
            </div>
            <h3 className="empty-title">Nenhum resultado para "{filtro}"</h3>
            <p className="empty-description">Tente outro nome ou CPF.</p>
            <button className="btn btn-secondary" onClick={() => setFiltro('')} style={{ marginTop: '12px' }}>
              Limpar filtro
            </button>
          </div>
        ) : (
          <ul className="processo-list">
            {pessoasFiltradas.map(pessoa => (
              <li key={pessoa.id} className="processo-item">
                {/* Cabeçalho */}
                <div className="processo-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, flexWrap: 'wrap' }}>
                    <button
                      onClick={() => handleExpandir(pessoa.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', fontWeight: 600, fontSize: '1rem', textAlign: 'left', padding: 0 }}
                    >
                      {pessoa.nome}
                    </button>
                    <button
                      onClick={() => navigate('/busca', {
                        state: { nome: pessoa.nome, tribunal: pessoa.tribunal_filtro || undefined, autoSearch: true, hideMonitorar: true }
                      })}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', padding: 0 }}
                      title="Consultar publicações por nome no DJe"
                    >
                      <Search size={14} />
                    </button>
                    {pessoa.tribunal_filtro && (
                      <span className="processo-tribunal">{pessoa.tribunal_filtro}</span>
                    )}
                    {pessoa.total_alertas_nao_lidos > 0 && (
                      <button
                        style={{ background: 'var(--danger)', color: 'white', border: 'none', borderRadius: '12px', padding: '2px 10px', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                        onClick={() => handleMarcarAlertasLidos(pessoa.id)}
                        title="Clique para marcar alertas como lidos"
                      >
                        <Bell size={11} />
                        {pessoa.total_alertas_nao_lidos} novo(s)
                      </button>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <button
                      className="btn btn-ghost"
                      onClick={() => handleExpandir(pessoa.id)}
                      title={pessoaExpandida === pessoa.id ? 'Recolher' : 'Ver publicações'}
                    >
                      {pessoaExpandida === pessoa.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    <button
                      className="btn btn-ghost"
                      onClick={() => handleRemover(pessoa.id)}
                      title="Remover monitoramento"
                      style={{ color: 'var(--danger)' }}
                    >
                      <EyeOff size={16} />
                    </button>
                  </div>
                </div>

                {/* Info */}
                <div className="processo-info">
                  <div className="processo-info-item">
                    <span className="processo-info-label">Publicações</span>
                    <span className="processo-info-value">{pessoa.total_publicacoes}</span>
                  </div>
                  <div className="processo-info-item">
                    <span className="processo-info-label">
                      <Clock size={11} style={{ display: 'inline', marginRight: '3px' }} />
                      Último check
                    </span>
                    <span className="processo-info-value">{formatarUltimoCheck(pessoa.ultimo_check)}</span>
                  </div>
                  <div className="processo-info-item">
                    <span className="processo-info-label">Frequência</span>
                    <span className="processo-info-value">A cada {pessoa.intervalo_horas}h</span>
                  </div>
                  {pessoa.cpf && (
                    <div className="processo-info-item">
                      <span className="processo-info-label">CPF</span>
                      <span className="processo-info-value">{pessoa.cpf}</span>
                    </div>
                  )}
                  {pessoa.numero_processo && (
                    <div className="processo-info-item">
                      <span className="processo-info-label">Processo</span>
                      <span className="processo-info-value" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{pessoa.numero_processo}</span>
                    </div>
                  )}
                  {(pessoa.comarca || pessoa.uf) && (
                    <div className="processo-info-item">
                      <span className="processo-info-label">Comarca</span>
                      <span className="processo-info-value">{[pessoa.comarca, pessoa.uf].filter(Boolean).join(' — ')}</span>
                    </div>
                  )}
                  {pessoa.data_expiracao && (
                    <div className="processo-info-item">
                      <span className="processo-info-label">Expira em</span>
                      <span className="processo-info-value" style={{ color: new Date(pessoa.data_expiracao) < new Date() ? 'var(--danger)' : undefined }}>
                        {new Date(pessoa.data_expiracao).toLocaleDateString('pt-BR')}
                      </span>
                    </div>
                  )}
                </div>

                {/* Publicações expandidas */}
                {pessoaExpandida === pessoa.id && (
                  <div className="animate-fadeIn" style={{ marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                    {loadingPublicacoes[pessoa.id] ? (
                      <div className="loading" style={{ padding: '24px 0' }}>
                        <div className="spinner" />
                        <span className="loading-text">Carregando publicações...</span>
                      </div>
                    ) : (publicacoes[pessoa.id] || []).length === 0 ? (
                      <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px', fontSize: '0.9rem' }}>
                        <FileText size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
                        <p>Nenhuma publicação encontrada ainda.</p>
                        <p style={{ fontSize: '0.8rem' }}>O sistema verificará no próximo ciclo.</p>
                      </div>
                    ) : (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {(publicacoes[pessoa.id] || []).map(pub => (
                          <li key={pub.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px 16px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                                {pub.tribunal && (
                                  <span className="processo-tribunal" style={{ fontSize: '0.7rem' }}>{pub.tribunal}</span>
                                )}
                                {pub.tipo_comunicacao && (
                                  <span style={{ fontSize: '0.7rem', background: 'rgba(99,102,241,0.1)', color: 'var(--primary)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                                    {pub.tipo_comunicacao}
                                  </span>
                                )}
                                {pub.numero_processo && (
                                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>{pub.numero_processo}</span>
                                )}
                              </div>
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                  {pub.data_disponibilizacao}
                                </span>
                                {pub.link && (
                                  <a href={pub.link} target="_blank" rel="noreferrer" style={{ color: 'var(--text-muted)' }} title="Ver documento original">
                                    <FileText size={13} />
                                  </a>
                                )}
                                {pub.numero_processo && (
                                  <button
                                    onClick={() => navigate('/busca', {
                                      state: {
                                        nome: pub.numero_processo,
                                        autoSearch: true,
                                        hideMonitorar: true,
                                      }
                                    })}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', display: 'flex', alignItems: 'center', padding: 0 }}
                                    title="Consultar processo no DJe"
                                  >
                                    <ExternalLink size={13} />
                                  </button>
                                )}
                              </div>
                            </div>
                            {pub.orgao && (
                              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '4px 0' }}>{pub.orgao}</p>
                            )}
                            {pub.texto_resumo && (
                              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginTop: '6px' }}>
                                {pub.texto_resumo}
                              </p>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
