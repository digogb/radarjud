import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Eye, Bell, Clock, TrendingUp, RefreshCw, AlertCircle } from 'lucide-react'
import { dashboardApi, syncApi, DashboardResumo, AlteracaoDetectada } from '../services/api'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function Dashboard() {
  const navigate = useNavigate()
  const [resumo, setResumo] = useState<DashboardResumo | null>(null)
  const [alteracoes, setAlteracoes] = useState<AlteracaoDetectada[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [resumoData, alteracoesData] = await Promise.all([
        dashboardApi.getResumo(),
        dashboardApi.getAlteracoes(10),
      ])
      setResumo(resumoData)
      setAlteracoes(alteracoesData)
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      await syncApi.forcar()
      // Aguarda um pouco e recarrega
      setTimeout(() => {
        loadData()
        setSyncing(false)
      }, 2000)
    } catch (error) {
      console.error('Erro ao sincronizar:', error)
      setSyncing(false)
    }
  }

  const handleMarcarVistas = async () => {
    try {
      await dashboardApi.marcarVistas()
      loadData()
    } catch (error) {
      console.error('Erro ao marcar como vistas:', error)
    }
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span className="loading-text">Carregando dashboard...</span>
      </div>
    )
  }

  return (
    <div className="animate-fadeIn">
      <header className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Visão geral do monitoramento de processos</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleSync}
          disabled={syncing}
        >
          <RefreshCw size={18} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Sincronizando...' : 'Sincronizar'}
        </button>
      </header>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card animate-fadeIn delay-1">
          <div className="stat-header">
            <div className="stat-icon primary">
              <FileText size={24} />
            </div>
          </div>
          <div className="stat-value">{resumo?.totalProcessos || 0}</div>
          <div className="stat-label">Publicações Encontradas</div>
        </div>

        <div className="stat-card accent animate-fadeIn delay-2">
          <div className="stat-header">
            <div className="stat-icon accent">
              <Eye size={24} />
            </div>
          </div>
          <div className="stat-value">{resumo?.processosMonitorados || 0}</div>
          <div className="stat-label">Pessoas Monitoradas</div>
        </div>

        <div className="stat-card warning animate-fadeIn delay-3">
          <div className="stat-header">
            <div className="stat-icon warning">
              <Bell size={24} />
            </div>
          </div>
          <div className="stat-value">{resumo?.alteracoesNaoVistas || 0}</div>
          <div className="stat-label">Novas Alterações</div>
        </div>

        <div className="stat-card success animate-fadeIn delay-4">
          <div className="stat-header">
            <div className="stat-icon success">
              <Clock size={24} />
            </div>
          </div>
          <div className="stat-value text-lg">
            {resumo?.ultimaSync
              ? formatDistanceToNow(new Date(resumo.ultimaSync), { locale: ptBR, addSuffix: true })
              : 'Nunca'
            }
          </div>
          <div className="stat-label">Última Sincronização</div>
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="alerts-section animate-fadeIn delay-4">
        <div className="results-header">
          <h2 className="results-title">Alterações Recentes</h2>
          {alteracoes.length > 0 && (
            <button className="btn btn-ghost text-sm" onClick={handleMarcarVistas}>
              Marcar todas como vistas
            </button>
          )}
        </div>

        {alteracoes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <TrendingUp size={32} />
            </div>
            <h3 className="empty-title">Nenhuma alteração pendente</h3>
            <p className="empty-description">
              Quando houver atualizações nos seus processos monitorados, elas aparecerão aqui.
            </p>
          </div>
        ) : (
          <div>
            {alteracoes.map((alteracao) => (
              <div
                key={alteracao.id}
                className="alert-item"
                onClick={() => navigate('/monitorados')}
              >
                <div className="alert-icon new">
                  <AlertCircle size={20} />
                </div>
                <div className="alert-content">
                  <div className="alert-title">
                    {alteracao.dadosNovos?.pessoa
                      ? `${alteracao.dadosNovos.pessoa} — Nova Publicação`
                      : alteracao.tipo === 'NOVA_PUBLICACAO' ? 'Nova Publicação' : alteracao.tipo}
                  </div>
                  <div className="alert-description">
                    {!!alteracao.dadosNovos?.tribunal && `${alteracao.dadosNovos.tribunal as string} · `}
                    {(alteracao.dadosNovos?.tipo_comunicacao as string) || alteracao.processo?.numeroUnificado || alteracao.processoId}
                  </div>
                  <div className="alert-time">
                    {formatDistanceToNow(new Date(alteracao.detectadoEm), {
                      locale: ptBR,
                      addSuffix: true,
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
