import { useState, useEffect, useMemo } from 'react'
import {
  Search,
  ChevronRight,
  Globe,
  Hash,
  FileText,
  Copy,
  Check,
  Filter,
  X
} from 'lucide-react'
import { supabase } from '../lib/supabase'
import type { ApiModule, ApiEndpoint } from '../types'

export default function ApiExplorer() {
  const [modules, setModules] = useState<ApiModule[]>([])
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const [expandedEndpoint, setExpandedEndpoint] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [methodFilter, setMethodFilter] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    setLoading(true)
    const [{ data: modulesData }, { data: endpointsData }] = await Promise.all([
      supabase.from('api_modules').select('*').order('name'),
      supabase.from('api_endpoints').select('*, module:api_modules(*)').order('path'),
    ])
    setModules(modulesData || [])
    setEndpoints(endpointsData || [])
    setLoading(false)
  }

  const filteredEndpoints = useMemo(() => {
    return endpoints.filter((ep) => {
      const matchesSearch =
        searchQuery === '' ||
        ep.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (ep.description && ep.description.toLowerCase().includes(searchQuery.toLowerCase()))
      const matchesModule = selectedModule === null || ep.module_id === selectedModule
      const matchesMethod = methodFilter === null || ep.method === methodFilter
      return matchesSearch && matchesModule && matchesMethod
    })
  }, [endpoints, searchQuery, selectedModule, methodFilter])

  const groupedEndpoints = useMemo(() => {
    const groups: Record<string, ApiEndpoint[]> = {}
    filteredEndpoints.forEach((ep) => {
      const moduleName = ep.module?.display_name || 'Unknown'
      if (!groups[moduleName]) groups[moduleName] = []
      groups[moduleName].push(ep)
    })
    return groups
  }, [filteredEndpoints])

  async function copyToClipboard(text: string, id: string) {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-success-500/20 text-success-400 border-success-500/30'
      case 'POST': return 'bg-primary-500/20 text-primary-400 border-primary-500/30'
      case 'PUT': return 'bg-warning-500/20 text-warning-400 border-warning-500/30'
      case 'DELETE': return 'bg-error-500/20 text-error-400 border-error-500/30'
      default: return 'bg-slate-700/50 text-slate-400 border-slate-600/30'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {modules.map((mod) => (
          <button
            key={mod.id}
            onClick={() => setSelectedModule(selectedModule === mod.id ? null : mod.id)}
            className={`p-4 rounded-xl border transition-all duration-200 text-left ${
              selectedModule === mod.id
                ? 'border-primary-500/50 bg-primary-500/10'
                : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-800/40'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: mod.color }}
              />
              <span className="text-sm font-semibold text-white">{mod.display_name}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color: mod.color }}>
              {mod.endpoint_count}
            </p>
            <p className="text-xs text-slate-500 mt-1">endpoints</p>
          </button>
        ))}
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search endpoints by path or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-900/60 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/30 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex gap-2">
          {/* Method filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <select
              value={methodFilter || ''}
              onChange={(e) => setMethodFilter(e.target.value || null)}
              className="pl-9 pr-8 py-2.5 bg-slate-900/60 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50 appearance-none cursor-pointer"
            >
              <option value="">All Methods</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          {selectedModule && (
            <button
              onClick={() => setSelectedModule(null)}
              className="px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700/60 transition-colors flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Clear filter
            </button>
          )}
        </div>
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Showing <span className="text-white font-medium">{filteredEndpoints.length}</span> of{' '}
          <span className="text-white font-medium">{endpoints.length}</span> endpoints
        </p>
      </div>

      {/* Endpoint List */}
      <div className="space-y-4">
        {Object.entries(groupedEndpoints).map(([moduleName, eps]) => (
          <div key={moduleName} className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40">
            <div className="px-4 py-3 bg-slate-800/40 border-b border-slate-800 flex items-center gap-2">
              <Hash className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-semibold text-slate-300">{moduleName}</h3>
              <span className="ml-auto text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                {eps.length}
              </span>
            </div>
            <div className="divide-y divide-slate-800/50">
              {eps.map((ep) => (
                <div key={ep.id}>
                  <button
                    onClick={() =>
                      setExpandedEndpoint(expandedEndpoint === ep.id ? null : ep.id)
                    }
                    className="w-full px-4 py-3 flex items-center gap-4 hover:bg-slate-800/30 transition-colors text-left"
                  >
                    <ChevronRight
                      className={`w-4 h-4 text-slate-500 transition-transform ${
                        expandedEndpoint === ep.id ? 'rotate-90' : ''
                      }`}
                    />
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold border ${getMethodColor(
                        ep.method
                      )}`}
                    >
                      {ep.method}
                    </span>
                    <code className="flex-1 text-sm font-mono text-slate-300 truncate">
                      {ep.path}
                    </code>
                    <span className="text-xs text-slate-500 hidden sm:block max-w-xs truncate">
                      {ep.description}
                    </span>
                  </button>

                  {expandedEndpoint === ep.id && (
                    <div className="px-4 py-4 bg-slate-800/20 border-t border-slate-800/50 space-y-3">
                      <div className="flex items-start gap-3">
                        <FileText className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Description</p>
                          <p className="text-sm text-slate-300">{ep.description || 'No description'}</p>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <Globe className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                        <div className="flex-1">
                          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Full URL</p>
                          <div className="flex items-center gap-2">
                            <code className="text-sm font-mono text-primary-400 break-all">
                              https://api.duoo.live{ep.path}
                            </code>
                            <button
                              onClick={() =>
                                copyToClipboard(`https://api.duoo.live${ep.path}`, ep.id)
                              }
                              className="p-1.5 rounded hover:bg-slate-700/50 transition-colors shrink-0"
                            >
                              {copiedId === ep.id ? (
                                <Check className="w-3.5 h-3.5 text-success-400" />
                              ) : (
                                <Copy className="w-3.5 h-3.5 text-slate-500" />
                              )}
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <Hash className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Endpoint ID</p>
                          <code className="text-xs font-mono text-slate-400">{ep.id}</code>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {filteredEndpoints.length === 0 && (
          <div className="text-center py-16">
            <Search className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 text-lg">No endpoints found</p>
            <p className="text-slate-600 text-sm mt-1">Try adjusting your search or filters</p>
          </div>
        )}
      </div>
    </div>
  )
}
