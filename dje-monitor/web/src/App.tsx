import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Search, Eye, Bell, Radar } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Busca from './pages/Busca'
import Monitorados from './pages/Monitorados'
import ProcessoDetalhe from './pages/ProcessoDetalhe'
import './App.css'

function App() {

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/busca', icon: Search, label: 'Buscar Processo' },
    { path: '/monitorados', icon: Eye, label: 'Pessoas Monitoradas' },
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
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sync-status">
            <Bell size={16} />
            <span>Sistema ativo</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/busca" element={<Busca />} />
          <Route path="/monitorados" element={<Monitorados />} />
          <Route path="/processo/:id" element={<ProcessoDetalhe />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
