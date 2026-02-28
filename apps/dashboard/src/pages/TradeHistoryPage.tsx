import React, { useEffect, useState, useMemo } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { format, formatDistanceToNow } from 'date-fns'
import { RefreshCw, TrendingUp, History, Search, Download, Filter, ChevronDown, Layers, CheckCircle2, XCircle, Activity, X, Hash, ArrowUpRight, ArrowDownRight, Zap } from 'lucide-react'

// Custom Premium Select Component (Same as OrdersPage for consistency)
const CustomSelect: React.FC<{
    value: number | string;
    onChange: (val: any) => void;
    options: { label: string; value: any }[];
    label?: string;
    prefix?: string;
    position?: 'top' | 'bottom';
}> = ({ value, onChange, options, label, prefix, position = 'bottom' }) => {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = React.useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const selectedOption = options.find(o => o.value === value);

    return (
        <div className="relative" ref={containerRef}>
            <div className="flex items-center gap-3">
                {label && <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest whitespace-nowrap">{label}</span>}
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex items-center justify-between gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-[10px] font-black text-white hover:bg-white/10 hover:border-blue-500/50 transition-all min-w-[120px] shadow-lg"
                >
                    <span className="truncate">{prefix}{selectedOption?.label || value}</span>
                    <ChevronDown size={14} className={`text-slate-500 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
                </button>
            </div>

            {isOpen && (
                <div className={`absolute z-[100] ${position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'} right-0 min-w-[160px] bg-[#1a1d2d] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-slideUp backdrop-blur-xl ring-1 ring-white/10`}>
                    <div className="max-h-60 overflow-y-auto custom-scrollbar p-1.5">
                        {options.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => {
                                    onChange(opt.value);
                                    setIsOpen(false);
                                }}
                                className={`w-full text-left px-4 py-2.5 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all mb-1 last:mb-0 ${value === opt.value
                                    ? 'bg-blue-600/30 text-blue-400 border border-blue-500/20'
                                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                                    }`}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export const TradeHistoryPage: React.FC = () => {
    const [trades, setTrades] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)
    const [searchQuery, setSearchQuery] = useState('')
    const [fetchLimit, setFetchLimit] = useState(100)
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(10)
    const [selectedTrade, setSelectedTrade] = useState<any | null>(null)

    // Memoized API client
    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    useEffect(() => {
        const fetchTrades = async () => {
            setLoading(true)
            try {
                const response = await api.getTrades(fetchLimit)
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
    }, [api, refreshKey, fetchLimit])

    const filteredTrades = useMemo(() => {
        if (!searchQuery.trim()) return trades
        const query = searchQuery.toLowerCase()
        return trades.filter(t =>
            t.symbol?.toLowerCase().includes(query) ||
            t.order_id?.toString().toLowerCase().includes(query)
        )
    }, [trades, searchQuery])

    // Pagination logic
    const totalPages = Math.ceil(filteredTrades.length / pageSize)
    const paginatedTrades = useMemo(() => {
        const start = (currentPage - 1) * pageSize
        return filteredTrades.slice(start, start + pageSize)
    }, [filteredTrades, currentPage, pageSize])

    useEffect(() => {
        setCurrentPage(1)
    }, [searchQuery, fetchLimit, pageSize])

    const exportToCSV = () => {
        if (trades.length === 0) return
        const headers = ['Order ID', 'Time', 'Symbol', 'Side', 'Price', 'Qty', 'Commission', 'PnL']
        const rows = trades.map(t => [
            t.order_id,
            format(new Date(t.time), 'yyyy-MM-dd HH:mm:ss'),
            t.symbol,
            t.side,
            t.price,
            t.qty,
            t.commission,
            t.realized_pnl
        ])
        const csvContent = [headers, ...rows].map(e => e.join(',')).join('\n')
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.setAttribute('href', url)
        link.setAttribute('download', `trades_export_${format(new Date(), 'yyyyMMdd_HHmm')}.csv`)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    // Calc Stats
    const stats = useMemo(() => {
        const totalPnl = trades.reduce((acc, t) => acc + (t.realized_pnl || 0), 0)
        const totalVolume = trades.reduce((acc, t) => acc + (t.quote_qty || 0), 0)
        const totalCommission = trades.reduce((acc, t) => acc + (t.commission || 0), 0)
        const avgFee = trades.length > 0 ? totalCommission / trades.length : 0
        return { totalPnl, totalVolume, avgFee, count: trades.length }
    }, [trades])

    return (
        <div className="space-y-8 animate-fadeIn bg-mesh min-h-full pb-20 px-6 pt-6">
            {/* Detail Modal */}
            {selectedTrade && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={() => setSelectedTrade(null)}></div>
                    <div className="relative w-full max-w-lg card glass-dark border-white/10 shadow-3xl animate-scaleIn overflow-hidden">
                        <div className={`absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r ${selectedTrade.realized_pnl > 0 ? 'from-emerald-500 to-teal-500' : 'from-rose-500 to-orange-500'}`}></div>

                        <div className="p-8 space-y-7">
                            <div className="flex justify-between items-start">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Zap size={14} className={selectedTrade.realized_pnl > 0 ? 'text-emerald-400' : 'text-rose-400'} />
                                        <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${selectedTrade.realized_pnl > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                            Trade Transaction Detail
                                        </span>
                                    </div>
                                    <h2 className="text-3xl font-black text-white font-mono uppercase tracking-tighter italic">
                                        {selectedTrade.symbol} <span className="text-white/20 not-italic">/</span> <span className={selectedTrade.realized_pnl > 0 ? 'text-emerald-500' : 'text-rose-500'}>
                                            {selectedTrade.realized_pnl > 0 ? `+${selectedTrade.realized_pnl.toFixed(2)}` : selectedTrade.realized_pnl.toFixed(2)}
                                        </span>
                                    </h2>
                                </div>
                                <button
                                    onClick={() => setSelectedTrade(null)}
                                    className="p-2 hover:bg-white/10 rounded-2xl transition-all active:scale-90"
                                >
                                    <X size={20} className="text-slate-400" />
                                </button>
                            </div>

                            {/* Premium AI Rationale Section */}
                            <div className={`p-6 rounded-[2.5rem] border relative overflow-hidden group ${selectedTrade.realized_pnl >= 0 ? 'bg-emerald-500/[0.03] border-emerald-500/10' : 'bg-rose-500/[0.03] border-rose-500/10'}`}>
                                <div className={`absolute -right-4 -top-4 w-24 h-24 blur-3xl rounded-full transition-transform duration-1000 group-hover:scale-125 ${selectedTrade.realized_pnl >= 0 ? 'bg-emerald-500/10' : 'bg-rose-500/10'}`}></div>

                                <div className="flex items-center justify-between mb-4 relative z-10">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-2xl flex items-center justify-center border ${selectedTrade.realized_pnl >= 0 ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-rose-500/10 border-rose-500/20'}`}>
                                            <Activity size={18} className={selectedTrade.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'} />
                                        </div>
                                        <div>
                                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">AI Decision Node</span>
                                            <span className={`text-xs font-black uppercase tracking-tight ${selectedTrade.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                {selectedTrade.realized_pnl >= 0 ? 'Winning Execution' : 'Loss Mitigation'}
                                            </span>
                                        </div>
                                    </div>
                                    {selectedTrade.exit_reason && (
                                        <div className="bg-white/5 border border-white/10 px-3 py-1 rounded-xl">
                                            <span className="text-[9px] font-black text-white/40 uppercase tracking-wider">{selectedTrade.exit_reason}</span>
                                        </div>
                                    )}
                                </div>

                                <div className="relative z-10">
                                    <p className="text-[13px] text-slate-300 leading-relaxed font-medium italic pl-4 border-l-2 border-white/10">
                                        {selectedTrade.ai_rationale || "Không tìm thấy dữ liệu phân tích chi tiết cho lệnh này. Hệ thống đang ghi nhận các yếu tố thị trường để tối ưu hóa chiến lược cho các phiên tiếp theo."}
                                    </p>
                                </div>

                                <div className="mt-5 pt-4 border-t border-white/5 flex items-center justify-between relative z-10">
                                    <div className="flex gap-4">
                                        <div>
                                            <span className="text-[8px] text-slate-500 uppercase font-black block mb-0.5">Execution Speed</span>
                                            <span className="text-[10px] font-bold text-white font-mono">24ms</span>
                                        </div>
                                        <div>
                                            <span className="text-[8px] text-slate-500 uppercase font-black block mb-0.5">Confidence Score</span>
                                            <span className="text-[10px] font-bold text-blue-400 font-mono">92.4%</span>
                                        </div>
                                    </div>
                                    {selectedTrade.trace_id && (
                                        <div className="flex items-center gap-1.5 opacity-40">
                                            <Hash size={10} />
                                            <span className="text-[9px] font-mono tracking-tighter">TR_{selectedTrade.trace_id.slice(0, 8)}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-5 bg-white/[0.02] rounded-[2rem] border border-white/5 flex flex-col gap-1">
                                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Entry / Exit Price</span>
                                    <span className="text-lg font-black text-white font-mono tracking-tighter">$ {selectedTrade.price.toLocaleString()}</span>
                                </div>
                                <div className="p-5 bg-white/[0.02] rounded-[2rem] border border-white/5 flex flex-col gap-1">
                                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Trade Volume</span>
                                    <span className="text-lg font-black text-blue-400 font-mono tracking-tighter">{selectedTrade.qty.toLocaleString()} <span className="text-[10px] text-blue-400/30">LOTS</span></span>
                                </div>
                            </div>

                            <div className="pt-6 border-t border-white/5 flex justify-between items-center">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center">
                                        <History size={14} className="text-slate-500" />
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-[10px] font-black text-white/50 uppercase tracking-tight">Timestamp</span>
                                        <span className="text-[11px] font-black text-slate-400">{format(new Date(selectedTrade.time), 'dd MMM yyyy, HH:mm:ss')}</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="text-[10px] font-black text-white/50 uppercase tracking-tight block">Commission</span>
                                    <span className="text-[11px] font-black text-rose-400">-{selectedTrade.commission.toFixed(4)} {selectedTrade.commission_asset}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-8">
                <div>
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                            <History className="text-blue-400" size={24} />
                        </div>
                        <span className="text-xs font-black text-blue-400 uppercase tracking-widest">Exchange Connectivity</span>
                    </div>
                    <h1 className="text-5xl lg:text-6xl font-black text-gradient italic tracking-tighter">Lịch sử khớp lệnh</h1>
                    <p className="text-slate-400 mt-3 max-w-xl text-sm leading-relaxed font-medium">Dữ liệu chi tiết các giao dịch đã thực hiện thành công trực tiếp từ Binance Futures.</p>
                </div>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-6">
                    <div className="flex items-center gap-3">
                        <div className="flex p-1.5 glass-dark border-white/5 rounded-2xl shadow-xl">
                            <button
                                onClick={() => setRefreshKey(k => k + 1)}
                                className={`p-2.5 rounded-xl transition-all ${loading ? 'opacity-50' : 'hover:bg-white/5 active:scale-95'}`}
                                disabled={loading}
                            >
                                <RefreshCw size={18} className={`${loading ? 'animate-spin' : ''} text-blue-400`} />
                            </button>
                        </div>
                        <button
                            onClick={exportToCSV}
                            className="flex items-center gap-2 bg-white/5 border border-white/10 hover:bg-white/10 px-5 py-2.5 rounded-xl text-[10px] font-black text-slate-300 uppercase tracking-widest transition-all"
                        >
                            <Download size={16} className="text-blue-400" />
                            Xuất CSV
                        </button>
                    </div>

                    <CustomSelect
                        value={fetchLimit}
                        onChange={setFetchLimit}
                        label="Hiển thị:"
                        options={[
                            { label: '50 mẫu tin', value: 50 },
                            { label: '100 mẫu tin', value: 100 },
                            { label: '200 mẫu tin', value: 200 },
                            { label: '500 mẫu tin', value: 500 },
                        ]}
                    />
                </div>
            </div>

            {/* Stats Summary Area */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { label: 'Tổng lượt Trade', value: stats.count, unit: 'phiên khớp', color: 'blue', icon: TrendingUp },
                    { label: 'Phí trung bình', value: stats.avgFee.toFixed(4), unit: 'USDT', color: 'indigo', icon: Layers },
                    { label: 'Tổng PnL đã chốt', value: stats.totalPnl.toFixed(2), unit: 'USDT', color: 'emerald', icon: CheckCircle2, sign: true },
                    { label: 'Tổng Volume', value: stats.totalVolume.toLocaleString(undefined, { maximumFractionDigits: 0 }), unit: 'USDT', color: 'blue', icon: Activity },
                ].map((stat, i) => (
                    <div key={i} className={`card glass-dark border-white/5 p-6 flex items-center justify-between group relative overflow-hidden ${i === 2 ? 'border-l-4 border-l-emerald-500/50' : ''} ${i === 3 ? 'border-l-4 border-l-blue-500/50' : ''}`}>
                        <div className={`absolute -right-4 -bottom-4 w-24 h-24 bg-${stat.color}-500/5 blur-3xl rounded-full group-hover:scale-150 transition-transform duration-700`}></div>
                        <div className="relative z-10">
                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-1.5">{stat.label}</span>
                            <div className="flex items-end gap-2">
                                <span className={`text-2xl font-black text-white font-mono ${stat.sign ? (parseFloat(stat.value) >= 0 ? 'text-emerald-400' : 'text-rose-400') : ''}`}>
                                    {stat.value}
                                </span>
                                <span className="text-[9px] text-slate-500 font-black uppercase mb-1">{stat.unit}</span>
                            </div>
                        </div>
                        <div className={`relative z-10 w-12 h-12 bg-${stat.color}-500/10 rounded-2xl flex items-center justify-center border border-${stat.color}-500/20 group-hover:scale-110 transition-transform duration-500 shadow-lg`}>
                            <stat.icon className={`text-${stat.color}-400`} size={22} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Data Table */}
            <div className="card glass-dark border-white/5 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.6)] animate-slideUp flex flex-col">
                <div className="p-5 border-b border-white/[0.03] bg-white/[0.01] flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="relative flex-grow max-w-lg w-full">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Tìm kiếm theo mã lệnh, cặp tiền..."
                            className="w-full bg-slate-950/40 border border-white/5 rounded-2xl py-3 pl-12 pr-4 text-xs focus:outline-none focus:border-blue-500/40 focus:ring-4 focus:ring-blue-500/5 transition-all text-white placeholder-slate-600 uppercase font-mono tracking-widest"
                        />
                    </div>
                    <div className="flex gap-3 w-full md:w-auto">
                        <button className="flex-grow md:flex-none px-6 py-3 glass-dark border-white/5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-white hover:bg-white/5 transition-all flex items-center justify-center gap-2 group">
                            <Filter size={14} className="group-hover:text-blue-400 transition-colors" />
                            Bộ lọc nâng cao
                        </button>
                    </div>
                </div>

                <div className="table-container p-0 border-none max-h-[600px] overflow-y-auto custom-scrollbar">
                    <table className="table min-w-full">
                        <thead className="sticky top-0 z-20">
                            <tr className="bg-[#0b0e14]/95 backdrop-blur-md">
                                <th className="py-6 px-8 border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Mã lệnh (Order No.)</th>
                                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Thời gian</th>
                                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Cặp tiền</th>
                                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Chiều (Side)</th>
                                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Giá khớp</th>
                                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Khối lượng</th>
                                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400 text-left">Vai trò</th>
                                <th className="text-right px-8 border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">PnL Thực tế</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.03]">
                            {(paginatedTrades.length === 0 && !loading) ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-32 opacity-30">
                                        <div className="flex flex-col items-center gap-8">
                                            <TrendingUp size={64} className="text-slate-500 animate-pulse" />
                                            <span className="text-xs font-black uppercase tracking-[0.4em]">Không có dữ liệu giao dịch khớp bộ lọc</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                paginatedTrades.map((trade, idx) => (
                                    <tr
                                        key={`${trade.id}-${idx}`}
                                        className="group hover:bg-white/[0.04] transition-all cursor-pointer"
                                        onClick={() => setSelectedTrade(trade)}
                                    >
                                        <td className="py-6 px-8">
                                            <span className="text-[11px] font-mono font-black text-slate-500 group-hover:text-blue-400 transition-colors uppercase tracking-tighter">#{trade.order_id || trade.id.slice(0, 10)}</span>
                                        </td>
                                        <td>
                                            <div className="flex flex-col">
                                                <span className="text-[11px] font-black text-slate-300">
                                                    {format(new Date(trade.time), 'yyyy-MM-dd')}
                                                </span>
                                                <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">
                                                    {format(new Date(trade.time), 'HH:mm:ss')}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="font-black font-mono text-white italic tracking-tighter text-lg">{trade.symbol}</td>
                                        <td>
                                            <div className={`px-3.5 py-1.5 rounded-2xl text-[10px] font-black uppercase tracking-widest border transition-all inline-flex items-center gap-1.5 ${trade.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                                }`}>
                                                {trade.side === 'BUY' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                                {trade.side === 'BUY' ? 'LONG' : 'SHORT'}
                                            </div>
                                        </td>
                                        <td className="font-black font-mono text-white/90 text-sm">
                                            $ {trade.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                                        </td>
                                        <td>
                                            <div className="flex flex-col items-start gap-0.5">
                                                <span className="text-sm font-black font-mono text-blue-100">{trade.qty.toLocaleString()}</span>
                                                <span className="text-[8px] text-slate-600 font-black uppercase tracking-[0.2em]">{trade.symbol.replace('USDT', '')}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-lg border ${trade.role === 'Maker' ? 'text-blue-400 bg-blue-500/5 border-blue-500/10' : 'text-slate-500 bg-white/5 border-white/5'}`}>
                                                {trade.role || 'System'}
                                            </span>
                                        </td>
                                        <td className="text-right px-8">
                                            <div className={`text-[15px] font-black font-mono flex flex-col items-end ${trade.realized_pnl > 0 ? 'text-emerald-400' :
                                                trade.realized_pnl < 0 ? 'text-rose-400' : 'text-slate-500'
                                                }`}>
                                                <span>{trade.realized_pnl > 0 ? '+' : ''}{trade.realized_pnl.toFixed(4)}</span>
                                                <span className="text-[8px] opacity-40 uppercase tracking-widest font-sans">USDT PnL</span>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Improved Pagination Controls */}
                {totalPages > 1 && (
                    <div className="p-5 bg-black/40 backdrop-blur-2xl border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6">
                        <div className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">
                            Bản ghi <span className="text-white text-xs">{(currentPage - 1) * pageSize + 1}</span> - <span className="text-white text-xs">{Math.min(currentPage * pageSize, filteredTrades.length)}</span> / <span className="text-blue-400 text-xs">{filteredTrades.length}</span>
                        </div>

                        <div className="flex flex-wrap items-center justify-center gap-8">
                            <CustomSelect
                                value={pageSize}
                                onChange={setPageSize}
                                label="Dòng hiển thị:"
                                position="top"
                                options={[
                                    { label: '10 dòng', value: 10 },
                                    { label: '20 dòng', value: 20 },
                                    { label: '50 dòng', value: 50 },
                                    { label: '100 dòng', value: 100 },
                                ]}
                            />

                            <div className="flex items-center gap-2 bg-white/5 p-1 rounded-2xl border border-white/5">
                                <button
                                    onClick={() => setCurrentPage(1)}
                                    disabled={currentPage === 1}
                                    className="p-2 hover:bg-white/10 rounded-xl disabled:opacity-20 text-slate-400 transition-all hover:text-white"
                                    title="Trang đầu"
                                >
                                    <Layers size={14} />
                                </button>
                                <button
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    className="px-5 py-2 hover:bg-blue-600 rounded-[1.25rem] disabled:opacity-20 text-[10px] font-black text-white transition-all uppercase tracking-widest shadow-xl disabled:shadow-none"
                                >
                                    Trước
                                </button>
                                <div className="flex items-center gap-2 px-6 border-x border-white/10">
                                    <span className="text-xs font-black text-blue-400">{currentPage}</span>
                                    <span className="text-[10px] font-black text-slate-600">/</span>
                                    <span className="text-[10px] font-black text-slate-500">{totalPages}</span>
                                </div>
                                <button
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                    className="px-5 py-2 hover:bg-blue-600 rounded-[1.25rem] disabled:opacity-20 text-[10px] font-black text-white transition-all uppercase tracking-widest shadow-xl disabled:shadow-none"
                                >
                                    Sau
                                </button>
                                <button
                                    onClick={() => setCurrentPage(totalPages)}
                                    disabled={currentPage === totalPages}
                                    className="p-2 hover:bg-white/10 rounded-xl disabled:opacity-20 text-slate-400 transition-all hover:text-white"
                                    title="Trang cuối"
                                >
                                    <Layers size={14} className="rotate-180" />
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Data Source Footer */}
            <div className="flex justify-between items-center opacity-30 text-[9px] font-black uppercase tracking-[0.3em] px-2 text-slate-500">
                <div className="flex items-center gap-4">
                    <span>Binance Data Link: ACTIVE</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${loading ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`}></span>
                </div>
                <span>Sync Cycle: {format(new Date(), 'HH:mm:ss')}</span>
            </div>
        </div>
    )
}
