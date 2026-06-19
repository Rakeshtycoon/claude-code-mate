import { useState, useEffect } from 'react'
import { Plus, Globe, Check, X, Pencil, Trash2, Loader as Loader2, CircleAlert as AlertCircle } from 'lucide-react'
import { supabase } from '../lib/supabase'
import type { ApiEnvironment } from '../types'

export default function Environments() {
  const [environments, setEnvironments] = useState<ApiEnvironment[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const [formData, setFormData] = useState({
    name: '',
    base_url: '',
    description: '',
    is_active: true,
  })

  useEffect(() => {
    fetchEnvironments()
  }, [])

  async function fetchEnvironments() {
    setLoading(true)
    const { data, error } = await supabase
      .from('api_environments')
      .select('*')
      .order('created_at')

    if (error) {
      console.error('Error fetching environments:', error)
    } else {
      setEnvironments(data || [])
    }
    setLoading(false)
  }

  function resetForm() {
    setFormData({ name: '', base_url: '', description: '', is_active: true })
    setEditingId(null)
    setError('')
  }

  function startEdit(env: ApiEnvironment) {
    setFormData({
      name: env.name,
      base_url: env.base_url,
      description: env.description || '',
      is_active: env.is_active,
    })
    setEditingId(env.id)
    setShowForm(true)
    setError('')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!formData.name.trim() || !formData.base_url.trim()) {
      setError('Name and Base URL are required')
      return
    }

    try {
      if (editingId) {
        await supabase
          .from('api_environments')
          .update(formData)
          .eq('id', editingId)
      } else {
        await supabase.from('api_environments').insert(formData)
      }
      resetForm()
      setShowForm(false)
      fetchEnvironments()
    } catch (err) {
      setError('Failed to save environment')
    }
  }

  async function deleteEnvironment(id: string) {
    if (!confirm('Delete this environment?')) return
    await supabase.from('api_environments').delete().eq('id', id)
    fetchEnvironments()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Add button */}
      <div className="flex justify-end">
        <button
          onClick={() => {
            resetForm()
            setShowForm(!showForm)
          }}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'Add Environment'}
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4"
        >
          {error && (
            <div className="flex items-center gap-2 p-3 bg-error-500/10 border border-error-500/30 rounded-lg text-sm text-error-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Production"
                className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary-500/50"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Base URL</label>
              <input
                type="text"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                placeholder="https://api.example.com"
                className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary-500/50"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional description"
              className="w-full px-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary-500/50"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-primary-500 focus:ring-primary-500/30"
            />
            <label htmlFor="is_active" className="text-sm text-slate-300">Active</label>
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                resetForm()
              }}
              className="px-4 py-2.5 bg-slate-800/60 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700/60 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {editingId ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      )}

      {/* Environments List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {environments.map((env) => (
          <div
            key={env.id}
            className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <Globe className="w-5 h-5 text-primary-400" />
                <h3 className="text-base font-semibold text-white">{env.name}</h3>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => startEdit(env)}
                  className="p-1.5 text-slate-500 hover:text-primary-400 transition-colors"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteEnvironment(env.id)}
                  className="p-1.5 text-slate-500 hover:text-error-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <code className="block text-sm font-mono text-primary-400 mb-3 break-all">
              {env.base_url}
            </code>

            {env.description && (
              <p className="text-sm text-slate-400 mb-3">{env.description}</p>
            )}

            <div className="flex items-center gap-2">
              {env.is_active ? (
                <span className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-success-500/15 text-success-400 border border-success-500/30">
                  <Check className="w-3 h-3" />
                  Active
                </span>
              ) : (
                <span className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-slate-700/50 text-slate-400 border border-slate-600/30">
                  <X className="w-3 h-3" />
                  Inactive
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {environments.length === 0 && (
        <div className="text-center py-16">
          <Globe className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-500 text-lg">No environments configured</p>
          <p className="text-slate-600 text-sm mt-1">Add your first API environment</p>
        </div>
      )}
    </div>
  )
}
