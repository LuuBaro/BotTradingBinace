import React, { useEffect, useState, useMemo } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Wallet, TrendingUp, TrendingDown, Clock, ArrowRightLeft } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export const WalletIndicator: React.FC = () => {
    const [data, setData] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [showDetails, setShowDetails] = useState(false)
    const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null)

    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    const fetchBalance = async () => {
        try {
            const response = await api.getWalletBalance()
            setData(response)
        } catch (error) {
            console.error('Failed to fetch wallet balance:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleMouseEnter = () => {
        if (timeoutId) clearTimeout(timeoutId)
        setShowDetails(true)
    }

    const handleMouseLeave = () => {
        const id = setTimeout(() => {
            setShowDetails(false)
        }, 400) // 400ms grace period to move mouse to popup
        setTimeoutId(id)
    }

    useEffect(() => {
        fetchBalance()
        const interval = setInterval(fetchBalance, 30000) // Update every 30s
        return () => clearInterval(interval)
    }, [api])

    if (loading && !data) return (
        <div className="h-10 w-32 bg-white/5 animate-pulse rounded-xl border border-white/5"></div>
    )

    const isProfit = (data?.pnl_24h || 0) >= 0

    return (
        <div
            className="relative"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <div
                className="flex items-center gap-4 px-5 py-2.5 glass-dark border border-white/10 rounded-2xl cursor-pointer group hover:border-blue-500/30 transition-all shadow-lg"
            >
                <div className="p-2 bg-blue-500/10 rounded-xl group-hover:scale-110 transition-transform">
                    <Wallet size={18} className="text-blue-400" />
                </div>
                <div className="flex flex-col">
                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Wallet Balance</span>
                    <span className="text-sm font-black text-white font-mono tracking-tighter">
                        ${data?.wallet_balance?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                </div>
                <div className={`flex flex-col items-end pl-4 border-l border-white/5`}>
                    <div className={`flex items-center gap-1 text-[10px] font-black ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isProfit ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                        {isProfit ? '+' : ''}{data?.pnl_24h_pct?.toFixed(2)}%
                    </div>
                    <span className="text-[8px] font-bold text-slate-600 uppercase">24H Alpha</span>
                </div>
            </div>

            {showDetails && data?.recent_trades && (
                <div className="absolute right-0 mt-3 w-80 bg-[#0f172a] border border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-3xl z-[100] overflow-hidden animate-slideUp">
                    {/* Bridge element to allow mouse movement across the gap */}
                    <div className="absolute -top-3 left-0 right-0 h-3 bg-transparent"></div>

                    <div className="p-5 border-b border-white/5 bg-white/[0.02]">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                                <ArrowRightLeft size={14} className="text-blue-400" />
                                Giao dịch gần đây
                            </h3>
                            <span className="text-[9px] font-bold text-slate-500">Live Context</span>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div className="p-3 bg-white/5 rounded-2xl border border-white/5">
                                <span className="text-[8px] text-slate-500 font-bold uppercase block mb-1">Available</span>
                                <span className="text-xs font-mono font-black text-white">${data.available_balance?.toLocaleString()}</span>
                            </div>
                            <div className="p-3 bg-white/5 rounded-2xl border border-white/5">
                                <span className="text-[8px] text-slate-500 font-bold uppercase block mb-1">24h Change</span>
                                <span className={`text-xs font-mono font-black ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {isProfit ? '+' : ''}${data.pnl_24h?.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="p-3 space-y-2 max-h-[300px] overflow-y-auto custom-scrollbar">
                        {data.recent_trades.length === 0 ? (
                            <div className="p-8 text-center opacity-30">
                                <span className="text-[10px] font-bold uppercase tracking-widest">Chưa có giao dịch gần đây</span>
                            </div>
                        ) : (
                            data.recent_trades.map((trade: any, i: number) => (
                                <div key={i} className="p-3 hover:bg-white/5 rounded-2xl transition-colors border border-transparent hover:border-white/5 group/item">
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[11px] font-black text-white font-mono">{trade.symbol}</span>
                                            <span className={`text-[8px] px-1.5 py-0.5 rounded font-black ${trade.side === 'LONG' || trade.side === 'WIN' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                                                {trade.side}
                                            </span>
                                        </div>
                                        <span className={`text-[10px] font-black font-mono ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                            {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center uppercase">
                                        <span className="text-[8px] font-bold text-slate-600 tracking-tighter">{trade.exit_reason}</span>
                                        <div className="flex items-center gap-1 opacity-40 group-hover/item:opacity-70 transition-opacity">
                                            <Clock size={8} />
                                            <span className="text-[8px] font-black">{formatDistanceToNow(new Date(trade.closed_at), { addSuffix: true })}</span>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    <button
                        onClick={() => window.location.href = '/orders'}
                        className="w-full p-4 text-[10px] font-black text-blue-400 hover:text-white hover:bg-blue-500/10 transition-all uppercase tracking-widest border-t border-white/5"
                    >
                        Xem nhật ký đầy đủ →
                    </button>
                </div>
            )}
        </div>
    )
}
