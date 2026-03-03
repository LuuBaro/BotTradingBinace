import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Globe, Plus, Trash2, Radio, MessageSquare, ExternalLink, Settings2, Bot, Database, Save, CheckCircle2, FlaskConical, Network, Shield, Brain, ShieldAlert } from 'lucide-react'
import { useAuthStore } from '../store'

interface SettingsResponse {
  settings: Record<string, any>
  db_status: {
    db_url: string
    counts: Record<string, number>
  }
}

// Predefined model names for each provider
const MODEL_OPTIONS: Record<string, string[]> = {
  openai: [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4.1',
    'gpt-4.1-mini',
    'gpt-4.1-nano',
    'gpt-4',
    'gpt-4-turbo',
    'gpt-3.5-turbo'
  ],
  anthropic: [
    'claude-3.5-sonnet',
    'claude-3.5-haiku',
    'claude-3-opus-20240229',
    'claude-3-sonnet-20240229',
    'claude-3-haiku-20240307'
  ],
  gemini: [
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-flash-latest',
    'gemini-pro-latest'
  ],
  groq: [
    'llama3-70b-8192',
    'llama3-8b-8192',
    'mixtral-8x7b-32768',
    'gemma-7b-it'
  ]
}

export const SettingsPage: React.FC = () => {
  const { user } = useAuthStore()
  const api = createApiClient(getApiBaseUrl(), localStorage.getItem('token') || '')
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState<Record<string, any>>({})
  const [dbStatus, setDbStatus] = useState<SettingsResponse['db_status'] | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [restartRequired, setRestartRequired] = useState<string[]>([])
  const [editFallbackSecrets, setEditFallbackSecrets] = useState(false)

  // Sensitive keys (Binance, OpenAI, etc.) are now managed per-user in Neural Portal

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

    // Check for hash and scroll to element
    if (window.location.hash === '#news-sources') {
      setTimeout(() => {
        const element = document.getElementById('news-sources');
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
          // Highlight effect
          element.style.outline = '2px solid #3b82f6';
          element.style.boxShadow = '0 0 40px rgba(59, 130, 246, 0.4)';
          setTimeout(() => {
            element.style.outline = '';
            element.style.boxShadow = '';
          }, 3000);
        }
      }, 500); // Wait for content load
    }
  }, [])

  const handleSave = async () => {
    try {
      setMessage(null)
      const payload: Record<string, any> = {
        ...settings,
        persist: 'both',
      }

      const res = await api.updateSettings(payload)
      setSettings(res.settings)
      setRestartRequired(res.restart_required || [])
      setMessage({ type: 'success', text: 'Global intelligence configuration updated successfully.' })
    } catch (err: any) {
      setMessage({ type: 'error', text: `Save failed: ${err.message || err}` })
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

  if (user?.role?.toLowerCase() !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <ShieldAlert size={64} className="text-rose-500 animate-pulse" />
        <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Truy cập bị từ chối</h2>
        <p className="text-slate-500">Chỉ quản trị viên mới có quyền truy cập vào cài đặt hệ thống.</p>
      </div>
    )
  }

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Globe className="text-blue-400" size={14} />
            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-blue-400">Core Engine Resource Management</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-white">Global Intel</h1>
          <p className="text-slate-400 font-medium">Quản trị hệ thống, luồng dữ liệu tin tức và hạ tầng quét dữ liệu chung.</p>
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
                <Database className="text-purple-400" size={20} />
                Execution Infrastructure
              </h2>
            </div>
            <div className="p-8 space-y-8">

              {/* Information Alert */}
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center gap-3">
                <Globe className="text-blue-400" size={20} />
                <p className="text-sm text-blue-300 font-medium">
                  <strong>Logic hệ thống:</strong> Trang này quản trị cấu hình <strong>global/fallback</strong> cho toàn hệ thống. Khóa API và AI <strong>cá nhân của admin</strong> (hoặc từng user) được quản lý tại <Link to="/portal" className="text-blue-400 underline font-bold italic">API Keys & AI Model</Link>.
                </p>
              </div>

              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm text-amber-300 font-semibold">Fallback secrets (global) chỉ dùng khi user không có key riêng.</p>
                  <p className="text-xs text-amber-200/80 mt-1">Mặc định bị khóa để tránh ghi đè nhầm cấu hình vận hành.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setEditFallbackSecrets((v) => !v)}
                  className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider border transition-all ${editFallbackSecrets
                    ? 'bg-amber-500/20 text-amber-200 border-amber-400/40'
                    : 'bg-white/5 text-slate-300 border-white/10 hover:bg-white/10'
                    }`}
                >
                  {editFallbackSecrets ? 'Đang mở sửa fallback' : 'Mở sửa fallback'}
                </button>
              </div>

              {/* Environment */}
              <div className="space-y-4">
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Global Targeting</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">System Execution Mode</label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.env || 'demo'}
                      onChange={(e) => setSettings({ ...settings, env: e.target.value })}
                    >
                      <option value="demo">Global Demo (Testnet Default)</option>
                      <option value="live">Global Live (Mainnet Authorized)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* BINANCE GLOBAL FALLBACK */}
              <div className="space-y-4 pt-4 border-t border-white/5">
                <h3 className="text-xs font-black text-yellow-500 uppercase tracking-widest flex items-center gap-2">
                  <Shield size={14} />
                  Binance Global Hub (Fallback mặc định)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-1">
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Global API Key</label>
                    <input
                      type="password"
                      disabled={!editFallbackSecrets}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-yellow-500/50"
                      value={settings.binance_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, binance_api_key: e.target.value })}
                      autoComplete="off"
                      placeholder={editFallbackSecrets ? 'Nhập fallback key nếu cần' : 'Đã khóa - bấm Mở sửa fallback để chỉnh'}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Global API Secret</label>
                    <input
                      type="password"
                      disabled={!editFallbackSecrets}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-yellow-500/50"
                      value={settings.binance_api_secret || ''}
                      onChange={(e) => setSettings({ ...settings, binance_api_secret: e.target.value })}
                      autoComplete="off"
                      placeholder={editFallbackSecrets ? 'Nhập fallback secret nếu cần' : 'Đã khóa - bấm Mở sửa fallback để chỉnh'}
                    />
                  </div>
                </div>
              </div>

              {/* AI GLOBAL FALLBACK */}
              <div className="space-y-4 pt-4 border-t border-white/5">
                <h3 className="text-xs font-black text-blue-500 uppercase tracking-widest flex items-center gap-2">
                  <Brain size={14} />
                  Neural Network Backbone (Fallback mặc định)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Provider</label>
                    <select
                      disabled={!editFallbackSecrets}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500/50"
                      value={settings.selected_llm || 'openai'}
                      onChange={(e) => setSettings({ ...settings, selected_llm: e.target.value })}
                    >
                      <option value="openai">OpenAI (GPT-4)</option>
                      <option value="anthropic">Anthropic (Claude)</option>
                      <option value="gemini">Google Gemini</option>
                      <option value="groq">Groq (Fast Llama)</option>
                      <option value="custom">Custom (Local/Ollama)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Neural Model</label>
                    {settings.selected_llm === 'custom' ? (
                      <input
                        type="text"
                        disabled={!editFallbackSecrets}
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500/50 font-mono"
                        value={settings.custom_model || ''}
                        onChange={(e) => setSettings({ ...settings, custom_model: e.target.value })}
                        placeholder="e.g. llama3:70b"
                      />
                    ) : (
                      <select
                        disabled={!editFallbackSecrets}
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500/50 font-mono"
                        value={
                          settings.selected_llm === 'openai' ? (settings.openai_model || 'gpt-4o-mini') :
                          settings.selected_llm === 'anthropic' ? (settings.anthropic_model || 'claude-3.5-sonnet') :
                          settings.selected_llm === 'gemini' ? (settings.gemini_model || 'gemini-2.0-flash') :
                          settings.selected_llm === 'groq' ? (settings.groq_model || 'llama3-70b-8192') :
                          ''
                        }
                        onChange={(e) => {
                          const key = settings.selected_llm === 'openai' ? 'openai_model' :
                            settings.selected_llm === 'anthropic' ? 'anthropic_model' :
                            settings.selected_llm === 'gemini' ? 'gemini_model' :
                            settings.selected_llm === 'groq' ? 'groq_model' :
                            'custom_model';
                          setSettings({ ...settings, [key]: e.target.value });
                        }}
                      >
                        {MODEL_OPTIONS[settings.selected_llm || 'openai']?.map((model) => (
                          <option key={model} value={model}>{model}</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div className="md:col-span-1">
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
                      {settings.selected_llm === 'openai' ? 'OpenAI API Key' :
                        settings.selected_llm === 'anthropic' ? 'Anthropic API Key' :
                        settings.selected_llm === 'gemini' ? 'Gemini API Key' :
                        settings.selected_llm === 'groq' ? 'Groq API Key' :
                        'Custom Endpoint'}
                    </label>
                    <input
                      type={settings.selected_llm === 'custom' ? 'text' : 'password'}
                      disabled={!editFallbackSecrets}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500/50"
                      value={
                        settings.selected_llm === 'openai' ? (settings.openai_api_key || '') :
                        settings.selected_llm === 'anthropic' ? (settings.anthropic_api_key || '') :
                        settings.selected_llm === 'gemini' ? (settings.gemini_api_key || '') :
                        settings.selected_llm === 'groq' ? (settings.groq_api_key || '') :
                        (settings.custom_endpoint || '')
                      }
                      onChange={(e) => {
                        const key = settings.selected_llm === 'openai' ? 'openai_api_key' :
                          settings.selected_llm === 'anthropic' ? 'anthropic_api_key' :
                          settings.selected_llm === 'gemini' ? 'gemini_api_key' :
                          settings.selected_llm === 'groq' ? 'groq_api_key' :
                          'custom_endpoint';
                        setSettings({ ...settings, [key]: e.target.value });
                      }}
                      placeholder={settings.selected_llm === 'custom' ? 'http://localhost:11434' : ''}
                      autoComplete="off"
                    />
                  </div>
                </div>
                <p className="text-[11px] text-slate-400">
                  Gợi ý vận hành: dùng <code className="text-slate-200">/portal</code> cho key riêng của admin. Chỉ cấu hình fallback ở đây khi cần default cho user chưa cấu hình.
                </p>
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
        <div className="lg:col-span-4 flex flex-col gap-8 h-full" id="news-sources">
          <div className="card glass-dark border-blue-500/10 bg-gradient-to-b from-slate-900 to-blue-950/20 overflow-hidden flex-1 flex flex-col transition-all duration-700">
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
