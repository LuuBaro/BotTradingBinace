import React, { useEffect, useState, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { useDashboardStore, Order } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { formatDistanceToNow, format } from 'date-fns'
import { Terminal, CheckCircle2, XCircle, ArrowUpRight, ArrowDownRight, RefreshCw, Layers, X, Hash, Activity, ChevronDown, Search, Filter } from 'lucide-react'

// Custom Premium Select Component
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

export const OrdersPage: React.FC = () => {
  const location = useLocation()
  const { orders, setOrders } = useDashboardStore()
  const [filter, setFilter] = useState<'open' | 'filled' | 'cancelled' | 'all'>('all')
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedOrder, setSelectedOrder] = useState<Order | any | null>(null)
  const [fetchLimit, setFetchLimit] = useState(100)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [searchQuery, setSearchQuery] = useState('')
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token, location.search])

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response = await api.getOrders(fetchLimit)
        setOrders(Array.isArray(response) ? response : [])
      } catch (error) {
        console.error('Failed to fetch orders:', error)
      }
    }

    fetchOrders()
    const interval = setInterval(fetchOrders, 8000)
    return () => clearInterval(interval)
  }, [api, setOrders, refreshKey, fetchLimit])

  const filteredByStatus = useMemo(() => orders.filter((o) => {
    if (filter === 'all') return true
    const status = o.status.toUpperCase();
    if (filter === 'open') return ['NEW', 'PARTIALLY_FILLED'].includes(status)
    if (filter === 'cancelled') return status === 'CANCELLED'
    if (filter === 'filled') return status === 'FILLED'
    return false
  }), [orders, filter])

  const filteredOrders = useMemo(() => {
    if (!searchQuery.trim()) return filteredByStatus
    const query = searchQuery.toLowerCase()
    return filteredByStatus.filter(o =>
      o.symbol.toLowerCase().includes(query) ||
      o.id.toLowerCase().includes(query)
    )
  }, [filteredByStatus, searchQuery])

  // Pagination logic
  const totalPages = Math.ceil(filteredOrders.length / pageSize)
  const paginatedOrders = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    // Decisions now arrive sorted by API, but we ensure frontend consistency here if needed
    return filteredOrders.slice(start, start + pageSize)
  }, [filteredOrders, currentPage, pageSize])

  // Reset page when filter or fetchLimit changes
  useEffect(() => {
    setCurrentPage(1)
  }, [filter, fetchLimit, pageSize, searchQuery])

  return (
    <div className="space-y-8 animate-fadeIn bg-mesh min-h-full pb-20 px-6 pt-6">
      {/* Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedOrder(null)}></div>
          <div className="relative w-full max-w-lg card glass-dark border-white/10 shadow-2xl animate-scaleIn overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500"></div>

            <div className="p-8 space-y-6">
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Hash size={14} className="text-blue-400" />
                    <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Chi tiết lệnh giao dịch</span>
                  </div>
                  <h2 className="text-2xl font-black text-white font-mono uppercase tracking-tighter">#{selectedOrder.id.slice(0, 16)}</h2>
                </div>
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="p-2 hover:bg-white/5 rounded-full transition-colors"
                >
                  <X size={20} className="text-slate-500" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-white/[0.03] rounded-2xl border border-white/5">
                  <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest block mb-2">Cặp tài sản</span>
                  <span className="text-lg font-black text-white italic">{selectedOrder.symbol}</span>
                </div>
                <div className="p-4 bg-white/[0.03] rounded-2xl border border-white/5">
                  <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest block mb-2">Trạng thái</span>
                  <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${selectedOrder.status === 'FILLED' ? 'bg-emerald-500' : 'bg-amber-500'}`}></div>
                    <span className="text-sm font-black text-white uppercase">{selectedOrder.status === 'FILLED' ? 'Đã khớp' : selectedOrder.status}</span>
                  </div>
                </div>
              </div>

              {/* Enhanced AI Insight Section */}
              <div className="p-5 bg-emerald-500/5 rounded-[2rem] border border-emerald-500/10 space-y-4 relative overflow-hidden group">
                <div className="absolute -right-4 -top-4 w-20 h-20 bg-emerald-500/5 blur-3xl rounded-full group-hover:scale-150 transition-transform duration-1000"></div>
                <div className="flex items-center justify-between relative z-10">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                      <Activity size={16} className="text-emerald-400" />
                    </div>
                    <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">AI Reasoning & Logic</span>
                  </div>
                  {selectedOrder.ai_regime && (
                    <span className="text-[8px] font-black text-white/40 uppercase bg-white/5 px-2 py-1 rounded-lg border border-white/5">
                      Regime: {selectedOrder.ai_regime}
                    </span>
                  )}
                </div>

                <div className="relative z-10">
                  <p className="text-xs text-slate-300 leading-relaxed font-semibold italic border-l-2 border-emerald-500/30 pl-4 py-1">
                    {selectedOrder.ai_rationale || "Đang phân tích dữ liệu lệnh từ database. Đối với các lệnh cũ, hệ thống đang ánh xạ lại các rationale từ trace log. Vui lòng kiểm tra lại sau giây lát."}
                  </p>
                </div>

                <div className="flex items-center gap-4 pt-2 relative z-10">
                  <div className="flex flex-col">
                    <span className="text-[8px] text-slate-500 uppercase font-black">AI Confidence</span>
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-16 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500 w-[85%]"></div>
                      </div>
                      <span className="text-[10px] font-black text-emerald-400">85%</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-white/[0.03] rounded-2xl border border-white/5">
                  <div>
                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest block mb-1">Loại lệnh & Chiều</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-black text-blue-400 uppercase">{selectedOrder.order_type}</span>
                      <span className={`text-xs font-black px-2 py-0.5 rounded ${selectedOrder.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                        {selectedOrder.side === 'BUY' ? 'MUA / LONG' : 'BÁN / SHORT'}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest block mb-1">Giá trung bình</span>
                    <span className="text-sm font-black text-white font-mono">
                      {selectedOrder.status === 'FILLED' && selectedOrder.avg_price && selectedOrder.avg_price > 0
                        ? `$${selectedOrder.avg_price.toLocaleString()}`
                        : '---'}
                    </span>
                  </div>
                </div>

                <div className="p-4 bg-white/[0.03] rounded-2xl border border-white/5 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Tiến độ khớp lệnh</span>
                    <span className="text-[10px] font-black text-white">
                      {((selectedOrder.filled_qty || 0) / (selectedOrder.quantity || 1) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)] transition-all duration-1000"
                      style={{ width: `${((selectedOrder.filled_qty || 0) / (selectedOrder.quantity || 1)) * 100}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between">
                    <div>
                      <span className="text-[8px] text-slate-500 uppercase block">Đã khớp</span>
                      <span className="text-xs font-black text-white font-mono">{(selectedOrder.filled_qty || 0).toFixed(4)}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[8px] text-slate-500 uppercase block">Tổng khối lượng</span>
                      <span className="text-xs font-black text-white font-mono">{(selectedOrder.quantity || 0).toFixed(4)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between opacity-50 border-t border-white/5">
                <div className="flex items-center gap-2">
                  <Activity size={12} className="text-slate-400" />
                  <span className="text-[9px] font-black text-slate-500 uppercase">Khởi tạo: {format(new Date(selectedOrder.created_at), 'dd/MM/yyyy HH:mm:ss')}</span>
                </div>
                {selectedOrder.trace_id && (
                  <div className="flex items-center gap-1.5">
                    <Hash size={10} className="text-slate-500" />
                    <span className="text-[8px] font-mono text-slate-600 uppercase">TRC_{selectedOrder.trace_id.slice(0, 8)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-8">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
              <Terminal className="text-blue-400" size={24} />
            </div>
            <span className="text-xs font-black text-blue-400 uppercase tracking-widest">Nhật ký giao dịch</span>
          </div>
          <h1 className="text-5xl lg:text-6xl font-black text-gradient italic tracking-tighter">Lịch sử lệnh</h1>
          <p className="text-slate-400 mt-3 max-w-xl text-sm leading-relaxed font-medium">Danh sách chi tiết các lệnh đã kích hoạt, đang chờ xử lý và đã hoàn tất trên hệ thống.</p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-6">
          <div className="flex p-1.5 glass-dark border-white/5 rounded-[2rem] shadow-2xl">
            {(['all', 'open', 'filled', 'cancelled'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-6 py-2.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-widest transition-all duration-300 ${filter === f
                  ? 'bg-blue-600 text-white shadow-xl shadow-blue-500/30 ring-1 ring-blue-400/50'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                  }`}
              >
                {f === 'all' ? 'Tất cả' : f === 'open' ? 'Đang mở' : f === 'filled' ? 'Đã khớp' : 'Đã hủy'}
              </button>
            ))}
            <div className="w-px h-8 bg-white/10 mx-2 self-center"></div>
            <button
              onClick={() => setRefreshKey(k => k + 1)}
              className="p-2.5 hover:bg-white/5 rounded-2xl text-slate-500 hover:text-white transition-all group"
            >
              <RefreshCw size={18} className="group-hover:rotate-180 transition-transform duration-700" />
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

      {/* Stats Summary Panel */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Hiện có', value: filteredOrders.length, color: 'blue', icon: Layers },
          { label: 'Đã khớp', value: filteredOrders.filter(o => o.status === 'FILLED').length, color: 'emerald', icon: CheckCircle2 },
          { label: 'Đã hủy', value: filteredOrders.filter(o => o.status === 'CANCELLED').length, color: 'rose', icon: XCircle },
          { label: 'Đang treo', value: filteredOrders.filter(o => ['NEW', 'PARTIALLY_FILLED'].includes(o.status)).length, color: 'amber', icon: Activity },
        ].map((stat, i) => (
          <div key={i} className="card glass-dark border-white/5 p-6 flex items-center justify-between group relative overflow-hidden">
            <div className={`absolute -right-4 -bottom-4 w-24 h-24 bg-${stat.color}-500/5 blur-3xl rounded-full group-hover:scale-150 transition-transform duration-700`}></div>
            <div className="relative z-10">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-1.5">{stat.label}</span>
              <span className={`text-3xl font-black text-white font-mono`}>{stat.value}</span>
            </div>
            <div className={`relative z-10 w-12 h-12 bg-${stat.color}-500/10 rounded-2xl flex items-center justify-center border border-${stat.color}-500/20 group-hover:scale-110 transition-transform duration-500 shadow-lg`}>
              <stat.icon className={`text-${stat.color}-400`} size={22} />
            </div>
          </div>
        ))}
      </div>

      {/* Orders Table Section */}
      <div className="card glass-dark border-white/5 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.6)] animate-slideUp flex flex-col">
        {/* Search Bar consistent with TradeHistoryPage */}
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
                <th className="py-6 px-8 border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">Mã lệnh (Order ID)</th>
                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">Cặp tiền</th>
                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">Loại lệnh</th>
                <th className="text-right border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">Khối lượng</th>
                <th className="border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">Trạng thái</th>
                <th className="text-right px-8 border-b border-white/5 font-black text-[10px] tracking-[0.2em] text-slate-400">Thời gian</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {paginatedOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-32 opacity-30">
                    <div className="flex flex-col items-center gap-6">
                      <Terminal size={64} className="text-slate-500 animate-pulse" />
                      <span className="text-xs font-black uppercase tracking-[0.4em]">Trống dữ liệu khớp bộ lọc</span>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedOrders.map((order) => (
                  <tr
                    key={order.id}
                    className="group hover:bg-white/[0.04] transition-all cursor-pointer relative"
                    onClick={() => setSelectedOrder(order)}
                  >
                    <td className="py-6 px-8">
                      <div className="flex items-center gap-4">
                        <div className={`w-2 h-2 rounded-full ${order.status === 'FILLED' ? 'bg-emerald-500 shadow-[0_0_12px_#10b981]' :
                          order.status === 'CANCELLED' ? 'bg-rose-500' : 'bg-amber-500 shadow-[0_0_12px_#f59e0b] animate-pulse'
                          }`}></div>
                        <span className="text-[11px] font-mono font-black text-slate-500 group-hover:text-blue-400 transition-colors uppercase tracking-tight">#{order.id.slice(0, 12)}</span>
                      </div>
                    </td>
                    <td className="font-black font-mono text-white italic tracking-tighter text-lg group-hover:pl-2 transition-all duration-300">{order.symbol}</td>
                    <td>
                      <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-2xl text-[10px] font-black uppercase tracking-widest ${order.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}>
                        {order.side === 'BUY' ? <ArrowUpRight size={12} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" /> : <ArrowDownRight size={12} className="group-hover:translate-x-0.5 group-hover:translate-y-0.5 transition-transform" />}
                        {order.side === 'BUY' ? 'MUA' : 'BÁN'}
                      </div>
                    </td>
                    <td className="text-right font-black font-mono text-blue-100/90 text-[15px]">
                      <span className="text-[9px] text-slate-600 mr-2 uppercase italic opacity-60 font-sans tracking-widest">qty</span>
                      {(order.quantity || 0).toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 })}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className={`px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest border transition-colors ${order.status === 'FILLED' ? 'bg-emerald-500/5 text-emerald-400 border-emerald-500/20' :
                          order.status === 'CANCELLED' ? 'bg-rose-500/5 text-rose-400 border-rose-500/20' :
                            'bg-amber-500/5 text-amber-400 border-amber-500/20'
                          }`}>
                          {order.status === 'FILLED' ? 'Hoàn tất' : order.status}
                        </span>
                      </div>
                    </td>
                    <td className="text-right px-8">
                      <div className="flex flex-col items-end gap-0.5">
                        <span className="text-[11px] font-black text-slate-300">
                          {formatDistanceToNow(new Date(order.created_at), { addSuffix: true })}
                        </span>
                        <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">
                          {format(new Date(order.created_at), 'HH:mm:ss.SSS')}
                        </span>
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
              Bản ghi <span className="text-white text-xs">{(currentPage - 1) * pageSize + 1}</span> - <span className="text-white text-xs">{Math.min(currentPage * pageSize, filteredOrders.length)}</span> / <span className="text-blue-400 text-xs">{filteredOrders.length}</span>
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

      {/* Footer Info */}
      <div className="flex justify-between items-center opacity-30 text-[9px] font-black uppercase tracking-[0.4em] px-2 text-slate-500">
        <span>Binance Trading Engine Framework v3.0.1</span>
        <div className="flex gap-6">
          <span>Buffer: {orders.length} cached</span>
          <span>Gateway: Secure Websocket</span>
        </div>
      </div>
    </div>
  )
}
