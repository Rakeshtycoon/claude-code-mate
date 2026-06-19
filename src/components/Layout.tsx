import { useState, type ReactNode } from 'react'
import {
  Zap,
  Globe,
  History,
  Upload,
  ChevronLeft,
  ChevronRight,
  Shield,
  Terminal
} from 'lucide-react'

interface LayoutProps {
  children: ReactNode
  activeTab: string
  onTabChange: (tab: string) => void
}

const navItems = [
  { id: 'explorer', label: 'API Explorer', icon: Zap },
  { id: 'tester', label: 'API Tester', icon: Terminal },
  { id: 'history', label: 'Test History', icon: History },
  { id: 'environments', label: 'Environments', icon: Globe },
  { id: 'uploads', label: 'File Uploads', icon: Upload },
]

export default function Layout({ children, activeTab, onTabChange }: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-slate-800 bg-slate-900/80 backdrop-blur-sm transition-all duration-300 ${
          collapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-slate-800">
          <Shield className="w-8 h-8 text-primary-400 shrink-0" />
          {!collapsed && (
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">API Explorer</h1>
              <p className="text-xs text-slate-400">Duoo Reverse Engineering</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-primary-500/15 text-primary-400 border border-primary-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-5 h-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </button>
            )
          })}
        </nav>

        {/* Collapse toggle */}
        <div className="px-2 py-3 border-t border-slate-800">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center w-full px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <>
                <ChevronLeft className="w-5 h-5" />
                <span className="ml-2 text-sm">Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm">
          <div>
            <h2 className="text-xl font-semibold text-white">
              {navItems.find((n) => n.id === activeTab)?.label}
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {activeTab === 'explorer' && 'Browse and search all 270 API endpoints'}
              {activeTab === 'tester' && 'Test API endpoints with custom parameters'}
              {activeTab === 'history' && 'View past API test executions'}
              {activeTab === 'environments' && 'Manage API base URLs and environments'}
              {activeTab === 'uploads' && 'Upload and manage APK/config files'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-success-500/15 text-success-400 border border-success-500/30">
              270 Endpoints
            </span>
            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-accent-500/15 text-accent-400 border border-accent-500/30">
              11 Modules
            </span>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
