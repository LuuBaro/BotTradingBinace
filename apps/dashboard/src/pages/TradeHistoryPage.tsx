import React, { useEffect, useState, useMemo } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { format } from 'date-fns'
import { RefreshCw, TrendingUp, History, Search, Download, Filter } from 'lucide-react'

export const TradeHistoryPage: React.FC = () => {
    const [trades, setTrades] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)

    // Memoized API client
    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    useEffect(() => {
        const fetchTrades = async () => {
            setLoading(true)
            try {
                const response = await api.getTrades(100)
                setTrades(Array.isArray(response) ? response : [])
            } catch (error) {
                console.error('Failed to fetch trades:', error)
            } finally {
                setLoading(false)
            }
        }

        fetchTrades()
        const interval = setInterval(fetchTrades, 30000) // Poll every 30s
        return () => clearInterval(interval)
    }, [api, refreshKey])

    return (
        <div className="space-y-8 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                            <History className="text-blue-400" size={24} />
                        </div>
                        <span className="text-xs font-bold text-blue-400 uppercase tracking-widest text-shadow-glow">Exchange Connectivity</span>
                    </div>
                    <h1 className="text-5xl font-black text-gradient">Lịch sử khớp lệnh</h1>
                    <p className="text-slate-400 mt-2 max-w-xl">Dữ liệu chi tiết các giao dịch đã thực hiện thành công trực tiếp từ Binance Futures.</p>
                </div>

                <div className="flex gap-3">
                    <div className="flex items-center gap-2 p-1.5 glass-dark border-white/5 rounded-2xl">
                        <button
                            onClick={() => setRefreshKey(k => k + 1)}
                            className={`p-2.5 rounded-xl transition-all ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/5 active:scale-95'}`}
                            disabled={loading}
                        >
                            <RefreshCw size={18} className={`${loading ? 'animate-spin' : ''} text-blue-400`} />
                        </button>
                    </div>
                    <button className="btn btn-secondary border-white/5 hover:bg-white/5">
                        <Download size={18} />
                        Xuất CSV
                    </button>
                </div>
            </div>

            {/* Stats Summary Area */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="card glass-dark border-white/5 p-6 space-y-2">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">Tổng lượt Trade</span>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-black text-white font-mono">{trades.length}</span>
                        <span className="text-xs text-slate-500 font-bold mb-1.5 italic">phiên khớp</span>
                    </div>
                </div>
                <div className="card glass-dark border-white/5 p-6 space-y-2">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">Phí trung bình</span>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-black text-blue-400 font-mono">
                            {trades.length > 0 ? (trades.reduce((acc, t) => acc + t.commission, 0) / trades.length).toFixed(4) : '0.0000'}
                        </span>
                        <span className="text-xs text-slate-500 font-bold mb-1.5 uppercase">USDT</span>
                    </div>
                </div>
                <div className="card glass-dark border-white/5 p-6 border-l-4 border-l-emerald-500/50 space-y-2">
                    <span className="text-[10px] font-black text-emerald-500/70 uppercase tracking-widest block">Tổng PnL đã chốt</span>
                    <div className="flex items-end gap-2 text-emerald-400">
                        <span className="text-3xl font-black font-mono">
                            {trades.reduce((acc, t) => acc + t.realized_pnl, 0).toFixed(2)}
                        </span>
                        <span className="text-xs font-bold mb-1.5 uppercase tracking-tighter">USDT</span>
                    </div>
                </div>
                <div className="card glass-dark border-white/5 p-6 border-l-4 border-l-blue-500/50 space-y-2">
                    <span className="text-[10px] font-black text-blue-500/70 uppercase tracking-widest block">Tổng Volume</span>
                    <div className="flex items-end gap-2 text-blue-400">
                        <span className="text-3xl font-black font-mono">
                            {trades.reduce((acc, t) => acc + t.quote_qty, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </span>
                        <span className="text-xs font-bold mb-1.5 uppercase tracking-tighter">USDT</span>
                    </div>
                </div>
            </div>

            {/* Main Data Table */}
            <div className="card glass-dark border-white/5 shadow-3xl overflow-hidden animate-slideUp">
                <div className="p-6 border-b border-white/5 bg-white/[0.02] flex flex-col md:flex-row justify-between gap-4">
                    <div className="relative flex-grow max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                        <input
                            type="text"
                            placeholder="Tìm kiếm theo mã lệnh, cặp tiền..."
                            className="w-full bg-slate-950/50 border border-white/5 rounded-2xl py-3 pl-12 pr-4 text-sm focus:outline-none focus:border-blue-500/50 transition-colors uppercase font-mono"
                        />
                    </div>
                    <div className="flex gap-2">
                        <button className="px-5 py-3 glass-dark border-white/5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-white transition-colors flex items-center gap-2">
                            <Filter size={14} />
                            Bộ lọc nâng cao
                        </button>
                    </div>
                </div>

                <div className="table-container p-0 border-none">
                    <table className="table">
                        <thead>
                            <tr className="bg-white/[0.03]">
                                <th className="py-6 px-8 rounded-tl-2xl">Mã lệnh (Order No.)</th>
                                <th>Thời gian</th>
                                <th>Cặp tiền</th>
                                <th>Chiều (Side)</th>
                                <th>Giá khớp</th>
                                <th>Khối lượng</th>
                                <th>Phí (Fee)</th>
                                <th>Vai trò</th>
                                <th className="text-right px-8 rounded-tr-2xl">PnL Thực tế</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {trades.length === 0 && !loading ? (
                                <tr>
                                    <td colSpan={9} className="text-center py-32 opacity-30">
                                        <div className="flex flex-col items-center gap-4">
                                            <TrendingUp size={48} />
                                            <span className="text-xs font-black uppercase tracking-[0.3em]">Không có dữ liệu giao dịch thực tế</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                trades.map((trade, idx) => (
                                    <tr key={`${trade.id}-${idx}`} className="group hover:bg-white/[0.03] transition-colors">
                                        <td className="py-5 px-8">
                                            <span className="text-xs font-mono font-black text-slate-500 uppercase tracking-tighter">#{trade.order_id}</span>
                                        </td>
                                        <td>
                                            <div className="flex flex-col">
                                                <span className="text-[11px] font-black text-slate-300">
                                                    {format(new Date(trade.time), 'yyyy-MM-dd HH:mm:ss')}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="font-black font-mono text-white italic tracking-tighter">{trade.symbol}</td>
                                        <td>
                                            <span className={`px-3 py-1 rounded-xl text-[10px] font-black uppercase tracking-widest ${trade.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                                }`}>
                                                {trade.side === 'BUY' ? 'MUA' : 'BÁN'}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="text-xs font-black font-mono text-white">
                                                $ {trade.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                            </span>
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-1">
                                                <span className="text-xs font-black font-mono text-blue-100">{trade.qty}</span>
                                                <span className="text-[9px] text-slate-600 font-bold uppercase">{trade.symbol.replace('USDT', '')}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div className="flex flex-col">
                                                <span className="text-[10px] font-black text-slate-400 font-mono">{trade.commission.toFixed(4)}</span>
                                                <span className="text-[8px] text-slate-600 uppercase font-black">{trade.commission_asset}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span className={`text-[10px] font-black uppercase tracking-widest ${trade.role === 'Maker' ? 'text-blue-400' : 'text-slate-500'}`}>
                                                {trade.role}
                                            </span>
                                        </td>
                                        <td className="text-right px-8">
                                            <span className={`text-xs font-black font-mono ${trade.realized_pnl > 0 ? 'text-emerald-400' :
                                                    trade.realized_pnl < 0 ? 'text-rose-400' : 'text-slate-500'
                                                }`}>
                                                {trade.realized_pnl > 0 ? '+' : ''}{trade.realized_pnl.toFixed(4)}
                                                <span className="text-[9px] ml-1 opacity-50 uppercase tracking-tighter">USDT</span>
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Data Source Footer */}
            <div className="flex justify-between items-center opacity-30 text-[9px] font-black uppercase tracking-[0.3em] px-2 text-slate-500">
                <div className="flex items-center gap-4">
                    <span>Binance Data Link: ACTIVE</span>
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                </div>
                <span>Last Synced: {format(new Date(), 'HH:mm:ss')}</span>
            </div>
        </div>
    )
}
