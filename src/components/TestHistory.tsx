import { useState, useEffect } from 'react'
import {
  Clock,
  Trash2,
  ChevronDown,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Loader2
} from 'lucide-react'
import { supabase } from '../lib/supabase'
import type { ApiTestHistory } from '../types'

export default function TestHistory() {
  const [history, setHistory] = useState<ApiTestHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    fetchHistory()
  }, [])

  async function fetchHistory() {
    setLoading(true)
    const { data, error } = await supabase
      .from('api_test_history')
      .select('*, endpoint:api_endpoints(path, module:api_modules(display_name, color))')
      .order('created_at', { ascending: false })
      .limit(100)

    if (error) {
      console.error('Error fetching history:', error)
    } else {
      setHistory(data || [])
    }
    setLoading(false)
  }

  async function clearHistory() {
    if (!confirm('Are you sure you want to clear all test history?')) return
    await supabase.from('api_test_history').delete().neq('id', '00000000-0000-0000-0000-000000000000')
    fetchHistory()
  }

  async function deleteItem(id: string) {
    await supabase.from('api_test_history').delete().eq('id', id)
    fetchHistory()
  }

  const getStatusColor = (status: number | null) => {
    if (!status) return 'bg-error-500/20 text-error-400 border-error-500/30'
    if (status >= 200 && status < 300) return 'bg-success-500/20 text-success-400 border-success-500/30'
    if (status >= 300 && status < 400) return 'bg-warning-500/20 text-warning-400 border-warning-500/30'
    return 'bg-error-500/20 text-error-400 border-error-500/30'
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          <span className="text-white font-medium">{history.length}</span> test records
        </p>
        <div className="flex gap-2">
          <button
            onClick={fetchHistory}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700/60 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={clearHistory}
            className="flex items-center gap-2 px-3 py-2 bg-error-500/10 border border-error-500/30 rounded-lg text-sm text-error-400 hover:bg-error-500/20 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Clear All
          </button>
        </div>
      </div>

      {/* History List */}
      {history.length === 0 ? (
        <div className="text-center py-16">
          <Clock className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-500 text-lg">No test history yet</p>
          <p className="text-slate-600 text-sm mt-1">Run some API tests to see them here</p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((item) => (
            <div
              key={item.id}
              className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40 hover:border-slate-700 transition-colors"
            >
              <button
                onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                className="w-full px-4 py-3 flex items-center gap-4 text-left"
              >
                <ChevronDown
                  className={`w-4 h-4 text-slate-500 transition-transform shrink-0 ${
                    expandedId === item.id ? 'rotate-180' : ''
                  }`}
                />

                {/* Status */}
                <span
                  className={`px-2 py-0.5 rounded text-xs font-bold border shrink-0 ${getStatusColor(
                    item.response_status
                  )}`}
                >
                  {item.response_status || 'ERR'}
                </span>

                {/* Method & Path */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-slate-500">{item.method}</span>
                    <code className="text-sm font-mono text-slate-300 truncate">{item.full_url}</code>
                  </div>
                </div>

                {/* Module badge */}
                {(item as any).endpoint?.module && (
                  <span
                    className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium border shrink-0"
                    style={{
                      backgroundColor: `${(item as any).endpoint.module.color}20`,
                      borderColor: `${(item as any).endpoint.module.color}40`,
                      color: (item as any).endpoint.module.color,
                    }}
                  >
                    {(item as any).endpoint.module.display_name}
                  </span>
                )}

                {/* Duration */}
                <div className="flex items-center gap-1.5 text-xs text-slate-500 shrink-0">
                  <Clock className="w-3.5 h-3.5" />
                  {item.duration_ms}ms
                </div>

                {/* Time */}
                <span className="hidden md:block text-xs text-slate-500 shrink-0">
                  {formatDate(item.created_at)}
                </span>

                {/* Delete */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteItem(item.id)
                  }}
                  className="p-1.5 text-slate-600 hover:text-error-400 transition-colors shrink-0"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </button>

              {expandedId === item.id && (
                <div className="px-4 pb-4 border-t border-slate-800/50 space-y-4">
                  {/* Request */}
                  <div className="pt-3">
                    <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Request</h4>
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
                      <div className="text-xs">
                        <span className="text-slate-500">URL:</span>{' '}
                        <code className="text-primary-400 break-all">{item.full_url}</code>
                      </div>
                      {Object.keys(item.request_headers).length > 0 && (
                        <div className="text-xs">
                          <span className="text-slate-500">Headers:</span>
                          <pre className="mt-1 text-slate-400">
                            {JSON.stringify(item.request_headers, null, 2)}
                          </pre>
                        </div>
                      )}
                      {Object.keys(item.request_body).length > 0 && (
                        <div className="text-xs">
                          <span className="text-slate-500">Body:</span>
                          <pre className="mt-1 text-slate-400">
                            {JSON.stringify(item.request_body, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Response */}
                  <div>
                    <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Response</h4>
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
                      {item.error_message ? (
                        <div className="flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-error-400 shrink-0 mt-0.5" />
                          <span className="text-sm text-error-400">{item.error_message}</span>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-success-400" />
                            <span className={`text-sm font-medium ${getStatusColor(item.response_status).split(' ')[1]}`}>
                              Status: {item.response_status}
                            </span>
                          </div>
                          {Object.keys(item.response_headers).length > 0 && (
                            <div className="text-xs">
                              <span className="text-slate-500">Headers:</span>
                              <pre className="mt-1 text-slate-400">
                                {JSON.stringify(item.response_headers, null, 2)}
                              </pre>
                            </div>
                          )}
                          {Object.keys(item.response_body).length > 0 && (
                            <div className="text-xs">
                              <span className="text-slate-500">Body:</span>
                              <pre className="mt-1 text-slate-400 max-h-64 overflow-auto">
                                {JSON.stringify(item.response_body, null, 2)}
                              </pre>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
