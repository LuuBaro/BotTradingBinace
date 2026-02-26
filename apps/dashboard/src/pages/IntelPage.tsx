import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { format } from 'date-fns'
import { Brain, Shield, Zap, TrendingUp, AlertTriangle, Target, Search } from 'lucide-react'

export const IntelPage: React.FC = () => {
    const navigate = useNavigate()
    const [signals, setSignals] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [approvalMode, setApprovalMode] = useState(false)

    // Explicitly create API client to avoid re-creation issues in hooks
    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    const fetchSignals = async () => {
        try {
            const response = await api.getSignals()
            setSignals(response.signals || [])

            const actionsStatus = await api.getActionsStatus()
            setApprovalMode(actionsStatus.approval_mode || false)
        } catch (error) {
            console.error('Failed to fetch signals:', error)
        } finally {
            setLoading(false)
        }
    }

    const toggleApproval = async () => {
        try {
            const nextMode = !approvalMode
            await api.updateApprovalMode(nextMode)
            setApprovalMode(nextMode)
        } catch (error) {
            console.error('Failed to toggle approval mode:', error)
        }
    }

    useEffect(() => {
        fetchSignals()
        const interval = setInterval(fetchSignals, 5000)
        return () => clearInterval(interval)
    }, [api])

    return (
        <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
            {/* Hero Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                            <Brain className="text-blue-400" size={24} />
                        </div>
                        <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Market Intelligence</span>
                    </div>
                    <h1 className="text-5xl font-black text-gradient">Neural Watchlist</h1>
                    <p className="text-slate-400 mt-2 max-w-xl">
                        AI-driven market scanning and predictive signal generation.
                        Live neural analysis of cross-exchange orderbooks and technical clusters.
                    </p>
                </div>

                <div className="flex flex-col items-end gap-4 p-6 glass-dark rounded-3xl border border-white/5 shadow-2xl">
                    <div className="flex items-center gap-4">
                        <div className="text-right">
                            <span className="text-[10px] uppercase font-black text-slate-500 block mb-1">Control Mode</span>
                            <span className={`text-sm font-bold uppercase ${approvalMode ? 'text-amber-400' : 'text-emerald-400'}`}>
                                {approvalMode ? 'Manual Approval' : 'Autonomous'}
                            </span>
                        </div>
                        <button
                            onClick={toggleApproval}
                            className={`w-14 h-7 rounded-full transition-all relative border border-white/10 ${approvalMode ? 'bg-amber-600 shadow-amber-500/20' : 'bg-emerald-600 shadow-emerald-500/20'}`}
                        >
                            <div className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow-lg transition-all transform ${approvalMode ? 'translate-x-8' : 'translate-x-1'}`}></div>
                        </button>
                    </div>
                    <div className="h-px w-full bg-white/5"></div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                        <span className="text-xs font-mono text-slate-400">{signals.length} high-confidence setups</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                {/* Signals Column */}
                <div className="lg:col-span-7 space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-bold flex items-center gap-3 underline decoration-blue-500/30 underline-offset-8">
                            <Zap className="text-amber-400" size={20} />
                            Active Signal Clusters
                        </h2>
                    </div>

                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-50">
                            <div className="spinner w-10 h-10"></div>
                            <span className="text-xs uppercase font-bold tracking-widest">Scanning Markets...</span>
                        </div>
                    ) : signals.length === 0 ? (
                        <div className="card p-20 text-center flex flex-col items-center gap-4">
                            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center border border-slate-700">
                                <Search size={24} className="text-slate-500" />
                            </div>
                            <div>
                                <h3 className="text-slate-300 font-bold">No setups detected</h3>
                                <p className="text-xs text-slate-500 mt-1">Markets are currently in low-probability consolidation.</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {signals.map((signal) => (
                                <div key={signal.id} className="card group hover:scale-[1.01] border-l-4 border-l-blue-500">
                                    <div className="p-6 flex justify-between items-center">
                                        <div className="space-y-3">
                                            <div className="flex items-center gap-4">
                                                <div className="flex flex-col">
                                                    <span className="text-2xl font-black font-mono tracking-tighter text-blue-50">{signal.symbol}</span>
                                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                                                        {format(new Date(signal.timestamp), 'HH:mm:ss')}
                                                    </span>
                                                </div>
                                                <span className={`px-4 py-1 rounded-lg text-[10px] font-black border tracking-wider ${signal.side === 'LONG'
                                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                                    }`}>
                                                    {signal.side}
                                                </span>
                                            </div>
                                            <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                                                <p className="text-sm text-slate-300 leading-relaxed font-medium">
                                                    <Brain size={12} className="inline mr-2 text-blue-400" />
                                                    {signal.rationale}
                                                </p>
                                            </div>
                                            <div className="flex gap-3">
                                                <div className="text-[10px] bg-slate-900 border border-slate-800 px-3 py-1 rounded-md text-slate-400">
                                                    ZONE: <span className="font-mono text-blue-300">{signal.entry_zone}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex flex-col items-end gap-2 pr-2">
                                            <div className="relative w-16 h-16">
                                                <svg className="w-full h-full transform -rotate-90">
                                                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-slate-800" />
                                                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="transparent"
                                                        strokeDasharray={175}
                                                        strokeDashoffset={175 - (175 * signal.probability)}
                                                        className="text-blue-500"
                                                    />
                                                </svg>
                                                <div className="absolute inset-0 flex items-center justify-center flex-col">
                                                    <span className="text-sm font-black text-blue-50">{(signal.probability * 100).toFixed(0)}</span>
                                                    <span className="text-[6px] uppercase text-slate-500">Prob</span>
                                                </div>
                                            </div>
                                            <button className="text-[10px] font-bold text-blue-400 hover:text-white transition-colors">DETAILS →</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* AI Bias & Strategy Column */}
                <div className="lg:col-span-5 space-y-8">
                    {/* Market Bias Card */}
                    <div className="card bg-gradient-to-br from-slate-900 via-slate-900 to-blue-900/10 border-blue-500/20">
                        <div className="p-8 space-y-8">
                            <h2 className="text-xl font-black flex items-center gap-3 uppercase tracking-tighter">
                                <Shield className="text-blue-400" size={20} />
                                Neural Market Bias
                            </h2>

                            <div className="space-y-8">
                                <div className="space-y-3">
                                    <div className="flex justify-between items-end">
                                        <span className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Bullish Pressure</span>
                                        <span className="text-lg font-black font-mono text-blue-400">72%</span>
                                    </div>
                                    <div className="h-2 bg-slate-950 rounded-full overflow-hidden flex">
                                        <div className="w-[72%] bg-gradient-to-r from-blue-600 to-blue-400 h-full shadow-[0_0_15px_rgba(59,130,246,0.4)]"></div>
                                        <div className="flex-1 bg-slate-800 h-full"></div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-950/60 p-5 rounded-2xl border border-white/5 space-y-1">
                                        <TrendingUp className="text-emerald-400 mb-2" size={16} />
                                        <span className="text-[10px] text-slate-500 block font-bold uppercase">Trend</span>
                                        <span className="text-sm font-black text-emerald-400">STRUCTURAL BULL</span>
                                    </div>
                                    <div className="bg-slate-950/60 p-5 rounded-2xl border border-white/5 space-y-1">
                                        <AlertTriangle className="text-amber-400 mb-2" size={16} />
                                        <span className="text-[10px] text-slate-500 block font-bold uppercase">Volatility</span>
                                        <span className="text-sm font-black text-amber-400">EXPANDING</span>
                                    </div>
                                </div>

                                <div className="p-6 bg-blue-500/5 rounded-2xl border border-blue-500/10 space-y-3">
                                    <h3 className="text-[11px] font-black text-blue-400 uppercase tracking-widest flex items-center gap-2">
                                        <Target size={14} />
                                        Deployment Focus
                                    </h3>
                                    <p className="text-xs text-slate-400 leading-relaxed font-medium">
                                        Neutralization of liquidity voids at $94,200. Strategy is currently overweight on
                                        Mean Reversion setups while trend consolidation occurs on HTF.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* AI Learning Progress */}
                    <div className="card border-purple-500/20 bg-gradient-to-br from-slate-900 to-purple-900/10 group overflow-hidden relative">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 blur-3xl group-hover:bg-purple-500/10 transition-all"></div>
                        <div className="p-8 text-center space-y-6 relative z-10">
                            <div className="w-20 h-20 bg-purple-500/10 rounded-3xl flex items-center justify-center mx-auto border border-purple-500/20 rotate-12 group-hover:rotate-0 transition-transform duration-500">
                                <Zap className="text-purple-400" size={32} />
                            </div>
                            <div>
                                <h3 className="text-xl font-black text-white">Quantum Optimization</h3>
                                <p className="text-xs text-slate-500 mt-2 font-medium">
                                    AI is re-calculating risk weights based on 32,491 data points from the last session.
                                </p>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => navigate('/trades')}
                                    className="btn btn-secondary text-[10px] h-10 flex-1"
                                >
                                    View Decision Logs
                                </button>
                                <button className="btn btn-primary text-[10px] h-10 flex-1">Optimize Now</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
