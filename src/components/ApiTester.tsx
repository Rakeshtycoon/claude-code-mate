import { useState, useEffect } from 'react'
import { Send, Globe, Key, Clock, CircleAlert as AlertCircle, CircleCheck as CheckCircle, ChevronDown, ChevronUp, Plus, Trash2, Play, Loader as Loader2, Copy, Check } from 'lucide-react'
import { supabase } from '../lib/supabase'
import type { ApiEndpoint, ApiEnvironment } from '../types'

interface TestResult {
  status: number | null
  statusText: string
  headers: Record<string, string>
  body: unknown
  duration: number
  error: string | null
}

export default function ApiTester() {
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([])
  const [environments, setEnvironments] = useState<ApiEnvironment[]>([])
  const [loading, setLoading] = useState(true)

  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null)
  const [baseUrl, setBaseUrl] = useState('https://api.duoo.live')
  const [authToken, setAuthToken] = useState('')
  const [uid, setUid] = useState('')
  const [queryParams, setQueryParams] = useState<{ key: string; value: string }[]>([
    { key: 'p', value: '1' },
    { key: 'v', value: '6.2.2' },
    { key: 'l', value: 'en-US' },
    { key: 'appName', value: 'Duoo' },
    { key: 'packageName', value: 'com.melot.meta' },
    { key: 'd', value: '' },
    { key: 'bizId', value: '1' },
  ])
  const [requestHeaders, setRequestHeaders] = useState<{ key: string; value: string }[]>([
    { key: 'Content-Type', value: 'application/json' },
  ])
  const [requestBody, setRequestBody] = useState('{}')
  const [showBody, setShowBody] = useState(false)
  const [showHeaders, setShowHeaders] = useState(false)
  const [showQuery, setShowQuery] = useState(true)

  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<TestResult | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    setLoading(true)
    const [{ data: eps }, { data: envs }] = await Promise.all([
      supabase.from('api_endpoints').select('*, module:api_modules(*)').order('path'),
      supabase.from('api_environments').select('*').eq('is_active', true).order('name'),
    ])
    setEndpoints(eps || [])
    setEnvironments(envs || [])
    if (envs && envs.length > 0) {
      setBaseUrl(envs[0].base_url)
    }
    setLoading(false)
  }

  function addQueryParam() {
    setQueryParams([...queryParams, { key: '', value: '' }])
  }

  function updateQueryParam(index: number, field: 'key' | 'value', value: string) {
    const updated = [...queryParams]
    updated[index][field] = value
    setQueryParams(updated)
  }

  function removeQueryParam(index: number) {
    setQueryParams(queryParams.filter((_, i) => i !== index))
  }

  function addHeader() {
    setRequestHeaders([...requestHeaders, { key: '', value: '' }])
  }

  function updateHeader(index: number, field: 'key' | 'value', value: string) {
    const updated = [...requestHeaders]
    updated[index][field] = value
    setRequestHeaders(updated)
  }

  function removeHeader(index: number) {
    setRequestHeaders(requestHeaders.filter((_, i) => i !== index))
  }

  function buildUrl(): string {
    if (!selectedEndpoint) return ''
    const params = queryParams
      .filter((p) => p.key && p.value)
      .map((p) => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value)}`)
      .join('&')
    return `${baseUrl}${selectedEndpoint.path}${params ? '?' + params : ''}`
  }

  async function runTest() {
    if (!selectedEndpoint) return
    setTesting(true)
    setResult(null)

    const url = buildUrl()
    const startTime = performance.now()

    try {
      const headers: Record<string, string> = {}
      requestHeaders.forEach((h) => {
        if (h.key && h.value) headers[h.key] = h.value
      })
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      let body: string | undefined
      if (['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method) && requestBody) {
        body = requestBody
      }

      const response = await fetch(url, {
        method: selectedEndpoint.method,
        headers,
        body,
      })

      const duration = Math.round(performance.now() - startTime)
      const responseHeaders: Record<string, string> = {}
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value
      })

      let responseBody: unknown
      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        responseBody = await response.json()
      } else {
        responseBody = await response.text()
      }

      setResult({
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
        body: responseBody,
        duration,
        error: null,
      })

      // Save to history
      await supabase.from('api_test_history').insert({
        endpoint_id: selectedEndpoint.id,
        base_url: baseUrl,
        full_url: url,
        method: selectedEndpoint.method,
        request_headers: headers,
        request_body: body ? JSON.parse(body) : {},
        response_status: response.status,
        response_body: typeof responseBody === 'object' ? responseBody : { text: responseBody },
        response_headers: responseHeaders,
        duration_ms: duration,
      })
    } catch (err) {
      const duration = Math.round(performance.now() - startTime)
      setResult({
        status: null,
        statusText: 'Error',
        headers: {},
        body: null,
        duration,
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    } finally {
      setTesting(false)
    }
  }

  async function copyResponse() {
    if (!result) return
    await navigator.clipboard.writeText(JSON.stringify(result.body, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getStatusColor = (status: number | null) => {
    if (!status) return 'text-error-400'
    if (status >= 200 && status < 300) return 'text-success-400'
    if (status >= 300 && status < 400) return 'text-warning-400'
    if (status >= 400) return 'text-error-400'
    return 'text-slate-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      {/* Left panel - Configuration */}
      <div className="space-y-4 overflow-auto">
        {/* Endpoint Selector */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Endpoint</label>
          <select
            value={selectedEndpoint?.id || ''}
            onChange={(e) => {
              const ep = endpoints.find((ep) => ep.id === e.target.value)
              setSelectedEndpoint(ep || null)
              setShowBody(ep?.method === 'POST' || ep?.method === 'PUT')
            }}
            className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
          >
            <option value="">Select an endpoint...</option>
            {endpoints.map((ep) => (
              <option key={ep.id} value={ep.id}>
                {ep.method} {ep.path} - {ep.description}
              </option>
            ))}
          </select>
        </div>

        {/* Environment & Auth */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-4">
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block flex items-center gap-2">
              <Globe className="w-3.5 h-3.5" />
              Environment
            </label>
            <select
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
            >
              {environments.map((env) => (
                <option key={env.id} value={env.base_url}>
                  {env.name} - {env.base_url}
                </option>
              ))}
              <option value="custom">Custom URL</option>
            </select>
            {baseUrl === 'custom' && (
              <input
                type="text"
                placeholder="https://api.example.com"
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full mt-2 px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
              />
            )}
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block flex items-center gap-2">
              <Key className="w-3.5 h-3.5" />
              Auth Token
            </label>
            <input
              type="text"
              placeholder="Bearer token or access token"
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary-500/50"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">User ID (uid)</label>
            <input
              type="text"
              placeholder="User ID"
              value={uid}
              onChange={(e) => setUid(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary-500/50"
            />
          </div>
        </div>

        {/* Query Parameters */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowQuery(!showQuery)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-800/40 transition-colors"
          >
            <span className="text-sm font-medium text-slate-300">Query Parameters</span>
            {showQuery ? (
              <ChevronUp className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            )}
          </button>
          {showQuery && (
            <div className="px-4 pb-4 space-y-2">
              {queryParams.map((param, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Key"
                    value={param.key}
                    onChange={(e) => updateQueryParam(i, 'key', e.target.value)}
                    className="flex-1 px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
                  />
                  <input
                    type="text"
                    placeholder="Value"
                    value={param.value}
                    onChange={(e) => updateQueryParam(i, 'value', e.target.value)}
                    className="flex-1 px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
                  />
                  <button
                    onClick={() => removeQueryParam(i)}
                    className="p-2 text-slate-500 hover:text-error-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={addQueryParam}
                className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add parameter
              </button>
            </div>
          )}
        </div>

        {/* Request Headers */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowHeaders(!showHeaders)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-800/40 transition-colors"
          >
            <span className="text-sm font-medium text-slate-300">Request Headers</span>
            {showHeaders ? (
              <ChevronUp className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            )}
          </button>
          {showHeaders && (
            <div className="px-4 pb-4 space-y-2">
              {requestHeaders.map((header, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Key"
                    value={header.key}
                    onChange={(e) => updateHeader(i, 'key', e.target.value)}
                    className="flex-1 px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
                  />
                  <input
                    type="text"
                    placeholder="Value"
                    value={header.value}
                    onChange={(e) => updateHeader(i, 'value', e.target.value)}
                    className="flex-1 px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-primary-500/50"
                  />
                  <button
                    onClick={() => removeHeader(i)}
                    className="p-2 text-slate-500 hover:text-error-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={addHeader}
                className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add header
              </button>
            </div>
          )}
        </div>

        {/* Request Body */}
        {selectedEndpoint && ['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method) && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowBody(!showBody)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-800/40 transition-colors"
            >
              <span className="text-sm font-medium text-slate-300">Request Body (JSON)</span>
              {showBody ? (
                <ChevronUp className="w-4 h-4 text-slate-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-500" />
              )}
            </button>
            {showBody && (
              <div className="px-4 pb-4">
                <textarea
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-sm font-mono text-slate-200 focus:outline-none focus:border-primary-500/50 resize-y"
                />
              </div>
            )}
          </div>
        )}

        {/* URL Preview & Send */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-4">
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Request URL</label>
            <code className="block p-3 bg-slate-950 border border-slate-800 rounded-lg text-sm font-mono text-primary-400 break-all">
              {buildUrl() || 'Select an endpoint to see URL'}
            </code>
          </div>
          <button
            onClick={runTest}
            disabled={!selectedEndpoint || testing}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-colors"
          >
            {testing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Send Request
              </>
            )}
          </button>
        </div>
      </div>

      {/* Right panel - Response */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-medium text-slate-300">Response</h3>
          {result && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs text-slate-400">{result.duration}ms</span>
              </div>
              {result.status !== null && (
                <span className={`text-sm font-bold ${getStatusColor(result.status)}`}>
                  {result.status} {result.statusText}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto p-4">
          {!result && !testing && (
            <div className="flex flex-col items-center justify-center h-full text-slate-600">
              <Send className="w-12 h-12 mb-4" />
              <p className="text-sm">Send a request to see the response</p>
            </div>
          )}

          {testing && (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-primary-400 mb-4" />
              <p className="text-sm text-slate-400">Sending request...</p>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {result.error && (
                <div className="flex items-start gap-3 p-4 bg-error-500/10 border border-error-500/30 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-error-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-error-400">Error</p>
                    <p className="text-sm text-error-300/80 mt-1">{result.error}</p>
                  </div>
                </div>
              )}

              {result.status !== null && result.status >= 200 && result.status < 300 && (
                <div className="flex items-center gap-2 p-3 bg-success-500/10 border border-success-500/30 rounded-lg">
                  <CheckCircle className="w-4 h-4 text-success-400" />
                  <span className="text-sm text-success-400">Request successful</span>
                </div>
              )}

              {/* Response Headers */}
              {Object.keys(result.headers).length > 0 && (
                <div>
                  <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Response Headers</h4>
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-1">
                    {Object.entries(result.headers).map(([key, value]) => (
                      <div key={key} className="flex gap-2 text-xs">
                        <span className="text-slate-500 shrink-0">{key}:</span>
                        <span className="text-slate-300 break-all">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Response Body */}
              {result.body !== null && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs text-slate-500 uppercase tracking-wider">Response Body</h4>
                    <button
                      onClick={copyResponse}
                      className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      {copied ? (
                        <Check className="w-3.5 h-3.5 text-success-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-slate-300 overflow-auto max-h-96">
                    {JSON.stringify(result.body, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
