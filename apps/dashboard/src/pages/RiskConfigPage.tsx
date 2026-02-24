import React, { useEffect, useState } from 'react'
import { useConfigStore } from '../store'
import { createApiClient } from '../api/client'

export const RiskConfigPage: React.FC = () => {
  const { currentConfig, setConfig, versions, setVersions } = useConfigStore()
  const [editedConfig, setEditedConfig] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await api.getRiskConfig()
        const vers = await api.getRiskConfigVersions()
        setConfig(config)
        setVersions(vers)
        setEditedConfig(config)
      } catch (error) {
        console.error('Failed to fetch config:', error)
      }
    }

    fetchConfig()
  }, [api, setConfig, setVersions])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.updateRiskConfig(editedConfig)
      setConfig(updated)
      setMessage({ type: 'success', text: 'Config updated successfully' })
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message })
    } finally {
      setSaving(false)
    }
  }

  const handleRollback = async (versionId: string) => {
    try {
      const config = await api.rollbackRiskConfig(versionId)
      setConfig(config)
      setEditedConfig(config)
      setMessage({ type: 'success', text: 'Rolled back successfully' })
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message })
    }
  }

  if (!editedConfig) {
    return <div className="text-white">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Risk Configuration</h1>

      {message && (
        <div className={`alert ${
          message.type === 'success'
            ? 'alert-success'
            : 'alert-danger'
        }`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Config Editor */}
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h2 className="text-xl font-bold">Current Configuration</h2>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {Object.entries(editedConfig).map(([key, value]: [string, any]) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-slate-300 mb-2 capitalize">
                    {key.replace(/_/g, ' ')}
                  </label>
                  <input
                    type={typeof value === 'number' ? 'number' : 'text'}
                    value={value}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        [key]: typeof value === 'number' ? parseFloat(e.target.value) : e.target.value,
                      })
                    }
                    className="input w-full"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn btn-primary flex-1 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Configuration'}
              </button>
              <button
                onClick={() => setEditedConfig(currentConfig)}
                className="btn btn-secondary flex-1"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        {/* Version History */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-bold">Version History</h2>
          </div>
          <div className="card-body max-h-96 overflow-auto">
            <div className="space-y-2">
              {versions.length === 0 ? (
                <p className="text-slate-400 text-sm">No versions yet</p>
              ) : (
                versions.map((version) => (
                  <div
                    key={version.id}
                    className="p-3 bg-slate-700/50 rounded-lg text-sm space-y-2"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-white font-mono text-xs">{version.id.substring(0, 8)}</p>
                        <p className="text-slate-400 text-xs">{new Date(version.created_at).toLocaleDateString()}</p>
                      </div>
                      <button
                        onClick={() => handleRollback(version.id)}
                        className="text-yellow-400 hover:text-yellow-300 text-xs font-medium"
                      >
                        Rollback
                      </button>
                    </div>
                    <p className="text-slate-300 text-xs">{version.description}</p>
                    <p className="text-slate-500 text-xs">by {version.created_by}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
