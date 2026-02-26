import React, { useEffect, useState } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'

interface SettingsResponse {
  settings: Record<string, any>
  db_status: {
    db_url: string
    counts: Record<string, number>
  }
}

export const SettingsPage: React.FC = () => {
  const api = createApiClient(getApiBaseUrl(), localStorage.getItem('token') || '')
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState<Record<string, any>>({})
  const [dbStatus, setDbStatus] = useState<SettingsResponse['db_status'] | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [restartRequired, setRestartRequired] = useState<string[]>([])

  const [binanceKey, setBinanceKey] = useState('')
  const [binanceSecret, setBinanceSecret] = useState('')
  const [telegramToken, setTelegramToken] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')

  const loadSettings = async () => {
    try {
      setLoading(true)
      const res: SettingsResponse = await api.getSettings()
      setSettings(res.settings)
      setDbStatus(res.db_status)
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to load settings: ${err.message || err}` })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  const handleSave = async () => {
    try {
      setMessage(null)
      const payload: Record<string, any> = {
        ...settings,
        persist: 'both',
      }

      if (binanceKey) payload.binance_api_key = binanceKey
      if (binanceSecret) payload.binance_api_secret = binanceSecret
      if (telegramToken) payload.telegram_bot_token = telegramToken
      if (openaiKey) payload.openai_api_key = openaiKey
      if (anthropicKey) payload.anthropic_api_key = anthropicKey

      const res = await api.updateSettings(payload)
      setSettings(res.settings)
      setRestartRequired(res.restart_required || [])
      setMessage({ type: 'success', text: 'Settings saved successfully' })
      setBinanceKey('')
      setBinanceSecret('')
      setTelegramToken('')
      setOpenaiKey('')
      setAnthropicKey('')
    } catch (err: any) {
      setMessage({ type: 'error', text: `Save failed: ${err.message || err}` })
    }
  }

  const handleTestBinance = async () => {
    try {
      const res = await api.testBinance()
      setMessage({
        type: res.ok ? 'success' : 'error',
        text: res.ok ? `Binance OK (${res.base_url})` : `Binance failed: ${res.error || res.status_code}`,
      })
    } catch (err: any) {
      setMessage({ type: 'error', text: `Binance test failed: ${err.message || err}` })
    }
  }

  const handleTestTelegram = async () => {
    try {
      const res = await api.testTelegram()
      setMessage({
        type: res.ok ? 'success' : 'error',
        text: res.ok ? `Telegram OK (${res.result?.username || 'bot'})` : `Telegram failed: ${res.error || 'unknown'}`,
      })
    } catch (err: any) {
      setMessage({ type: 'error', text: `Telegram test failed: ${err.message || err}` })
    }
  }

  if (loading) {
    return <div className="text-white">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">System Settings</h1>

      {message && (
        <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-danger'}`}>
          {message.text}
        </div>
      )}

      {restartRequired.length > 0 && (
        <div className="alert alert-warning">
          Changes applied. Restart recommended for: {restartRequired.join(', ')}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h2 className="text-xl font-bold">Runtime Configuration</h2>
          </div>
          <div className="card-body space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Mode</label>
                <select
                  className="input w-full"
                  value={settings.env || 'demo'}
                  onChange={(e) => setSettings({ ...settings, env: e.target.value })}
                >
                  <option value="demo">Demo</option>
                  <option value="live">Live</option>
                </select>
              </div>
              <div className="flex items-center gap-3 mt-7">
                <input
                  type="checkbox"
                  checked={!!settings.binance_testnet}
                  onChange={(e) => setSettings({ ...settings, binance_testnet: e.target.checked })}
                />
                <span className="text-sm text-slate-300">Use Binance Testnet</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Binance API Key</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  className="input w-full"
                  value={binanceKey}
                  onChange={(e) => setBinanceKey(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Binance API Secret</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  className="input w-full"
                  value={binanceSecret}
                  onChange={(e) => setBinanceSecret(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Telegram Bot Token</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  className="input w-full"
                  value={telegramToken}
                  onChange={(e) => setTelegramToken(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Telegram Admin IDs</label>
                <input
                  type="text"
                  className="input w-full"
                  value={settings.telegram_admin_ids || ''}
                  onChange={(e) => setSettings({ ...settings, telegram_admin_ids: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Telegram Trader IDs</label>
                <input
                  type="text"
                  className="input w-full"
                  value={settings.telegram_trader_ids || ''}
                  onChange={(e) => setSettings({ ...settings, telegram_trader_ids: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">LLM Provider</label>
                <select
                  className="input w-full"
                  value={settings.selected_llm || 'mock'}
                  onChange={(e) => setSettings({ ...settings, selected_llm: e.target.value })}
                >
                  <option value="mock">Mock</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="local">Local</option>
                </select>
              </div>
              <div className="flex items-center gap-3 mt-7">
                <input
                  type="checkbox"
                  checked={!!settings.use_local_llm}
                  onChange={(e) => setSettings({ ...settings, use_local_llm: e.target.checked })}
                />
                <span className="text-sm text-slate-300">Use Local LLM</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">OpenAI API Key</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  className="input w-full"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">OpenAI Model</label>
                <input
                  type="text"
                  className="input w-full"
                  value={settings.openai_model || 'gpt-4'}
                  onChange={(e) => setSettings({ ...settings, openai_model: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Anthropic API Key</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  className="input w-full"
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Anthropic Model</label>
                <input
                  type="text"
                  className="input w-full"
                  value={settings.anthropic_model || 'claude-3-sonnet'}
                  onChange={(e) => setSettings({ ...settings, anthropic_model: e.target.value })}
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button onClick={handleSave} className="btn btn-primary flex-1">
                Save & Apply
              </button>
              <button onClick={handleTestBinance} className="btn btn-secondary">
                Test Binance
              </button>
              <button onClick={handleTestTelegram} className="btn btn-secondary">
                Test Telegram
              </button>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-bold">Database Status</h2>
          </div>
          <div className="card-body space-y-3">
            <div className="text-xs text-slate-400 break-all">
              {dbStatus?.db_url}
            </div>
            <div className="space-y-2">
              {dbStatus?.counts && Object.entries(dbStatus.counts).map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm">
                  <span className="text-slate-300 capitalize">{k.replace('_', ' ')}</span>
                  <span className="text-white font-medium">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
