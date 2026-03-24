import { useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Search, Eye, Bell, Radar, TrendingUp, Settings, LogOut, User, KeyRound, Sun, Moon, Menu, X } from 'lucide-react'
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
import { useTheme } from './contexts/ThemeContext'
import './App.css'

function AppLayout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard', shortLabel: 'Home' },
    { path: '/busca', icon: Search, label: 'Buscar Processo', shortLabel: 'Busca' },
    { path: '/monitorados', icon: Eye, label: 'Pessoas Monitoradas', shortLabel: 'Monitorados' },
    { path: '/oportunidades', icon: TrendingUp, label: 'Oportunidades', shortLabel: 'Oportun.' },
    { path: '/parametrizacao', icon: Settings, label: 'Parametrização', shortLabel: 'Config' },
  ]

  const closeMobileMenu = () => setMobileMenuOpen(false)

  return (
    <div className="app">
      {/* Mobile header */}
      <header className="mobile-header">
        <div className="logo">
          <div className="logo-icon" style={{ width: 36, height: 36 }}>
            <Radar size={18} />
          </div>
          <div className="logo-text">
            <span className="logo-title" style={{ fontSize: '1rem' }}>Radar</span>
            <span className="logo-subtitle" style={{ fontSize: '0.75rem' }}>Jud</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="theme-toggle" onClick={toggleTheme} style={{ margin: 0, padding: 8 }} title={theme === 'dark' ? 'Modo claro' : 'Modo escuro'}>
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </header>

      {/* Mobile drawer overlay */}
      {mobileMenuOpen && <div className="mobile-overlay" onClick={closeMobileMenu} />}

      {/* Sidebar — also serves as mobile drawer */}
      <aside className={`sidebar ${mobileMenuOpen ? 'sidebar-open' : ''}`}>
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
          <button className="mobile-close-btn" onClick={closeMobileMenu}>
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={closeMobileMenu}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          {user && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.5rem', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                <User size={14} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.name}
                </span>
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem', paddingLeft: '1.3rem', marginTop: '0.15rem' }}>
                {user.role}
              </div>
              <NavLink
                to="/alterar-senha"
                onClick={closeMobileMenu}
                style={({ isActive }) => ({
                  display: 'flex', alignItems: 'center', gap: '0.4rem',
                  color: isActive ? 'var(--primary-hover)' : 'var(--text-muted)',
                  fontSize: '0.75rem', textDecoration: 'none',
                  paddingLeft: '1.3rem', marginTop: '0.3rem',
                })}
              >
                <KeyRound size={12} />
                Alterar senha
              </NavLink>
            </div>
          )}
          <button className="theme-toggle" onClick={toggleTheme} title={theme === 'dark' ? 'Modo claro' : 'Modo escuro'}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            <span>{theme === 'dark' ? 'Modo claro' : 'Modo escuro'}</span>
          </button>
          <div className="sync-status">
            <Bell size={16} />
            <span>Sistema ativo</span>
          </div>
          <button
            onClick={() => { closeMobileMenu(); logout(); }}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              background: 'none', border: 'none', color: 'var(--text-muted)',
              cursor: 'pointer', fontSize: '0.8rem', padding: '0.4rem 0',
              width: '100%', marginTop: '0.25rem', fontFamily: 'inherit',
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
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <h2>Acesso negado</h2>
              <p>Você não tem permissão para acessar esta página.</p>
            </div>
          } />
        </Routes>
      </main>

      {/* Bottom navigation — mobile only */}
      <nav className="bottom-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon size={20} />
            <span>{item.shortLabel}</span>
          </NavLink>
        ))}
      </nav>
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
