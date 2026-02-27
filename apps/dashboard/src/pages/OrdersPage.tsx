import React, { useEffect, useState, useMemo } from 'react'
import { useDashboardStore, Order } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { formatDistanceToNow, format } from 'date-fns'
import { Terminal, CheckCircle2, XCircle, ArrowUpRight, ArrowDownRight, RefreshCw, Layers, X, Info, Hash, Activity } from 'lucide-react'

export const OrdersPage: React.FC = () => {
  const { orders, setOrders } = useDashboardStore()
  const [filter, setFilter] = useState<'open' | 'filled' | 'cancelled' | 'all'>('all')
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)

  // Memoized API client
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response = await api.getOrders(200)
        // API returns a direct array, not wrapped in { orders: [] }
        setOrders(Array.isArray(response) ? response : [])
      } catch (error) {
        console.error('Failed to fetch orders:', error)
      }
    }

    fetchOrders()
    const interval = setInterval(fetchOrders, 8000)
    return () => clearInterval(interval)
  }, [api, setOrders, refreshKey])

  const filteredOrders = orders.filter((o) => {
    if (filter === 'all') return true
    if (filter === 'open') return ['NEW', 'PARTIALLY_FILLED'].includes(o.status.toUpperCase())
    if (filter === 'cancelled') return o.status.toUpperCase() === 'CANCELLED'
    if (filter === 'filled') return o.status.toUpperCase() === 'FILLED'
    return o.status.toLowerCase() === filter.toLowerCase()
  })

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
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

              <div className="pt-4 flex items-center gap-4 opacity-50 border-t border-white/5">
                <div className="flex items-center gap-2">
                  <Activity size={12} className="text-slate-400" />
                  <span className="text-[9px] font-black text-slate-500 uppercase">Khởi tạo: {format(new Date(selectedOrder.created_at), 'dd/MM/yyyy HH:mm:ss')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Terminal className="text-blue-400" size={24} />
            </div>
            <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Nhật ký giao dịch</span>
          </div>
          <h1 className="text-5xl font-black text-gradient">Lịch sử lệnh</h1>
          <p className="text-slate-400 mt-2 max-w-xl">Danh sách chi tiết các lệnh đã kích hoạt, đang chờ xử lý và đã hoàn tất trên hệ thống.</p>
        </div>

        <div className="flex flex-wrap gap-2 p-1.5 glass-dark border-white/5 rounded-3xl">
          {(['all', 'open', 'filled', 'cancelled'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-6 py-2.5 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${filter === f
                ? 'bg-blue-600 text-white shadow-xl shadow-blue-500/20'
                : 'text-slate-500 hover:text-white hover:bg-white/5'
                }`}
            >
              {f === 'all' ? 'Tất cả' : f === 'open' ? 'Đang mở' : f === 'filled' ? 'Đã khớp' : 'Đã hủy'}
            </button>
          ))}
          <div className="w-px h-8 bg-white/5 mx-2 self-center"></div>
          <button
            onClick={() => setRefreshKey(k => k + 1)}
            className="p-2.5 hover:bg-white/5 rounded-2xl text-slate-500 hover:text-white transition-all group"
          >
            <RefreshCw size={18} className="group-hover:rotate-180 transition-transform duration-500" />
          </button>
        </div>
      </div>

      {/* Stats Summary Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card glass-dark border-white/5 p-6 flex items-center justify-between group">
          <div>
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] block mb-1">Tổng số lệnh</span>
            <span className="text-3xl font-black text-white font-mono">{orders.length}</span>
          </div>
          <div className="w-12 h-12 bg-blue-500/10 rounded-2xl flex items-center justify-center border border-blue-500/20">
            <Layers className="text-blue-400" size={20} />
          </div>
        </div>
        <div className="card glass-dark border-white/5 p-6 flex items-center justify-between group">
          <div>
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] block mb-1">Lệnh đã khớp</span>
            <span className="text-3xl font-black text-emerald-400 font-mono">{orders.filter(o => o.status === 'FILLED').length}</span>
          </div>
          <div className="w-12 h-12 bg-emerald-500/10 rounded-2xl flex items-center justify-center border border-emerald-500/20">
            <CheckCircle2 className="text-emerald-400" size={20} />
          </div>
        </div>
        <div className="card glass-dark border-white/5 p-6 flex items-center justify-between group">
          <div>
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] block mb-1">Lệnh đã hủy</span>
            <span className="text-3xl font-black text-rose-400 font-mono">{orders.filter(o => o.status === 'CANCELLED').length}</span>
          </div>
          <div className="w-12 h-12 bg-rose-500/10 rounded-2xl flex items-center justify-center border border-rose-500/20">
            <XCircle className="text-rose-400" size={20} />
          </div>
        </div>
      </div>

      {/* Orders Table Section */}
      <div className="card glass-dark border-white/5 shadow-3xl overflow-hidden animate-slideUp">
        <div className="table-container p-0 border-none">
          <table className="table">
            <thead>
              <tr className="bg-white/[0.02]">
                <th className="rounded-tl-2xl py-6 px-8">Mã lệnh (Order ID)</th>
                <th>Cặp tiền</th>
                <th>Loại lệnh</th>
                <th className="text-right">Khối lượng</th>
                <th>Trạng thái</th>
                <th className="text-right rounded-tr-2xl px-8">Thời gian</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-32 opacity-30">
                    <div className="flex flex-col items-center gap-4">
                      <Terminal size={48} />
                      <span className="text-xs font-black uppercase tracking-[0.3em]">Không tìm thấy dữ liệu lệnh nào khớp với lọc</span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr
                    key={order.id}
                    className="group hover:bg-white/[0.03] transition-colors cursor-pointer"
                    onClick={() => setSelectedOrder(order)}
                  >
                    <td className="py-6 px-8">
                      <div className="flex items-center gap-3">
                        <div className={`w-1.5 h-1.5 rounded-full ${order.status === 'FILLED' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' :
                          order.status === 'CANCELLED' ? 'bg-rose-500' : 'bg-amber-500 animate-pulse'
                          }`}></div>
                        <span className="text-xs font-mono font-black text-slate-500 group-hover:text-blue-400 transition-colors uppercase tracking-tight">#{order.id.slice(0, 12)}</span>
                      </div>
                    </td>
                    <td className="font-black font-mono text-white italic tracking-tighter text-lg">{order.symbol}</td>
                    <td>
                      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-xl text-[10px] font-black uppercase tracking-widest ${order.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}>
                        {order.side === 'BUY' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                        {order.side}
                      </div>
                    </td>
                    <td className="text-right font-black font-mono text-blue-100">
                      <span className="text-[10px] text-slate-600 mr-2 uppercase">Qty:</span>
                      {(order.quantity || 0).toFixed(4)}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-widest ${order.status === 'FILLED' ? 'bg-emerald-500/10 text-emerald-400' :
                          order.status === 'CANCELLED' ? 'bg-rose-500/10 text-rose-400' :
                            'bg-amber-500/10 text-amber-400'
                          }`}>
                          {order.status === 'FILLED' ? 'Đã khớp' : order.status}
                        </span>
                      </div>
                    </td>
                    <td className="text-right px-8">
                      <div className="flex flex-col items-end">
                        <span className="text-[11px] font-black text-slate-300">
                          {formatDistanceToNow(new Date(order.created_at), { addSuffix: true })}
                        </span>
                        <span className="text-[9px] font-mono text-slate-600 uppercase">
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
      </div>

      {/* Footer Info */}
      <div className="flex justify-between items-center opacity-30 text-[9px] font-black uppercase tracking-[0.3em] px-2 text-slate-500">
        <span>Binance Order Gateway v2.4</span>
        <span>Latency Offset: -1.2ms</span>
      </div>
    </div>
  )
}
