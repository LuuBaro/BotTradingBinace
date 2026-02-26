import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboardStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { formatDistanceToNow } from 'date-fns'
import { Activity, TrendingUp, TrendingDown, Zap, Clock, X, Edit3, Share2, Anchor, RefreshCw, Brain, Grid, Layout } from 'lucide-react'

export const PositionsPage: React.FC = () => {
  const navigate = useNavigate()
  const { positions, setPositions, orders, setOrders } = useDashboardStore()
  const [loading, setLoading] = useState(true)
  const [refreshKey, setRefreshKey] = useState(0)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [formData, setFormData] = useState({ symbol: 'BTCUSDT', side: 'LONG', leverage: 10, size_pct: 1 })
  const [submitting, setSubmitting] = useState(false)

  // Memoized API client
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  const fetchData = async () => {
    try {
      const [posResponse, ordResponse] = await Promise.all([
        api.getPositions(),
        api.getOrders()
      ])
      setPositions(Array.isArray(posResponse) ? posResponse : [])
      setOrders(Array.isArray(ordResponse) ? ordResponse : [])
    } catch (error) {
      console.error('Failed to sync positions/orders:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleManualTrade = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.openPosition(formData)
      alert('Lệnh đã được gửi thành công!')
      setIsModalOpen(false)
      fetchData()
    } catch (error) {
      console.error('Lỗi khi đặt lệnh:', error)
      alert('Không thể đặt lệnh. Vui lòng kiểm tra lại cấu hình.')
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [api, setPositions, setOrders, refreshKey])

  const totalPnL = positions.reduce((acc, p) => acc + (p.unrealized_pnl || 0), 0)

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Manual Trade Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-[#020617]/80 backdrop-blur-md" onClick={() => setIsModalOpen(false)}></div>
          <div className="card glass-dark w-full max-w-md relative z-10 border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] p-8 animate-slideUp">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-black text-white">Mở vị thế thủ công</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-500 hover:text-white"><X size={24} /></button>
            </div>
            <form onSubmit={handleManualTrade} className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Cặp giao dịch (Symbol)</label>
                <input
                  type="text"
                  value={formData.symbol}
                  onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-white font-mono focus:border-blue-500 outline-none transition-colors"
                  placeholder="BTCUSDT"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Vị thế (Side)</label>
                  <select
                    value={formData.side}
                    onChange={(e) => setFormData({ ...formData, side: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-white outline-none focus:border-blue-500 transition-colors cursor-pointer"
                  >
                    <option value="LONG" className="bg-[#0f172a]">LONG</option>
                    <option value="SHORT" className="bg-[#0f172a]">SHORT</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Đòn bẩy (x)</label>
                  <input
                    type="number"
                    value={formData.leverage}
                    onChange={(e) => setFormData({ ...formData, leverage: parseInt(e.target.value) })}
                    className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-white font-mono outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Khối lượng (% Tài khoản)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={formData.size_pct}
                    onChange={(e) => setFormData({ ...formData, size_pct: parseInt(e.target.value) })}
                    className="flex-grow h-1.5 bg-white/5 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <span className="text-xl font-mono font-black text-blue-400 min-w-[3rem]">{formData.size_pct}%</span>
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting}
                className={`w-full btn btn-primary py-5 rounded-2xl mt-4 flex items-center justify-center gap-3 ${submitting ? 'opacity-50' : ''}`}
              >
                {submitting ? <RefreshCw className="animate-spin" /> : <Zap size={18} />}
                <span className="font-black uppercase tracking-widest">Thực thi lệnh ngay</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Activity className="text-blue-400" size={24} />
            </div>
            <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Vị thế đang hoạt động</span>
          </div>
          <h1 className="text-5xl font-black text-gradient">Positions</h1>
          <p className="text-slate-400 mt-2 max-w-xl">Theo dõi và quản lý dữ liệu thời gian thực các vị thế đang mở trên sàn giao dịch.</p>
        </div>

        <div className="flex gap-4">
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn btn-primary self-center px-6 py-4 rounded-3xl flex items-center gap-3"
          >
            <Zap size={18} />
            <span className="text-[10px] font-black uppercase tracking-widest">Mở vị thế</span>
          </button>
          <div className="glass-dark px-6 py-4 rounded-3xl border border-white/5 shadow-2xl">
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-1">Số lượng vị thế</span>
            <span className="text-2xl font-black text-white font-mono">{positions.length}</span>
          </div>
          <div className={`glass-dark px-6 py-4 rounded-3xl border border-white/5 shadow-2xl relative overflow-hidden group`}>
            <div className="relative z-10">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-1">Tổng Alpha (PnL)</span>
              <span className={`text-2xl font-black font-mono ${totalPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(2)}
              </span>
            </div>
            <div className={`absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity ${totalPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {totalPnL >= 0 ? <TrendingUp size={60} /> : <TrendingDown size={60} />}
            </div>
          </div>
          <div className="flex bg-white/5 p-1 rounded-2xl border border-white/5">
            <button
              onClick={() => setViewMode('table')}
              className={`p-3 rounded-xl transition-all ${viewMode === 'table' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-500 hover:text-white'}`}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setViewMode('card')}
              className={`p-3 rounded-xl transition-all ${viewMode === 'card' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-500 hover:text-white'}`}
            >
              <Layout size={18} />
            </button>
          </div>
          <button
            onClick={() => setRefreshKey(k => k + 1)}
            className="btn btn-secondary group self-center p-4 rounded-3xl"
          >
            <RefreshCw size={20} className="group-hover:rotate-180 transition-transform duration-700" />
          </button>
        </div>
      </div>

      {loading && positions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-40 gap-6 opacity-50">
          <div className="spinner w-12 h-12"></div>
          <p className="text-xs font-black uppercase tracking-[0.3em] text-blue-400 animate-pulse">Đang đồng bộ dữ liệu với Binance...</p>
        </div>
      ) : positions.length === 0 ? (
        <div className="card glass-dark border-white/5 py-32 flex flex-col items-center justify-center gap-6 animate-slideUp">
          <div className="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center border border-white/5 relative">
            <Anchor size={40} className="text-slate-500" />
            <div className="absolute inset-0 border-2 border-dashed border-slate-700 rounded-full animate-spin-slow"></div>
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-black text-white">Không có vị thế nào đang mở</h3>
            <p className="text-slate-500 max-w-sm mx-auto">Hệ thống AI đang quét thanh khoản thị trường để tìm điểm vào lệnh tối ưu. Hiện đang ở chế độ chờ (Standby).</p>
          </div>
          <button className="btn btn-primary mt-4">
            <Zap size={16} />
            Quét thủ công
          </button>
        </div>
      ) : viewMode === 'table' ? (
        /* Premium Table View */
        <div className="card glass-dark border-white/5 overflow-hidden animate-slideUp">
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/[0.02] border-b border-white/5">
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">Symbol</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">Size</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">Entry Price</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">Mark Price</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">Liq. Price</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">Margin</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">PNL (ROI %)</th>
                  <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-500 tracking-[0.2em] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {positions.map((pos) => {
                  const pnl = pos.unrealized_pnl || 0
                  const isProfit = pnl >= 0
                  const leverage = pos.leverage || 1
                  const margin = (pos.entry_price * pos.qty) / leverage

                  // Correct ROI calculation for Futures
                  const pnlPercent = ((pnl / margin) * 100).toFixed(2)

                  const currentPrice = pos.side === 'long'
                    ? pos.entry_price + (pnl / pos.qty)
                    : pos.entry_price - (pnl / pos.qty)

                  return (
                    <tr key={pos.id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-6 py-6">
                        <div className="flex flex-col">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-black text-white font-mono">{pos.symbol}</span>
                            <span className={`text-[8px] px-1.5 py-0.5 rounded font-black uppercase ${pos.side.toLowerCase() === 'long' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                              Perp {leverage}x
                            </span>
                          </div>
                          <span className={`text-[9px] font-bold ${pos.side.toLowerCase() === 'long' ? 'text-emerald-500' : 'text-rose-500'} uppercase mt-1`}>
                            {pos.side.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-6">
                        <div className="flex flex-col">
                          <span className={`text-sm font-mono font-black ${pos.side.toLowerCase() === 'long' ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {pos.side.toLowerCase() === 'long' ? '+' : '-'}{pos.qty.toLocaleString(undefined, { minimumFractionDigits: 3 })}
                          </span>
                          <span className="text-[9px] font-bold text-slate-600 uppercase">{pos.symbol.replace('USDT', '')}</span>
                        </div>
                      </td>
                      <td className="px-6 py-6">
                        <span className="text-sm font-mono font-bold text-slate-300">{pos.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                      </td>
                      <td className="px-6 py-6">
                        <span className="text-sm font-mono font-bold text-blue-400">{currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                      </td>
                      <td className="px-6 py-6">
                        <span className="text-sm font-mono font-bold text-amber-500/80">
                          {pos.liquidation_price ? pos.liquidation_price.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '--'}
                        </span>
                      </td>
                      <td className="px-6 py-6">
                        <div className="flex flex-col">
                          <span className="text-sm font-mono font-bold text-slate-300">{margin.toLocaleString(undefined, { minimumFractionDigits: 2 })} USDT</span>
                          <span className="text-[9px] font-bold text-slate-600 uppercase">{pos.margin_type || 'Cross'}</span>
                        </div>
                      </td>
                      <td className="px-6 py-6">
                        <div className="flex flex-col">
                          <span className={`text-sm font-mono font-black ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isProfit ? '+' : ''}${pnl.toFixed(2)}
                          </span>
                          <span className={`text-[10px] font-black ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {isProfit ? '+' : ''}{pnlPercent}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-6 text-right">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={async () => {
                              if (confirm(`Bạn có chắc chắn muốn Đóng vị thế (Close Position) ${pos.symbol} ngay lập tức không?`)) {
                                try {
                                  await api.closePosition(pos.symbol)
                                  alert(`Đã gửi yêu cầu đóng vị thế ${pos.symbol}`)
                                  fetchData()
                                } catch (e) {
                                  console.error(e)
                                  alert('Lỗi khi đóng vị thế!')
                                }
                              }
                            }}
                            className="px-4 py-2 bg-rose-500/10 text-rose-500 hover:bg-rose-500 hover:text-white rounded-xl transition-all font-black text-[10px] uppercase tracking-widest border border-rose-500/20"
                          >
                            Close
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Existing Card Grid (Original View) */
        <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-8">
          {positions.map((pos) => {
            const pnl = pos.unrealized_pnl || 0
            const isProfit = pnl >= 0
            const margin = (pos.entry_price * pos.qty / (pos.leverage || 1))
            const pnlPercent = ((pnl / (margin || 1)) * 100).toFixed(2)
            const currentPrice = pos.side === 'long'
              ? pos.entry_price + (pnl / pos.qty)
              : pos.entry_price - (pnl / pos.qty)

            return (
              <div key={pos.id} className="card glass-dark border-white/10 group hover:border-blue-500/30 transition-all duration-500 relative overflow-hidden flex flex-col h-full">
                {/* ... existing card content ... */}
                {/* Visual Accent */}
                <div className={`absolute top-0 left-0 w-full h-1.5 ${isProfit ? 'bg-gradient-to-r from-emerald-500 to-teal-500' : 'bg-gradient-to-r from-rose-500 to-orange-500'} opacity-50 group-hover:opacity-100 transition-opacity`}></div>

                <div className="p-8 space-y-8 flex-grow">
                  {/* Header Information */}
                  <div className="flex justify-between items-start">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <h2 className="text-3xl font-black font-mono tracking-tighter text-white">{pos.symbol}</h2>
                        <div className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-widest ${pos.side === 'long' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                          {pos.side} {pos.leverage}x
                        </div>
                      </div>
                      <div className="flex items-center gap-2 opacity-50">
                        <Clock size={12} className="text-slate-400" />
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                          {formatDistanceToNow(new Date(pos.opened_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className={`text-3xl font-black font-mono tracking-tighter ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isProfit ? '+' : ''}${pnl.toFixed(2)}
                      </div>
                      <div className={`flex items-center justify-end gap-1 text-[11px] font-black ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {isProfit ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                        {pnlPercent}%
                      </div>
                    </div>
                  </div>

                  {/* Telemetry Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-white/[0.03] rounded-2xl border border-white/5 group-hover:bg-white/[0.05] transition-colors relative">
                      <span className="text-[9px] text-slate-500 font-black uppercase tracking-[0.2em] block mb-2">Giá hiện tại (Mark Price)</span>
                      <div className="flex flex-col">
                        <span className="text-lg font-mono font-black text-blue-400">${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        <span className="text-[9px] text-slate-600 font-bold uppercase tracking-tighter">Live Telemetry</span>
                      </div>
                    </div>
                    <div className="p-4 bg-white/[0.03] rounded-2xl border border-white/5 group-hover:bg-white/[0.05] transition-colors">
                      <span className="text-[9px] text-slate-500 font-black uppercase tracking-[0.2em] block mb-2">Deployed Vol (Khối lượng)</span>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-1">
                          <span className="text-lg font-mono font-black text-white">{pos.qty.toLocaleString()}</span>
                          <span className="text-[10px] text-slate-500 font-bold uppercase">{pos.symbol.replace('USDT', '')}</span>
                        </div>
                        <span className="text-[9px] text-slate-600 font-bold uppercase text-gradient">Entry: ${pos.entry_price.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* AI Insights & Rationale */}
                  <div className="p-5 bg-gradient-to-br from-indigo-500/5 to-blue-500/5 rounded-2xl border border-blue-500/10 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Brain size={14} className="text-blue-400" />
                        <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Neural Rationale (Phân tích AI)</span>
                      </div>
                      <span className="text-[9px] font-mono text-slate-500">CONF: {((pos as any).confidence * 100 || 85).toFixed(0)}%</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed italic line-clamp-3">
                      "{(pos as any).rationale || 'Thị trường đang duy trì đà tăng trưởng trên các cụm hỗ trợ cục bộ. Hồ sơ Delta cho thấy áp lực bán đang được hấp thụ với biến động mở rộng.'}"
                    </p>
                    <div className="flex gap-2">
                      <span className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 rounded text-[8px] font-bold text-blue-400 uppercase">
                        TRẠNG THÁI: {(pos as any).regime || 'XU HƯỚNG TĂNG'}
                      </span>
                      <span className="px-2 py-0.5 bg-purple-500/10 border border-purple-500/20 rounded text-[8px] font-bold text-purple-400 uppercase">
                        Hệ thống: Đang hoạt động
                      </span>
                    </div>
                  </div>

                  {/* Position Value & Leverage Summary */}
                  <div className="p-5 bg-blue-500/5 rounded-2xl border border-blue-500/10 flex justify-between items-center group-hover:bg-blue-500/10 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="p-2.5 bg-blue-500/20 rounded-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">
                        <Zap size={18} className="text-blue-400" />
                      </div>
                      <div>
                        <span className="text-[9px] text-blue-400 font-black uppercase tracking-widest block">Giá trị hiện tại (Market Value)</span>
                        <span className="text-xl font-mono font-black text-white italic tracking-tighter">${((pos.entry_price * pos.qty) + pos.unrealized_pnl).toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 })}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest block">Margin Utilized (Ký quỹ)</span>
                      <span className="text-sm font-black text-slate-300">{margin.toLocaleString()} USDT</span>
                    </div>
                  </div>

                  {/* Visual Target Bar */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-[8px] font-black uppercase tracking-tighter">
                      <span className="text-rose-500">Stop Loss</span>
                      <span className="text-slate-500">Tiến độ mục tiêu (Target Path)</span>
                      <span className="text-emerald-500">Take Profit</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden flex relative">
                      {/* Current progress relative to TP/SL */}
                      {pos.stop_loss && pos.take_profit ? (
                        <div
                          className={`h-full transition-all duration-1000 ${isProfit ? 'bg-emerald-500' : 'bg-rose-500'}`}
                          style={{
                            width: `${Math.min(100, Math.max(0,
                              pos.side === 'long'
                                ? ((currentPrice - pos.stop_loss) / (pos.take_profit - pos.stop_loss) * 100)
                                : ((pos.stop_loss - currentPrice) / (pos.stop_loss - pos.take_profit) * 100)
                            ))}%`
                          }}
                        ></div>
                      ) : (
                        <div className="h-full bg-blue-500/20 w-1/2 mx-auto"></div>
                      )}
                      {/* Central Entry Mark */}
                      <div className="absolute left-[50%] top-0 w-0.5 h-full bg-white/40"></div>
                    </div>
                  </div>

                  {/* Risk Barriers */}
                  <div className="space-y-3 pt-2">
                    <div className="flex gap-3">
                      <div className="flex-1 p-3 bg-white/5 border border-white/5 rounded-xl text-center">
                        <span className="text-[8px] text-slate-600 block mb-1 uppercase font-black">SL (Cắt lỗ)</span>
                        <span className="text-xs font-mono font-black text-rose-500/80">{pos.stop_loss ? `$${pos.stop_loss.toLocaleString()}` : 'CHƯA THIẾT LẬP'}</span>
                      </div>
                      <div className="flex-1 p-3 bg-white/5 border border-white/5 rounded-xl text-center">
                        <span className="text-[8px] text-slate-600 block mb-1 uppercase font-black">TP (Chốt lời)</span>
                        <span className="text-xs font-mono font-black text-emerald-500/80">{pos.take_profit ? `$${pos.take_profit.toLocaleString()}` : 'CHƯA THIẾT LẬP'}</span>
                      </div>
                    </div>
                  </div>
                  {/* Recent Orders for this Symbol */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center px-1">
                      <span className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Lịch sử khớp lệnh (Execution Stack)</span>
                      <button
                        onClick={() => navigate('/orders')}
                        className="text-[9px] font-black text-blue-400 hover:text-white uppercase tracking-tighter"
                      >
                        Xem tất cả →
                      </button>
                    </div>
                    <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">
                      {/* Filter orders for this symbol, take top 2 */}
                      {orders
                        .filter(o => o.symbol === pos.symbol)
                        .slice(0, 2)
                        .map(order => (
                          <div key={order.id} className="p-3 bg-white/[0.02] border border-white/5 rounded-xl flex items-center justify-between group/order hover:bg-white/5 transition-colors">
                            <div className="flex items-center gap-3">
                              <div className={`w-1 h-1 rounded-full ${order.status === 'FILLED' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 'bg-amber-500'}`}></div>
                              <div className="flex flex-col">
                                <span className="text-[10px] font-black text-white">{order.side} {order.quantity.toFixed(4)}</span>
                                <span className="text-[8px] font-mono text-slate-600 uppercase tracking-tighter">{order.status}</span>
                              </div>
                            </div>
                            <span className="text-[9px] font-mono text-slate-500">{formatDistanceToNow(new Date(order.created_at), { addSuffix: true })}</span>
                          </div>
                        ))
                      }
                      {orders.filter(o => o.symbol === pos.symbol).length === 0 && (
                        <div className="p-4 rounded-xl border border-dashed border-white/5 text-center opacity-30">
                          <span className="text-[8px] font-black uppercase tracking-widest">Không có dữ liệu khớp lệnh nào được ghi nhận</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Management Hub */}
                <div className="p-6 bg-white/[0.02] border-t border-white/5 flex gap-3">
                  <button
                    className="flex-grow btn btn-secondary group border-white/5 py-4 rounded-2xl flex items-center justify-center gap-3"
                    onClick={() => navigate('/settings')}
                  >
                    <Edit3 size={16} className="text-slate-400 group-hover:text-white" />
                    <span className="text-xs">Điều chỉnh cấu hình</span>
                  </button>
                  <button
                    className="btn btn-secondary p-4 rounded-2xl border-white/5"
                    title="Export Strategy Trace"
                    onClick={() => {
                      navigate('/trades')
                    }}
                  >
                    <Share2 size={16} className="text-slate-400 hover:text-white" />
                  </button>
                  <button
                    className="btn border-rose-500/20 bg-rose-500/10 text-rose-500 hover:bg-rose-500 hover:text-white p-4 rounded-2xl group transition-all"
                    onClick={async () => {
                      if (confirm(`Bạn có chắc chắn muốn Đóng vị thế (Close Position) ${pos.symbol} không?`)) {
                        try {
                          await api.closePosition(pos.symbol)
                          alert(`Close request sent for ${pos.symbol}`)
                          setRefreshKey(k => k + 1)
                        } catch (error) {
                          console.error('Failed to close position:', error)
                          alert('Failed to close position')
                        }
                      }
                    }}
                  >
                    <X size={16} className="group-hover:rotate-90 transition-transform" />
                  </button>
                </div>

                {/* Background Decoration */}
                <div className="absolute top-0 right-0 p-8 opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none">
                  <Activity size={180} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
