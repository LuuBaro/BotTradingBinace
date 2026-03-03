import React, { useState, useEffect } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Shield, Key, Sparkles, Brain, Save, CheckCircle, AlertCircle, Lock, Eye, EyeOff } from 'lucide-react'

// Helper: detect if a value from server is a masked placeholder (already saved)
const isMasked = (val: string | undefined | null): boolean =>
    !!(val && val !== 'not_set' && (val.includes('***') || val.includes('****')))

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
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite',
        'gemini-2.0-pro',
        'gemini-1.5-pro',
        'gemini-1.5-pro-latest',
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest'
    ],
    groq: [
        'llama3-70b-8192',
        'llama3-8b-8192',
        'mixtral-8x7b-32768',
        'gemma-7b-it'
    ]
}

export const NeuralPortalPage: React.FC = () => {
    const api = createApiClient(getApiBaseUrl(), localStorage.getItem('token') || '')
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null)
    const [showSecrets, setShowSecrets] = useState(false)

    // Track which fields already have a saved value (masked from backend)
    const [savedStatus, setSavedStatus] = useState({
        binance_api_key: false,
        binance_api_secret: false,
        ai_api_key: false,
    })

    const [creds, setCreds] = useState({
        binance_api_key: '',
        binance_api_secret: '',
        use_testnet: true,
        ai_provider: 'gemini',  // Default to Gemini now (working)
        ai_api_key: '',
        ai_model: 'gemini-2.5-flash',  // Latest working model
        ai_custom_endpoint: 'https://generativelanguage.googleapis.com/v1beta'
    })

    useEffect(() => {
        const fetchCreds = async () => {
            try {
                const res = await api.get('user/credentials')
                if (res.data) {
                    const d = res.data

                    // Track which keys are already saved (server returns masked value)
                    setSavedStatus({
                        binance_api_key: isMasked(d.binance_api_key),
                        binance_api_secret: isMasked(d.binance_api_secret),
                        ai_api_key: isMasked(d.ai_api_key),
                    })

                    setCreds(prev => ({
                        ...prev,
                        use_testnet: d.use_testnet ?? true,
                        ai_provider: d.ai_provider || 'openai',
                        ai_model: d.ai_model || 'gpt-4',
                        ai_custom_endpoint: d.ai_custom_endpoint || (d.ai_provider === 'gemini' ? 'https://generativelanguage.googleapis.com/v1beta/openai' : ''),
                        // Actually fill the state with masked placeholders from server
                        binance_api_key: isMasked(d.binance_api_key) ? '********************' : '',
                        binance_api_secret: isMasked(d.binance_api_secret) ? '********************' : '',
                        ai_api_key: isMasked(d.ai_api_key) ? '********************' : '',
                    }))
                }
            } catch (err) {
                console.error('Failed to fetch credentials')
            } finally {
                setLoading(false)
            }
        }
        fetchCreds()
    }, [])

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setSaving(true)
        setStatus(null)
        try {
            // Only send non-masked values that user actually changed
            const payload: Record<string, any> = {
                use_testnet: creds.use_testnet,
                ai_provider: creds.ai_provider,
                ai_model: creds.ai_model,
                ai_custom_endpoint: creds.ai_custom_endpoint,
            }
            if (creds.binance_api_key.trim() && !creds.binance_api_key.includes('*')) payload.binance_api_key = creds.binance_api_key
            if (creds.binance_api_secret.trim() && !creds.binance_api_secret.includes('*')) payload.binance_api_secret = creds.binance_api_secret
            if (creds.ai_api_key.trim() && !creds.ai_api_key.includes('*')) payload.ai_api_key = creds.ai_api_key

            await api.post('user/credentials', payload)

            // After saving, mark as saved
            setSavedStatus(prev => ({
                binance_api_key: prev.binance_api_key || !!creds.binance_api_key.trim(),
                binance_api_secret: prev.binance_api_secret || !!creds.binance_api_secret.trim(),
                ai_api_key: prev.ai_api_key || !!creds.ai_api_key.trim(),
            }))
            // Clear the input fields (security — no raw key in DOM)
            setCreds(prev => ({ ...prev, binance_api_key: '', binance_api_secret: '', ai_api_key: '' }))

            setStatus({ type: 'success', message: ' Neural settings saved. Keys encrypted & secured.' })
        } catch (err) {
            setStatus({ type: 'error', message: '❌ Failed to update credentials. Please check your data.' })
        } finally {
            setSaving(false)
        }
    }

    if (loading) return <div className="text-white p-8">Neural portal syncing...</div>

    // Reusable indicator for saved key status
    const SavedBadge = ({ field }: { field: keyof typeof savedStatus }) =>
        savedStatus[field] ? (
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                <Lock size={9} />
                KEY SAVED & ENCRYPTED
            </div>
        ) : (
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 bg-slate-700/30 px-2.5 py-1 rounded-full border border-white/5">
                NOT SET
            </div>
        )

    return (
        <div className="max-w-4xl mx-auto animate-fadeIn pb-20">
            <div className="mb-10">
                <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="text-blue-400" size={14} />
                    <span className="text-[10px] uppercase font-black tracking-[0.3em] text-blue-400">Personalized Engine Config</span>
                </div>
                <h1 className="text-4xl font-black tracking-tighter text-white">API Keys & AI Context</h1>
                <p className="text-slate-400 mt-2 font-medium">Cấu hình API Binance và bộ não AI (OpenAI, Claude, Gemini) của riêng sếp tại đây.</p>
            </div>

            {/* Global show/hide toggle */}
            <div className="flex justify-end mb-4">
                <button
                    type="button"
                    onClick={() => setShowSecrets(!showSecrets)}
                    className="flex items-center gap-2 text-xs font-bold text-slate-400 hover:text-white transition-colors px-3 py-2 bg-white/5 rounded-xl border border-white/10 hover:border-white/20"
                >
                    {showSecrets ? <EyeOff size={13} /> : <Eye size={13} />}
                    {showSecrets ? 'Hide Inputs' : 'Edit Keys'}
                </button>
            </div>

            <form onSubmit={handleSave} className="space-y-8">
                {/* Admin Critical Warning */}
                <section className="glass-dark border-blue-500/20 rounded-3xl p-6 space-y-4 bg-gradient-to-r from-blue-950/30 to-blue-900/20">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="text-blue-400 flex-shrink-0 mt-1" size={20} />
                        <div className="space-y-2">
                            <h3 className="text-sm font-black text-blue-300 uppercase tracking-widest">Cấu hình AI của Admin</h3>
                            <p className="text-xs text-blue-200/90">
                                Anh là admin — cần **cấu hình key và AI riêng** ở đây để hệ thống hoạt động. Nếu anh không set key, hệ thống sẽ dùng fallback global từ <code className="text-blue-100 bg-black/30 px-2 py-1 rounded">/settings</code> (nếu có).
                            </p>
                            <p className="text-xs text-amber-300 mt-2">
                                ✓ Ngoài ra, anh có thể cấu hình trader riêng nếu cần (SaaS feature).
                            </p>
                        </div>
                    </div>
                </section>

                {savedStatus.ai_api_key && (
                    <section className="glass-dark border-emerald-500/20 rounded-3xl p-6 space-y-2 bg-gradient-to-r from-emerald-950/30 to-emerald-900/20">
                        <div className="flex items-center gap-2">
                            <CheckCircle className="text-emerald-400" size={18} />
                            <p className="text-sm font-bold text-emerald-300">AI Key đã lưu & mã hóa ✓</p>
                        </div>
                        <p className="text-xs text-emerald-200/80">Hệ thống sẽ ưu tiên dùng key của anh thay vì fallback global.</p>
                    </section>
                )}
                
                {!savedStatus.ai_api_key && (
                    <section className="glass-dark border-amber-500/20 rounded-3xl p-6 space-y-2 bg-gradient-to-r from-amber-950/30 to-amber-900/20">
                        <div className="flex items-center gap-2">
                            <AlertCircle className="text-amber-400" size={18} />
                            <p className="text-sm font-bold text-amber-300">Chưa set AI key</p>
                        </div>
                        <p className="text-xs text-amber-200/80">Admin chưa cấu hình key AI riêng. Worker sẽ dùng fallback từ /settings (nếu có). 👈 Hãy set ngay nếu muốn AI hoạt động.</p>
                    </section>
                )}

                {/* Binance Section */}
                <section className="glass-dark border-white/5 rounded-3xl p-8 space-y-6">
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-yellow-500/10 rounded-xl text-yellow-500">
                                <Shield size={20} />
                            </div>
                            <h2 className="text-xl font-bold text-white">Binance Nexus</h2>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">API Key</label>
                                <SavedBadge field="binance_api_key" />
                            </div>
                            {showSecrets ? (
                                <input
                                    type="text"
                                    value={creds.binance_api_key}
                                    onChange={e => setCreds({ ...creds, binance_api_key: e.target.value })}
                                    placeholder={savedStatus.binance_api_key ? "Leave blank to keep existing key" : "Paste your Binance API Key"}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-yellow-500/50 font-mono"
                                />
                            ) : (
                                <div className={`w-full rounded-xl py-3 px-4 text-sm font-mono flex items-center gap-2 ${savedStatus.binance_api_key ? 'bg-emerald-500/5 border border-emerald-500/20 text-emerald-300' : 'bg-black/20 border border-white/5 text-slate-600'}`}>
                                    {savedStatus.binance_api_key ? <><Lock size={13} className="text-emerald-400" /> <span>••••••••••••••••••••••••</span></> : <span className="italic text-slate-600">Not configured</span>}
                                </div>
                            )}
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">API Secret</label>
                                <SavedBadge field="binance_api_secret" />
                            </div>
                            {showSecrets ? (
                                <input
                                    type="password"
                                    value={creds.binance_api_secret}
                                    onChange={e => setCreds({ ...creds, binance_api_secret: e.target.value })}
                                    placeholder={savedStatus.binance_api_secret ? "Leave blank to keep existing secret" : "Paste your API Secret"}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-yellow-500/50"
                                />
                            ) : (
                                <div className={`w-full rounded-xl py-3 px-4 text-sm font-mono flex items-center gap-2 ${savedStatus.binance_api_secret ? 'bg-emerald-500/5 border border-emerald-500/20 text-emerald-300' : 'bg-black/20 border border-white/5 text-slate-600'}`}>
                                    {savedStatus.binance_api_secret ? <><Lock size={13} className="text-emerald-400" /> <span>••••••••••••••••••••••••</span></> : <span className="italic text-slate-600">Not configured</span>}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-2 p-4 bg-yellow-500/5 rounded-2xl border border-yellow-500/10">
                        <input
                            type="checkbox"
                            id="testnet"
                            checked={creds.use_testnet}
                            onChange={e => setCreds({ ...creds, use_testnet: e.target.checked })}
                            className="w-4 h-4 rounded bg-slate-900 border-white/10 text-yellow-500"
                        />
                        <label htmlFor="testnet" className="text-sm font-bold text-yellow-500/80">Use Binance Testnet (Recommended for safety)</label>
                    </div>
                </section>

                {/* AI Section */}
                <section className="glass-dark border-white/5 rounded-3xl p-8 space-y-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-500/10 rounded-xl text-blue-400">
                            <Brain size={20} />
                        </div>
                        <h2 className="text-xl font-bold text-white">Custom Neural Intelligence</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">AI Provider</label>
                            <select
                                value={creds.ai_provider}
                                onChange={e => {
                                    const newProvider = e.target.value
                                    setCreds({ 
                                        ...creds, 
                                        ai_provider: newProvider,
                                        ai_custom_endpoint: newProvider === 'gemini' && !creds.ai_custom_endpoint 
                                            ? 'https://generativelanguage.googleapis.com/v1beta/openai' 
                                            : creds.ai_custom_endpoint
                                    })
                                }}
                                className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-blue-500/50"
                            >
                                <option value="openai">OpenAI (GPT-4)</option>
                                <option value="anthropic">Anthropic (Claude)</option>
                                <option value="gemini">Google Gemini</option>
                                <option value="groq">Groq (Fast Llama)</option>
                                <option value="manual">Custom (Local/Ollama)</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">Model Name</label>
                            {creds.ai_provider === 'manual' ? (
                                <input
                                    type="text"
                                    value={creds.ai_model}
                                    onChange={e => setCreds({ ...creds, ai_model: e.target.value })}
                                    placeholder="e.g. llama3:70b"
                                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-blue-500/50 font-mono"
                                />
                            ) : (
                                <select
                                    value={creds.ai_model}
                                    onChange={e => setCreds({ ...creds, ai_model: e.target.value })}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-blue-500/50 font-mono"
                                >
                                    {MODEL_OPTIONS[creds.ai_provider]?.map((model) => (
                                        <option key={model} value={model}>{model}</option>
                                    ))}
                                </select>
                            )}
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <div className="flex items-center justify-between">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">AI API Key</label>
                                <SavedBadge field="ai_api_key" />
                            </div>
                            {showSecrets ? (
                                <div className="space-y-2">
                                    <div className="relative">
                                        <input
                                            type="password"
                                            value={creds.ai_api_key}
                                            onChange={e => setCreds({ ...creds, ai_api_key: e.target.value })}
                                            placeholder={savedStatus.ai_api_key ? "Leave blank to keep existing key" : "Paste your AI Provider API Key"}
                                            className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-blue-500/50"
                                        />
                                        <Key className="absolute right-4 top-3 text-slate-600" size={16} />
                                    </div>
                                    {creds.ai_provider === 'gemini' && (
                                        <p className="text-xs text-blue-300/70">
                                            💡 Lấy key từ Google Cloud Console. Đã test & validate: <code className="bg-black/50 px-1.5 py-0.5 rounded text-blue-200">gemini-2.5-flash</code> hoạt động ✓
                                        </p>
                                    )}
                                </div>
                            ) : (
                                <div className={`w-full rounded-xl py-3 px-4 text-sm font-mono flex items-center gap-2 ${savedStatus.ai_api_key ? 'bg-emerald-500/5 border border-emerald-500/20 text-emerald-300' : 'bg-black/20 border border-white/5 text-slate-600'}`}>
                                    {savedStatus.ai_api_key ? <><Lock size={13} className="text-emerald-400" /> <span>••••••••••••••••••••••••</span></> : <span className="italic text-slate-600">Not configured</span>}
                                </div>
                            )}
                        </div>

                        {(creds.ai_provider === 'manual' || creds.ai_provider === 'gemini') ? (
                            <div className="md:col-span-2 space-y-2 animate-fadeIn">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                                    {creds.ai_provider === 'gemini' ? 'Gemini Endpoint URL' : 'Custom Endpoint URL (Optional)'}
                                </label>
                                <input
                                    type="text"
                                    value={creds.ai_custom_endpoint}
                                    onChange={e => setCreds({ ...creds, ai_custom_endpoint: e.target.value })}
                                    placeholder={creds.ai_provider === 'gemini' 
                                        ? 'https://generativelanguage.googleapis.com/v1beta/openai' 
                                        : 'https://api.openai-compatible.com/v1 or http://localhost:11434'}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 px-4 text-sm text-white focus:outline-none focus:border-blue-500/50"
                                />
                            </div>
                        ) : null}
                    </div>
                </section>

                {status && (
                    <div className={`p-4 rounded-2xl border flex items-center gap-3 animate-slideUp ${status.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                        }`}>
                        {status.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                        <span className="text-sm font-bold">{status.message}</span>
                    </div>
                )}

                <div className="flex justify-end gap-4">
                    <button
                        type="submit"
                        disabled={saving}
                        className="flex items-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all shadow-xl shadow-blue-500/20 active:scale-95"
                    >
                        {saving ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Save size={18} />}
                        {saving ? 'Synchronizing...' : 'Save Neural Config'}
                    </button>
                </div>
            </form>
        </div>
    )
}
