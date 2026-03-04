import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Search, Eye, Bell, Radar, TrendingUp, Settings, LogOut, User, KeyRound } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Busca from './pages/Busca'
import Monitorados from './pages/Monitorados'
import Oportunidades from './pages/Oportunidades'
import Parametrizacao from './pages/Parametrizacao'
import ProcessoDetalhe from './pages/ProcessoDetalhe'
import AlterarSenha from './pages/AlterarSenha'
import LoginPage from './pages/LoginPage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuth } from './contexts/AuthContext'
import './App.css'

function AppLayout() {
  const { user, logout } = useAuth()

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/busca', icon: Search, label: 'Buscar Processo' },
    { path: '/monitorados', icon: Eye, label: 'Pessoas Monitoradas' },
    { path: '/oportunidades', icon: TrendingUp, label: 'Oportunidades' },
    { path: '/parametrizacao', icon: Settings, label: 'Parametrização' },
  ]

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">
              <Radar size={24} />
            </div>
            <div className="logo-text">
              <span className="logo-title">Radar</span>
              <span className="logo-subtitle">Jud</span>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          {user && (
            <div style={{ borderTop: '1px solid #334155', paddingTop: '0.5rem', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8', fontSize: '0.8rem' }}>
                <User size={14} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.name}
                </span>
              </div>
              <div style={{ color: '#475569', fontSize: '0.7rem', paddingLeft: '1.3rem', marginTop: '0.15rem' }}>
                {user.role}
              </div>
              <NavLink
                to="/alterar-senha"
                style={({ isActive }) => ({
                  display: 'flex', alignItems: 'center', gap: '0.4rem',
                  color: isActive ? '#93c5fd' : '#64748b',
                  fontSize: '0.75rem', textDecoration: 'none',
                  paddingLeft: '1.3rem', marginTop: '0.3rem',
                })}
              >
                <KeyRound size={12} />
                Alterar senha
              </NavLink>
            </div>
          )}
          <div className="sync-status">
            <Bell size={16} />
            <span>Sistema ativo</span>
          </div>
          <button
            onClick={logout}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              background: 'none', border: 'none', color: '#64748b',
              cursor: 'pointer', fontSize: '0.8rem', padding: '0.4rem 0',
              width: '100%', marginTop: '0.25rem',
            }}
          >
            <LogOut size={14} />
            Sair
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/busca" element={<Busca />} />
          <Route path="/monitorados" element={<Monitorados />} />
          <Route path="/oportunidades" element={<Oportunidades />} />
          <Route path="/parametrizacao" element={<Parametrizacao />} />
          <Route path="/processo/:id" element={<ProcessoDetalhe />} />
          <Route path="/alterar-senha" element={<AlterarSenha />} />
          <Route path="/403" element={
            <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
              <h2>Acesso negado</h2>
              <p>Você não tem permissão para acessar esta página.</p>
            </div>
          } />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default App
