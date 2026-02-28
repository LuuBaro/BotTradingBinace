import React, { useEffect, useState } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Globe, Plus, Trash2, Radio, MessageSquare, ExternalLink, Settings2, KeyRound, Bot, Database, Save, CheckCircle2, FlaskConical, Network } from 'lucide-react'

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

  // News Sources State
  const [newsSources, setNewsSources] = useState<any[]>([])
  const [newSourceName, setNewSourceName] = useState('')
  const [newSourceUrl, setNewSourceUrl] = useState('')
  const [newSourceType, setNewSourceType] = useState('web')
  const [isAddingSource, setIsAddingSource] = useState(false)

  const loadSettings = async () => {
    try {
      setLoading(true)
      const res: SettingsResponse = await api.getSettings()
      setSettings(res.settings)
      setDbStatus(res.db_status)

      // Load News Sources
      const sources = await api.getNewsSources()
      setNewsSources(sources)
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
      setMessage({ type: 'success', text: 'Cấu hình đã được cập nhật thành công (Settings Saved)' })
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
        text: res.ok ? `Binance Connected OK (${res.base_url})` : `Binance failed: ${res.error || res.status_code}`,
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
        text: res.ok ? `Telegram OK (@${res.result?.username || 'bot'})` : `Telegram failed: ${res.error || 'unknown'}`,
      })
    } catch (err: any) {
      setMessage({ type: 'error', text: `Telegram test failed: ${err.message || err}` })
    }
  }

  const handleAddSource = async () => {
    if (!newSourceName || !newSourceUrl) return
    try {
      setIsAddingSource(true)
      await api.addNewsSource({
        name: newSourceName,
        url: newSourceUrl,
        source_type: newSourceType
      })
      setNewSourceName('')
      setNewSourceUrl('')
      const sources = await api.getNewsSources()
      setNewsSources(sources)
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to add source: ${err.message || err}` })
    } finally {
      setIsAddingSource(false)
    }
  }

  const handleDeleteSource = async (id: number) => {
    if (!confirm("Bạn có chắc chắn muốn xóa tin tức này khỏi danh sách quét của AI?")) return;
    try {
      await api.deleteNewsSource(id)
      const sources = await api.getNewsSources()
      setNewsSources(sources)
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to delete source: ${err.message || err}` })
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center animate-pulse">
        <div className="flex flex-col items-center gap-4">
          <Settings2 size={48} className="text-blue-500 animate-spin" />
          <span className="text-blue-400 font-black tracking-[0.3em]">INITIALIZING CONFIGURATION...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Settings2 className="text-blue-400" size={14} />
            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-blue-400">Core Engine Configuration</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-white">System Settings</h1>
          <p className="text-slate-400 font-medium">Global environment variables, API keys, and external data sources provisioning.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleSave} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center gap-2 transition-all shadow-lg shadow-blue-600/20">
            <Save size={16} />
            Save Globals
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-2xl border flex items-center gap-3 ${message.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
          <CheckCircle2 size={18} />
          <span className="font-medium text-sm">{message.text}</span>
        </div>
      )}

      {restartRequired.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center gap-3 text-amber-400">
          <FlaskConical size={18} />
          <span className="font-medium text-sm">Changes applied. Backend restart recommended for: {restartRequired.join(', ')}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* Core Config */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          <div className="card glass-dark border-white/5 overflow-hidden group">
            <div className="card-header border-b border-white/5 bg-white/[0.02]">
              <h2 className="text-xl font-black flex items-center gap-3">
                <KeyRound className="text-purple-400" size={20} />
                API Gateways & Secrets
              </h2>
            </div>
            <div className="p-8 space-y-8">

              {/* Environment */}
              <div className="space-y-4">
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Environment Targeting</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Execution Mode</label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.env || 'demo'}
                      onChange={(e) => setSettings({ ...settings, env: e.target.value })}
                    >
                      <option value="demo">Demo / Paper Trading</option>
                      <option value="live">Live / Real Money</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-3 mt-7 bg-white/5 px-4 rounded-xl border border-white/5">
                    <label className="flex items-center gap-3 cursor-pointer w-full py-3">
                      <input
                        type="checkbox"
                        className="accent-purple-500 w-4 h-4"
                        checked={!!settings.binance_testnet}
                        onChange={(e) => setSettings({ ...settings, binance_testnet: e.target.checked })}
                      />
                      <span className="text-sm font-bold text-slate-300">Route to Binance Testnet</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="h-[1px] bg-white/5 w-full"></div>

              {/* API Keys */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Binance Exchange Connection</h3>
                  <button onClick={handleTestBinance} className="text-[10px] font-black uppercase tracking-widest text-purple-400 hover:text-purple-300 bg-purple-500/10 px-3 py-1 rounded-full transition-colors">Test Connection</button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">API Key</label>
                    <input
                      type="password"
                      placeholder="••••••••••••••••••••••••"
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-700"
                      value={binanceKey}
                      onChange={(e) => setBinanceKey(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">API Secret</label>
                    <input
                      type="password"
                      placeholder="••••••••••••••••••••••••"
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-700"
                      value={binanceSecret}
                      onChange={(e) => setBinanceSecret(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="h-[1px] bg-white/5 w-full"></div>

              {/* LLM Models */}
              <div className="space-y-4">
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Neural LLM Engines</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Active Provider</label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.selected_llm || 'mock'}
                      onChange={(e) => setSettings({ ...settings, selected_llm: e.target.value })}
                    >
                      <option value="mock">Mock Engine (Testing)</option>
                      <option value="openai">OpenAI (GPT-4)</option>
                      <option value="anthropic">Anthropic (Claude)</option>
                      <option value="groq">Groq (Ultra-fast)</option>
                      <option value="local">Local Model (Ollama)</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-3 mt-7 bg-white/5 px-4 rounded-xl border border-white/5">
                    <label className="flex items-center gap-3 cursor-pointer w-full py-3">
                      <input
                        type="checkbox"
                        className="accent-purple-500 w-4 h-4"
                        checked={!!settings.use_local_llm}
                        onChange={(e) => setSettings({ ...settings, use_local_llm: e.target.checked })}
                      />
                      <span className="text-sm font-bold text-slate-300">Force Local Mode</span>
                    </label>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">OpenAI API Key</label>
                    <input
                      type="password"
                      placeholder="sk-..."
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-700"
                      value={openaiKey}
                      onChange={(e) => setOpenaiKey(e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Model (e.g. gpt-4)"
                      className="w-full mt-2 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.openai_model || 'gpt-4o'}
                      onChange={(e) => setSettings({ ...settings, openai_model: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Anthropic API Key</label>
                    <input
                      type="password"
                      placeholder="sk-ant-..."
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-700"
                      value={anthropicKey}
                      onChange={(e) => setAnthropicKey(e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Model (e.g. claude-3)"
                      className="w-full mt-2 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.anthropic_model || 'claude-3-5-sonnet'}
                      onChange={(e) => setSettings({ ...settings, anthropic_model: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="h-[1px] bg-white/5 w-full"></div>

              {/* Telegram Config */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Telegram Notification Bridge</h3>
                  <button onClick={handleTestTelegram} className="text-[10px] font-black uppercase tracking-widest text-sky-400 hover:text-sky-300 bg-sky-500/10 px-3 py-1 rounded-full transition-colors">Test Bot</button>
                </div>
                <div className="grid grid-cols-1 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Telegram Bot Token (BotFather)</label>
                    <input
                      type="password"
                      placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500/50 transition-colors placeholder:text-slate-700 text-center font-mono tracking-widest"
                      value={telegramToken}
                      onChange={(e) => setTelegramToken(e.target.value)}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Admin Chat IDs (Comma separated)</label>
                    <input
                      type="text"
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500/50 transition-colors"
                      value={settings.telegram_admin_ids || ''}
                      onChange={(e) => setSettings({ ...settings, telegram_admin_ids: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Trader Chat IDs (Comma separated)</label>
                    <input
                      type="text"
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500/50 transition-colors"
                      value={settings.telegram_trader_ids || ''}
                      onChange={(e) => setSettings({ ...settings, telegram_trader_ids: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="card glass-dark border-white/5 overflow-hidden group">
            <div className="card-header border-b border-white/5 bg-white/[0.02]">
              <h2 className="text-xl font-black flex items-center gap-3">
                <Database className="text-emerald-400" size={20} />
                Internal Database Engine
              </h2>
            </div>
            <div className="p-8 space-y-4">
              <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
                  <Network size={24} />
                </div>
                <div>
                  <span className="text-[10px] font-black text-emerald-500 uppercase tracking-[0.2em] block mb-1">Connection String</span>
                  <span className="text-xs font-mono text-slate-300 break-all">{dbStatus?.db_url || "sqlite+aiosqlite:///data/trading_bot.db"}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
                {dbStatus?.counts && Object.entries(dbStatus.counts).map(([tag, count]) => (
                  <div key={tag} className="bg-black/40 p-4 rounded-2xl border border-white/5 text-center">
                    <span className="text-2xl font-black font-mono text-white block">{count}</span>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{tag.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Intelligence Sources Side */}
        <div className="lg:col-span-4 flex flex-col gap-8 h-full">
          <div className="card glass-dark border-blue-500/10 bg-gradient-to-b from-slate-900 to-blue-950/20 overflow-hidden flex-1 flex flex-col">
            <div className="p-6 border-b border-white/5 bg-white/[0.02] relative z-10">
              <h2 className="text-xl font-black flex items-center gap-3 text-white">
                <Bot className="text-blue-400" size={20} />
                Data Ingestion Sources
              </h2>
              <p className="text-xs font-medium text-slate-400 mt-2">URLs and streams the AI scans for market sentiment correlation.</p>
            </div>

            <div className="p-6 flex-1 flex flex-col gap-6 relative z-10 overflow-y-auto">
              {/* Add Section */}
              <div className="p-5 bg-black/40 rounded-2xl border border-blue-500/20 shadow-inner space-y-4">
                <h3 className="text-[10px] font-black text-blue-400 uppercase tracking-widest flex items-center gap-2">
                  <Plus size={12} />
                  Register New Feed
                </h3>

                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Name (e.g. Coin369 Channel)"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500/50"
                    value={newSourceName}
                    onChange={(e) => setNewSourceName(e.target.value)}
                  />

                  <input
                    type="text"
                    placeholder="URL (e.g. https://t.me/...)"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500/50"
                    value={newSourceUrl}
                    onChange={(e) => setNewSourceUrl(e.target.value)}
                  />

                  <div className="grid grid-cols-3 gap-2">
                    {['web', 'rss', 'telegram'].map(type => (
                      <button
                        key={type}
                        onClick={() => setNewSourceType(type)}
                        className={`py-2 text-[10px] font-black uppercase rounded-lg border transition-all ${newSourceType === type
                          ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-500/20'
                          : 'bg-white/5 border-white/5 text-slate-500 hover:bg-white/10'
                          }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={handleAddSource}
                    disabled={isAddingSource || !newSourceName || !newSourceUrl}
                    className="w-full py-3 mt-1 bg-white/10 hover:bg-blue-600 border border-white/5 hover:border-blue-500 transition-all rounded-xl text-xs font-black uppercase tracking-widest text-white disabled:opacity-50"
                  >
                    Inject Source
                  </button>
                </div>
              </div>

              {/* List Section */}
              <div className="space-y-3">
                <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Active Neural Streams</h3>
                <div className="space-y-2">
                  {newsSources.length === 0 ? (
                    <div className="p-6 text-center border border-dashed border-white/10 rounded-2xl">
                      <p className="text-slate-500 text-xs italic">No ingestion pipes connected.</p>
                    </div>
                  ) : newsSources.map((source: any) => (
                    <div key={source.id} className="flex flex-col p-3 bg-white/[0.02] border border-white/5 rounded-2xl group hover:border-white/20 transition-all">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${source.source_type === 'telegram' ? 'bg-sky-500/10 text-sky-400' :
                            source.source_type === 'rss' ? 'bg-orange-500/10 text-orange-400' :
                              'bg-indigo-500/10 text-indigo-400'
                            }`}>
                            {source.source_type === 'telegram' ? <MessageSquare size={14} /> :
                              source.source_type === 'rss' ? <Radio size={14} /> :
                                <Globe size={14} />}
                          </div>
                          <div>
                            <h4 className="text-xs font-bold text-white">{source.name}</h4>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${source.is_active ? 'bg-emerald-500 animate-glow' : 'bg-rose-500'}`}></span>
                              <span className="text-[9px] font-black uppercase text-slate-500">{source.source_type}</span>
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteSource(source.id)}
                          className="text-slate-600 hover:text-rose-400 transition-colors p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      <a href={source.url} target="_blank" rel="noreferrer" className="text-[9px] text-slate-500 hover:text-blue-400 flex items-center gap-1 mt-3 transition-colors bg-black/20 p-2 rounded-lg truncate w-full group/link">
                        <ExternalLink size={10} className="group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
                        <span className="truncate">{source.url}</span>
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
