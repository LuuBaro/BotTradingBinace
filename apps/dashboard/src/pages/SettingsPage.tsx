import React, { useEffect, useState } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Globe, Plus, Trash2, Radio, MessageSquare, ExternalLink, Settings2, KeyRound, Bot, Database, Save, CheckCircle2, FlaskConical, Network, Zap, ArrowRight, Sparkles, Shield, Copy, Check } from 'lucide-react'

interface SettingsResponse {
  settings: Record<string, any>
  db_status: {
    db_url: string
    counts: Record<string, number>
  }
}

// Model lists for each provider
const PROVIDER_MODELS = {
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o (Recommended, fast)' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Cheaper, faster)' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-4', label: 'GPT-4 (Legacy)' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (Fast, cheap)' },
  ],
  anthropic: [
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Recommended)' },
    { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku (Fast, cheap)' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (Most powerful)' },
    { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
  ],
  groq: [
    { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B (Recommended, powerful)' },
    { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B (Fast, cheap)' },
    { value: 'llama-3.1-70b-versatile', label: 'Llama 3.1 70B' },
    { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
    { value: 'gemma2-9b-it', label: 'Gemma 2 9B' },
  ],
  gemini: [
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro (Recommended)' },
    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (Fast, cheap)' },
    { value: 'gemini-1.0-pro', label: 'Gemini 1.0 Pro' },
  ],
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
  const [groqKey, setGroqKey] = useState('')
  const [geminiKey, setGeminiKey] = useState('')
  const [customProviderName, setCustomProviderName] = useState('')
  const [customProviderKey, setCustomProviderKey] = useState('')
  const [customProviderUrl, setCustomProviderUrl] = useState('')
  const [customProviderModel, setCustomProviderModel] = useState('')
  const [workerAiMode, setWorkerAiMode] = useState<string>('two_tier_hybrid')
  const [workerAiPromptLevel, setWorkerAiPromptLevel] = useState<string>('standard')
  
  // Password Management State
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  
  // 2FA Management State
  const [twoFAEnabled, setTwoFAEnabled] = useState(false)
  const [showTwoFASetup, setShowTwoFASetup] = useState(false)
  const [twoFAPassword, setTwoFAPassword] = useState('')
  const [twoFASecret, setTwoFASecret] = useState('')
  const [twoFAQRCode, setTwoFAQRCode] = useState('')
  const [twoFAVerificationCode, setTwoFAVerificationCode] = useState('')
  const [twoFABackupCodes, setTwoFABackupCodes] = useState<string[]>([])
  const [twoFAMessage, setTwoFAMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
  
  // Confirm Dialog State
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

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
      setWorkerAiMode(res.settings.worker_ai_mode || 'two_tier_hybrid')
      setWorkerAiPromptLevel(res.settings.worker_ai_prompt_level || 'standard')

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
      // Only send non-secret settings + new keys (don't spread old masked keys)
      const payload: Record<string, any> = {
        env: settings.env,
        api_host: settings.api_host,
        api_port: settings.api_port,
        selected_llm: settings.selected_llm,
        use_local_llm: settings.use_local_llm,
        openai_model: settings.openai_model,
        anthropic_model: settings.anthropic_model,
        worker_ai_mode: workerAiMode,
        worker_ai_prompt_level: workerAiPromptLevel,
        custom_provider_name: customProviderName || settings.custom_provider_name,
        custom_provider_url: customProviderUrl || settings.custom_provider_url,
        custom_provider_model: customProviderModel || settings.custom_provider_model,
        persist: 'both',
      }

      // Only include keys if user provided new values
      if (binanceKey) payload.binance_api_key = binanceKey
      if (binanceSecret) payload.binance_api_secret = binanceSecret
      if (telegramToken) payload.telegram_bot_token = telegramToken
      if (openaiKey) payload.openai_api_key = openaiKey
      if (anthropicKey) payload.anthropic_api_key = anthropicKey
      if (groqKey) payload.groq_api_key = groqKey
      if (geminiKey) payload.gemini_api_key = geminiKey
      if (customProviderKey) payload.custom_provider_key = customProviderKey

      const res = await api.updateSettings(payload)
      setSettings(res.settings)
      setRestartRequired(res.restart_required || [])
      setMessage({ type: 'success', text: 'Cấu hình đã được cập nhật thành công (Settings Saved)' })
      // Clear input fields after save
      setBinanceKey('')
      setBinanceSecret('')
      setTelegramToken('')
      setOpenaiKey('')
      setAnthropicKey('')
      setGroqKey('')
      setGeminiKey('')
      setCustomProviderKey('')
      setCustomProviderName('')
      setCustomProviderUrl('')
      setCustomProviderModel('')
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

  const handleSetupTwoFA = async (e: React.FormEvent) => {
    e.preventDefault()
    setTwoFAMessage(null)
    
    if (!twoFAPassword.trim()) {
      setTwoFAMessage({ type: 'error', text: 'Password is required to setup 2FA' })
      return
    }

    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      
      const response = await api.axiosInstance.post('auth/setup-totp', {
        username: user.username,
        password: twoFAPassword,
      })

      setTwoFASecret(response.data.secret)
      setTwoFAQRCode(response.data.qr_code)
      setTwoFAMessage({ type: 'success', text: 'QR code generated. Scan with Google Authenticator' })
    } catch (err: any) {
      setTwoFAMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to setup 2FA' })
    }
  }

  const handleVerifyTwoFA = async (e: React.FormEvent) => {
    e.preventDefault()
    setTwoFAMessage(null)

    if (!twoFAVerificationCode.trim() || twoFAVerificationCode.length !== 6) {
      setTwoFAMessage({ type: 'error', text: 'Please enter a valid 6-digit code' })
      return
    }

    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      
      const response = await api.axiosInstance.post('auth/verify-totp-setup', {
        username: user.username,
        secret: twoFASecret,
        code: twoFAVerificationCode,
      })

      setTwoFABackupCodes(response.data.backup_codes || [])
      setTwoFAEnabled(true)
      setTwoFAMessage({ type: 'success', text: '2FA enabled successfully!' })
    } catch (err: any) {
      setTwoFAMessage({ type: 'error', text: err.response?.data?.detail || 'Invalid verification code' })
    }
  }

  const copyBackupCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordMessage(null)

    // Validation
    if (!oldPassword.trim()) {
      setPasswordMessage({ type: 'error', text: 'Current password is required' })
      return
    }
    if (!newPassword.trim()) {
      setPasswordMessage({ type: 'error', text: 'New password is required' })
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: 'error', text: 'Passwords do not match' })
      return
    }
    if (newPassword.length < 4) {
      setPasswordMessage({ type: 'error', text: 'New password must be at least 4 characters' })
      return
    }

    try {
      await api.axiosInstance.post('auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
      setPasswordMessage({ type: 'success', text: 'Password changed successfully!' })
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPasswordMessage(null), 3000)
    } catch (err: any) {
      setPasswordMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to change password'
      })
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
      setMessage({ type: 'success', text: `✓ Intelligence source "${newSourceName}" added successfully!` })
      // Auto-clear success message after 3 seconds
      setTimeout(() => setMessage(null), 3000)
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to add source: ${err.message || err}` })
    } finally {
      setIsAddingSource(false)
    }
  }

  const handleDeleteSource = async (id: number) => {
    setDeleteConfirmId(id)
    setShowDeleteConfirm(true)
  }

  const confirmDeleteSource = async () => {
    if (!deleteConfirmId) return
    try {
      await api.deleteNewsSource(deleteConfirmId)
      const sources = await api.getNewsSources()
      setNewsSources(sources)
      setShowDeleteConfirm(false)
      setDeleteConfirmId(null)
      setMessage({ type: 'success', text: '✓ Intelligence source removed successfully!' })
      // Auto-clear success message after 3 seconds
      setTimeout(() => setMessage(null), 3000)
    } catch (err: any) {
      setMessage({ type: 'error', text: `Failed to delete source: ${err.message || err}` })
      setShowDeleteConfirm(false)
      setDeleteConfirmId(null)
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
      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
          <div className="relative max-w-md w-full animate-fadeIn">
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl p-6 space-y-4">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-rose-500/10 border border-rose-500/20">
                    <Trash2 className="h-6 w-6 text-rose-400" />
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-black text-white">Remove Intelligence Source?</h3>
                  <p className="text-sm text-slate-400 mt-2">
                    This will delete the data ingestion feed from AI analysis. The AI will no longer scan this source for market sentiment.
                  </p>
                </div>
              </div>
              
              <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4">
                <p className="text-xs font-bold text-rose-300 uppercase tracking-wider">⚠️ This action cannot be undone</p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false)
                    setDeleteConfirmId(null)
                  }}
                  className="flex-1 px-4 py-3 bg-slate-700/50 hover:bg-slate-600 border border-slate-600 rounded-xl font-black uppercase tracking-wider text-sm text-white transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeleteSource}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 border border-rose-400/20 shadow-lg shadow-rose-600/20 hover:shadow-rose-500/40 rounded-xl font-black uppercase tracking-wider text-sm text-white transition-all flex items-center justify-center gap-2"
                >
                  <Trash2 size={16} />
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
        <div className={`p-4 rounded-2xl border flex items-center justify-between gap-4 animate-in fade-in slide-in-from-top-4 duration-300 ${message.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
          <div className="flex items-center gap-3">
            <CheckCircle2 size={18} className="flex-shrink-0" />
            <span className="font-medium text-sm">{message.text}</span>
          </div>
          <button
            onClick={() => setMessage(null)}
            className="flex-shrink-0 text-current opacity-60 hover:opacity-100 transition-opacity"
            aria-label="Close message"
          >
            <span className="text-lg">×</span>
          </button>
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
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      API Key
                      {settings.binance_api_key && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.binance_api_key || "Enter new Binance API key..."}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                      value={binanceKey}
                      onChange={(e) => setBinanceKey(e.target.value)}
                    />
                    {settings.binance_api_key && !binanceKey && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.binance_api_key}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      API Secret
                      {settings.binance_api_secret && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.binance_api_secret || "Enter new Binance API secret..."}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                      value={binanceSecret}
                      onChange={(e) => setBinanceSecret(e.target.value)}
                    />
                    {settings.binance_api_secret && !binanceSecret && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.binance_api_secret}</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="h-[1px] bg-white/5 w-full"></div>

              {/* LLM Models */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Neural LLM Engines</h3>
                  <div className="text-[9px] text-slate-500 bg-white/5 px-3 py-1 rounded-full border border-white/5">
                    💡 Multiple providers for redundancy & cost optimization
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Active Provider</label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.selected_llm || 'mock'}
                      onChange={(e) => setSettings({ ...settings, selected_llm: e.target.value })}
                    >
                      <option value="mock">Mock Engine (Testing)</option>
                      <option value="openai">OpenAI GPT-4 (Powerful, expensive)</option>
                      <option value="anthropic">Anthropic Claude (Analytical, balanced)</option>
                      <option value="groq">Groq (Ultra-fast, free tier available)</option>
                      <option value="gemini">Google Gemini (Balanced, good value)</option>
                      <option value="local">Local Model (Ollama/LM Studio)</option>
                      <option value="custom">Custom Provider (Your own API)</option>
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

                {/* AI Architecture Mode */}
                <div className="mt-6 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">AI Architecture Strategy</label>
                    <span className="text-[9px] text-slate-500 bg-purple-500/10 px-3 py-1 rounded-full border border-purple-500/20">
                      {workerAiMode === 'two_tier_hybrid' ? '🌐 Cloud Mode Active' : '🖥️ Local Mode Active'}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div
                      onClick={() => setWorkerAiMode('two_tier_hybrid')}
                      className={`p-4 rounded-xl cursor-pointer transition-all border-2 ${
                        workerAiMode === 'two_tier_hybrid'
                          ? 'bg-blue-500/20 border-blue-500/50'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-1 ${
                          workerAiMode === 'two_tier_hybrid' ? 'border-blue-500 bg-blue-500/30' : 'border-white/20'
                        }`}>
                          {workerAiMode === 'two_tier_hybrid' && <div className="w-2 h-2 bg-blue-400 rounded-full"></div>}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white">🌐 2 Cloud LLMs</p>
                          <p className="text-[11px] text-slate-400 mt-1">Scout (GPT-3.5) + Verifier (GPT-4)</p>
                          <p className="text-[10px] text-slate-500 mt-2">
                            <strong>Pros:</strong> Stable, reliable, works everywhere<br/>
                            <strong>Cons:</strong> ≈$0.30/decision, depends on internet
                          </p>
                        </div>
                      </div>
                    </div>
                    <div
                      onClick={() => setWorkerAiMode('two_tier_same')}
                      className={`p-4 rounded-xl cursor-pointer transition-all border-2 ${
                        workerAiMode === 'two_tier_same'
                          ? 'bg-green-500/20 border-green-500/50'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-1 ${
                          workerAiMode === 'two_tier_same' ? 'border-green-500 bg-green-500/30' : 'border-white/20'
                        }`}>
                          {workerAiMode === 'two_tier_same' && <div className="w-2 h-2 bg-green-400 rounded-full"></div>}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white">🖥️ 1 Local AI</p>
                          <p className="text-[11px] text-slate-400 mt-1">Single Ollama/LM Studio instance</p>
                          <p className="text-[10px] text-slate-500 mt-2">
                            <strong>Pros:</strong> Zero cost, instant, offline<br/>
                            <strong>Cons:</strong> Quality depends on hardware
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Prompt Level Selection */}
                <div className="mt-6 space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Prompt Optimization Level</label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => setWorkerAiPromptLevel('lightweight')}
                      className={`py-2 px-3 rounded-lg text-[11px] font-bold transition-all ${
                        workerAiPromptLevel === 'lightweight'
                          ? 'bg-amber-500/30 border border-amber-500/50 text-white'
                          : 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10'
                      }`}
                    >
                      ⚡ Lightweight
                    </button>
                    <button
                      onClick={() => setWorkerAiPromptLevel('standard')}
                      className={`py-2 px-3 rounded-lg text-[11px] font-bold transition-all ${
                        workerAiPromptLevel === 'standard'
                          ? 'bg-purple-500/30 border border-purple-500/50 text-white'
                          : 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10'
                      }`}
                    >
                      ⚙️ Standard
                    </button>
                    <button
                      onClick={() => setWorkerAiPromptLevel('heavyweight')}
                      className={`py-2 px-3 rounded-lg text-[11px] font-bold transition-all ${
                        workerAiPromptLevel === 'heavyweight'
                          ? 'bg-rose-500/30 border border-rose-500/50 text-white'
                          : 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10'
                      }`}
                    >
                      🧠 Heavyweight
                    </button>
                  </div>
                  <p className="text-[9px] text-slate-500 mt-2">
                    Lightweight: Fast, basic analysis | Standard: Balanced (default) | Heavyweight: Detailed, slower
                  </p>
                </div>

                {/* Provider Explanation */}
                <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 text-xs space-y-2 mt-6">
                  <p className="text-blue-300 font-bold">🤔 Understanding AI Strategies</p>
                  <div className="text-slate-400 space-y-2">
                    <p><strong className="text-white">☁️ 2 Cloud LLMs (two_tier_hybrid):</strong> Scout checks opportunities, Verifier validates decisions. Stable, reliable but requires API keys & internet.</p>
                    <p><strong className="text-white">💻 1 Local AI (two_tier_same):</strong> Single Ollama/LM Studio instance does all analysis. Zero cost but requires hardware & offline capable.</p>
                    <p><strong className="text-amber-400">💡 Tip:</strong> Switch strategies easily - just select mode and restart worker!</p>
                  </div>
                </div>

                {/* OpenAI Config */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      OpenAI API Key
                      {settings.openai_api_key && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.openai_api_key || "sk-..."}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                      value={openaiKey}
                      onChange={(e) => setOpenaiKey(e.target.value)}
                    />
                    {settings.openai_api_key && !openaiKey && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.openai_api_key}</p>
                    )}
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-3 mb-2">
                      Model Selection
                    </label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.openai_model || 'gpt-4o'}
                      onChange={(e) => setSettings({ ...settings, openai_model: e.target.value })}
                    >
                      {PROVIDER_MODELS.openai.map(model => (
                        <option key={model.value} value={model.value}>{model.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      Anthropic API Key
                      {settings.anthropic_api_key && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.anthropic_api_key || "sk-ant-..."}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                      value={anthropicKey}
                      onChange={(e) => setAnthropicKey(e.target.value)}
                    />
                    {settings.anthropic_api_key && !anthropicKey && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.anthropic_api_key}</p>
                    )}
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-3 mb-2">
                      Model Selection
                    </label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.anthropic_model || 'claude-3-5-sonnet-20241022'}
                      onChange={(e) => setSettings({ ...settings, anthropic_model: e.target.value })}
                    >
                      {PROVIDER_MODELS.anthropic.map(model => (
                        <option key={model.value} value={model.value}>{model.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Groq & Gemini Config */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      Groq API Key
                      {settings.groq_api_key && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.groq_api_key || "gsk-..."}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                      value={groqKey}
                      onChange={(e) => setGroqKey(e.target.value)}
                    />
                    {settings.groq_api_key && !groqKey && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.groq_api_key}</p>
                    )}
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-3 mb-2">
                      Model Selection
                    </label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.groq_model || 'llama-3.3-70b-versatile'}
                      onChange={(e) => setSettings({ ...settings, groq_model: e.target.value })}
                    >
                      {PROVIDER_MODELS.groq.map(model => (
                        <option key={model.value} value={model.value}>{model.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      Gemini API Key
                      {settings.gemini_api_key && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.gemini_api_key || "AIza..."}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                      value={geminiKey}
                      onChange={(e) => setGeminiKey(e.target.value)}
                    />
                    {settings.gemini_api_key && !geminiKey && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.gemini_api_key}</p>
                    )}
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-3 mb-2">
                      Model Selection
                    </label>
                    <select
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                      value={settings.gemini_model || 'gemini-1.5-pro'}
                      onChange={(e) => setSettings({ ...settings, gemini_model: e.target.value })}
                    >
                      {PROVIDER_MODELS.gemini.map(model => (
                        <option key={model.value} value={model.value}>{model.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Custom Provider Section */}
                {settings.selected_llm === 'custom' && (
                  <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-6 space-y-4 mt-4">
                    <h4 className="text-sm font-black text-purple-300 uppercase tracking-wider flex items-center gap-2">
                      <KeyRound size={14} />
                      Custom LLM Provider Configuration
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                          Provider Name
                        </label>
                        <input
                          type="text"
                          placeholder="e.g., Mistral, Llama, etc."
                          className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                          value={customProviderName || settings.custom_provider_name || ''}
                          onChange={(e) => setCustomProviderName(e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                          Model Name
                        </label>
                        <input
                          type="text"
                          placeholder="e.g., mistral-large-latest"
                          className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                          value={customProviderModel || settings.custom_provider_model || ''}
                          onChange={(e) => setCustomProviderModel(e.target.value)}
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                        API Endpoint URL
                      </label>
                      <input
                        type="text"
                        placeholder="https://api.your-provider.com/v1/chat/completions"
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-purple-500/50 transition-colors font-mono text-xs"
                        value={customProviderUrl || settings.custom_provider_url || ''}
                        onChange={(e) => setCustomProviderUrl(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                        API Key
                        {settings.custom_provider_key && (
                          <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                        )}
                      </label>
                      <input
                        type="password"
                        placeholder={settings.custom_provider_key || "Enter your provider's API key..."}
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600"
                        value={customProviderKey}
                        onChange={(e) => setCustomProviderKey(e.target.value)}
                      />
                      {settings.custom_provider_key && !customProviderKey && (
                        <p className="text-[9px] text-slate-500 mt-1 font-mono">{settings.custom_provider_key}</p>
                      )}
                    </div>
                    <p className="text-[9px] text-slate-500 italic">
                      ⚠️ Custom provider should support OpenAI-compatible API format
                    </p>
                  </div>
                )}
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
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                      Telegram Bot Token (BotFather)
                      {settings.telegram_bot_token && (
                        <span className="ml-2 text-emerald-400 text-[9px]">✓ Configured</span>
                      )}
                    </label>
                    <input
                      type="password"
                      placeholder={settings.telegram_bot_token || "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500/50 transition-colors placeholder:text-slate-600 text-center font-mono tracking-widest"
                      value={telegramToken}
                      onChange={(e) => setTelegramToken(e.target.value)}
                    />
                    {settings.telegram_bot_token && !telegramToken && (
                      <p className="text-[9px] text-slate-500 mt-1 font-mono text-center">{settings.telegram_bot_token}</p>
                    )}
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
          
          {/* Security - Change Password */}
          <div className="card glass-dark border-amber-500/10 bg-gradient-to-b from-slate-900 via-amber-950/10 to-slate-900/50 overflow-hidden shadow-xl">
            <div className="p-6 border-b border-amber-500/20 bg-gradient-to-r from-amber-500/5 to-transparent">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-500/10 rounded-lg">
                  <KeyRound className="text-amber-400" size={20} />
                </div>
                <div>
                  <h2 className="text-lg font-black text-white">Account Security</h2>
                  <p className="text-xs font-medium text-amber-300 mt-1">Change your password</p>
                </div>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {passwordMessage && (
                <div className={`p-4 rounded-xl border flex items-center justify-between ${
                  passwordMessage.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                }`}>
                  <span className="text-sm font-medium">{passwordMessage.text}</span>
                </div>
              )}

              <form onSubmit={handleChangePassword} className="space-y-3">
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    placeholder="Enter current password"
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    placeholder="Enter new password (min 4 characters)"
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    placeholder="Confirm new password"
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>

                <button
                  type="submit"
                  disabled={!oldPassword.trim() || !newPassword.trim()}
                  className="btn btn-primary w-full mt-2 disabled:opacity-50"
                >
                  Update Password
                </button>
              </form>

              {/* 2FA Setup Section */}
              <div className="mt-6 pt-6 border-t border-slate-700">
                <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                  <Shield size={16} className="text-blue-400" />
                  Two-Factor Authentication (2FA)
                </h3>

                {twoFAMessage && (
                  <div className={`p-3 rounded-lg border mb-4 text-sm ${
                    twoFAMessage.type === 'success'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : 'bg-red-500/10 border-red-500/30 text-red-400'
                  }`}>
                    {twoFAMessage.text}
                  </div>
                )}

                {!showTwoFASetup && !twoFAEnabled && (
                  <button
                    onClick={() => setShowTwoFASetup(true)}
                    className="btn btn-secondary w-full text-sm"
                  >
                    Enable 2FA with Google Authenticator
                  </button>
                )}

                {showTwoFASetup && !twoFAQRCode && (
                  <form onSubmit={handleSetupTwoFA} className="space-y-3">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                        Confirm Password
                      </label>
                      <input
                        type="password"
                        placeholder="Enter your password to enable 2FA"
                        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-colors"
                        value={twoFAPassword}
                        onChange={(e) => setTwoFAPassword(e.target.value)}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={!twoFAPassword.trim()}
                      className="btn btn-secondary w-full text-sm disabled:opacity-50"
                    >
                      Generate QR Code
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowTwoFASetup(false)
                        setTwoFAPassword('')
                      }}
                      className="btn btn-ghost w-full text-sm"
                    >
                      Cancel
                    </button>
                  </form>
                )}

                {twoFAQRCode && !twoFAEnabled && (
                  <div className="space-y-4">
                    <div className="bg-black/60 p-4 rounded-lg text-center">
                      <img src={twoFAQRCode} alt="2FA QR Code" className="w-48 h-48 mx-auto" />
                      <p className="text-xs text-slate-400 mt-3">Scan this with Google Authenticator</p>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                        Enter 6-Digit Code
                      </label>
                      <input
                        type="text"
                        placeholder="000000"
                        maxLength={6}
                        className="w-full text-center text-2xl font-bold tracking-widest bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500/50 transition-colors"
                        value={twoFAVerificationCode}
                        onChange={(e) => setTwoFAVerificationCode(e.target.value.replace(/\\D/g, '').slice(0, 6))}
                      />
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={handleVerifyTwoFA}
                        disabled={twoFAVerificationCode.length !== 6}
                        className="btn btn-primary flex-1 text-sm disabled:opacity-50"
                      >
                        Verify & Enable 2FA
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowTwoFASetup(false)
                          setTwoFAPassword('')
                          setTwoFASecret('')
                          setTwoFAQRCode('')
                          setTwoFAVerificationCode('')
                        }}
                        className="btn btn-ghost flex-1 text-sm"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {twoFAEnabled && twoFABackupCodes.length > 0 && (
                  <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 space-y-3">
                    <p className="text-sm text-blue-300 font-semibold">✅ 2FA is now enabled!</p>
                    <p className="text-xs text-slate-300">Save these backup codes in a safe place. You can use them to access your account if you lose access to your authenticator.</p>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {twoFABackupCodes.map((code, idx) => (
                        <div key={idx} className="flex items-center justify-between px-3 py-2 bg-black/40 rounded text-xs font-mono">
                          <span className="text-slate-400">{code}</span>
                          <button
                            onClick={() => copyBackupCode(code)}
                            className="text-slate-500 hover:text-blue-400 transition"
                          >
                            {copiedCode === code ? <Check size={14} /> : <Copy size={14} />}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Intelligence Sources Card */}
          <div className="card glass-dark border-white/5 overflow-hidden group flex flex-col h-full">
            <div className="p-6 border-b border-blue-500/20 bg-gradient-to-r from-blue-500/5 to-transparent relative z-10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg">
                    <Bot className="text-blue-400" size={24} />
                  </div>
                  <div>
                    <h2 className="text-lg font-black text-white leading-tight">Data Ingestion Sources</h2>
                    <p className="text-xs font-medium text-blue-300 mt-1">Market intelligence feeds for AI analysis</p>
                  </div>
                </div>
                <Sparkles className="text-blue-400 animate-pulse" size={20} />
              </div>
            </div>

            <div className="p-6 flex-1 flex flex-col gap-6 relative z-10 overflow-y-auto">
              {/* Add Section - Enhanced */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 rounded-2xl blur-xl"></div>
                <div className="relative p-6 bg-gradient-to-br from-slate-800/50 to-blue-950/30 rounded-2xl border border-blue-500/30 space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                      <Plus size={14} className="text-blue-400" />
                    </div>
                    <h3 className="text-sm font-black text-blue-300 uppercase tracking-widest">Add Intelligence Source</h3>
                  </div>

                  <div className="space-y-3">
                    <div className="relative">
                      <input
                        type="text"
                        placeholder="Feed Name (e.g. CoinTelegraph, Binance News)"
                        className="w-full bg-slate-900/50 border border-blue-500/20 hover:border-blue-500/40 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-transparent transition-all placeholder:text-slate-500"
                        value={newSourceName}
                        onChange={(e) => setNewSourceName(e.target.value)}
                      />
                    </div>

                    <div className="relative">
                      <input
                        type="text"
                        placeholder="URL (RSS feed, Telegram channel, website)"
                        className="w-full bg-slate-900/50 border border-blue-500/20 hover:border-blue-500/40 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-transparent transition-all placeholder:text-slate-500 font-mono"
                        value={newSourceUrl}
                        onChange={(e) => setNewSourceUrl(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Source Type</label>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { type: 'web', icon: Globe, label: 'Web', color: 'indigo' },
                          { type: 'rss', icon: Radio, label: 'RSS', color: 'orange' },
                          { type: 'telegram', icon: MessageSquare, label: 'Telegram', color: 'sky' },
                        ].map(({ type, icon: Icon, label, color }) => (
                          <button
                            key={type}
                            onClick={() => setNewSourceType(type)}
                            className={`group relative py-3 px-2 rounded-xl border font-black text-[10px] uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2 ${
                              newSourceType === type
                                ? `bg-${color}-600/30 border-${color}-500 text-${color}-300 shadow-lg shadow-${color}-500/20`
                                : `bg-slate-800/30 border-slate-700/50 text-slate-400 hover:border-${color}-500/50 hover:bg-${color}-500/10`
                            }`}
                          >
                            <Icon size={14} />
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={handleAddSource}
                      disabled={isAddingSource || !newSourceName || !newSourceUrl}
                      className="w-full group relative py-3 mt-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:from-slate-700 disabled:to-slate-600 disabled:opacity-50 border border-blue-400/20 disabled:border-slate-600 rounded-xl text-sm font-black uppercase tracking-widest text-white transition-all duration-300 shadow-lg shadow-blue-600/20 hover:shadow-blue-500/40 disabled:shadow-none flex items-center justify-center gap-2"
                    >
                      <Zap size={16} className="group-hover:animate-pulse" />
                      {isAddingSource ? 'Adding...' : 'Inject Feed'}
                      <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                    </button>
                  </div>
                </div>
              </div>

              {/* List Section - Enhanced */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-black text-slate-300 uppercase tracking-widest">Active Intelligence Streams</h3>
                  <span className="text-[10px] font-bold bg-blue-500/20 text-blue-300 px-3 py-1 rounded-full border border-blue-500/30">
                    {newsSources.length} Connected
                  </span>
                </div>
                <div className="space-y-2">
                  {newsSources.length === 0 ? (
                    <div className="relative p-8 text-center border-2 border-dashed border-slate-700/50 rounded-2xl hover:border-blue-500/30 transition-all duration-300 group">
                      <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                      <div className="relative space-y-3">
                        <Bot size={32} className="mx-auto text-slate-600 group-hover:text-blue-400 transition-colors" />
                        <p className="text-slate-500 text-sm font-semibold">No feeds connected yet</p>
                        <p className="text-slate-600 text-xs">Add RSS, Telegram, or web sources above to start ingesting market intelligence</p>
                      </div>
                    </div>
                  ) : (
                    newsSources.map((source: any, idx: number) => (
                      <div key={source.id} className="group relative">
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 rounded-xl blur-lg transition-opacity duration-300"></div>
                        <div className="relative flex items-center gap-4 p-4 bg-slate-800/30 hover:bg-slate-800/50 border border-slate-700/50 hover:border-blue-500/30 rounded-xl transition-all duration-300">
                          <div className={`flex-shrink-0 p-3 rounded-lg border ${
                            source.source_type === 'telegram' 
                              ? 'bg-sky-500/10 border-sky-500/30 text-sky-400' :
                            source.source_type === 'rss' 
                              ? 'bg-orange-500/10 border-orange-500/30 text-orange-400' :
                              'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                          }`}>
                            {source.source_type === 'telegram' ? <MessageSquare size={18} /> :
                              source.source_type === 'rss' ? <Radio size={18} /> :
                                <Globe size={18} />}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="text-sm font-bold text-white">{source.name}</h4>
                              <span className={`inline-flex items-center gap-1 px-2 py-1 text-[9px] font-black uppercase rounded-full border ${
                                source.is_active 
                                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
                                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                              }`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${source.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
                                {source.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </div>
                            <a 
                              href={source.url} 
                              target="_blank" 
                              rel="noreferrer" 
                              className="text-[11px] text-slate-400 hover:text-blue-400 flex items-center gap-1 truncate transition-colors group/link"
                            >
                              <ExternalLink size={10} className="flex-shrink-0" />
                              <span className="truncate">{source.url}</span>
                            </a>
                          </div>

                          <button
                            onClick={() => handleDeleteSource(source.id)}
                            className="flex-shrink-0 p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all duration-200"
                            title="Remove source"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
