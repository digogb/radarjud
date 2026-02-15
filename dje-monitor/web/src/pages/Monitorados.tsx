import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Search, FileText } from 'lucide-react'
import { processoApi, Processo } from '../services/api'

export default function Monitorados() {
  const navigate = useNavigate()
  const [processos, setProcessos] = useState<Processo[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    loadProcessos()
  }, [])

  const loadProcessos = async () => {
    try {
      setLoading(true)
      const response = await processoApi.listar({ monitorado: true })
      setProcessos(response.data || [])
      setTotal(response.total || 0)
    } catch (error) {
      console.error('Erro ao carregar processos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDesmonitorar = async (id: string) => {
    try {
      await processoApi.desmonitorar(id)
      setProcessos((prev) => prev.filter((p) => p.id !== id))
      setTotal((prev) => prev - 1)
    } catch (err) {
      console.error('Erro ao remover monitoramento:', err)
    }
  }

  return (
    <div className="animate-fadeIn">
      <header className="page-header">
        <h1 className="page-title">Processos Monitorados</h1>
        <p className="page-subtitle">
          Acompanhe as atualizações dos seus processos em tempo real
        </p>
      </header>

      <div className="results-section">
        <div className="results-header">
          <h2 className="results-title">Seus Processos</h2>
          <span className="results-count">{total} processo(s) monitorado(s)</span>
        </div>

        {loading ? (
          <div className="loading">
            <div className="spinner" />
            <span className="loading-text">Carregando processos...</span>
          </div>
        ) : processos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <Eye size={32} />
            </div>
            <h3 className="empty-title">Nenhum processo monitorado</h3>
            <p className="empty-description">
              Busque um processo e clique no ícone de olho para começar a monitorar.
            </p>
            <button
              className="btn btn-primary mt-4"
              onClick={() => navigate('/busca')}
              style={{ marginTop: '16px' }}
            >
              <Search size={18} />
              Buscar Processo
            </button>
          </div>
        ) : (
          <ul className="processo-list">
            {processos.map((processo) => (
              <li key={processo.id} className="processo-item">
                <div className="processo-header">
                  <span
                    className="processo-numero"
                    onClick={() => navigate(`/processo/${processo.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {processo.numeroUnificado}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="processo-tribunal">{processo.tribunal}</span>
                    <button
                      className="btn btn-ghost text-primary"
                      onClick={() => handleDesmonitorar(processo.id)}
                      title="Remover monitoramento"
                    >
                      <EyeOff size={18} />
                    </button>
                  </div>
                </div>

                <div className="processo-info">
                  <div className="processo-info-item">
                    <span className="processo-info-label">Classe</span>
                    <span className="processo-info-value">{processo.classeNome || '-'}</span>
                  </div>
                  <div className="processo-info-item">
                    <span className="processo-info-label">Órgão Julgador</span>
                    <span className="processo-info-value">{processo.orgaoJulgadorNome || '-'}</span>
                  </div>
                  <div className="processo-info-item">
                    <span className="processo-info-label">Data Distribuição</span>
                    <span className="processo-info-value">
                      {processo.dataDistribuicao
                        ? new Date(processo.dataDistribuicao).toLocaleDateString('pt-BR')
                        : '-'}
                    </span>
                  </div>
                </div>

                {processo.partes && processo.partes.length > 0 && (
                  <div className="processo-partes">
                    {processo.partes.slice(0, 4).map((parte, idx) => (
                      <span
                        key={idx}
                        className={`parte-tag ${parte.polo === 'ATIVO' ? 'autor' : 'reu'}`}
                      >
                        {parte.tipoParte || parte.polo}: {parte.nome.split(' ').slice(0, 2).join(' ')}
                      </span>
                    ))}
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
