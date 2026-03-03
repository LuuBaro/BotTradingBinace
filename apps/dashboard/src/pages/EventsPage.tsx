import React, { useEffect, useState, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { useEventsStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { formatDistanceToNow, format } from 'date-fns'
import { Terminal, History, User, List, Info, AlertOctagon, AlertTriangle, CheckCircle, Clock, Database, Code2 } from 'lucide-react'

// Map generic system logs to readable Vietnamese
const formatSystemLog = (message: string) => {
  if (!message) return ''
  let text = message

  // Pattern matching
  if (text.includes('Worker active. Monitoring')) {
    const parts = text.match(/Monitoring (\d+) symbols/)
    const count = parts ? parts[1] : ''
    text = `Worker Framework đang khởi chạy ở chế độ ngầm.Đang giám sát ${count} cặp giao dịch(Symbols).`
  } else if (text.includes('Fetching historical data')) {
    text = `Đang đồng bộ dữ liệu lịch sử nến(Klines) cho Neural Engine...`
  } else if (text.includes('Not enough historical trades')) {
    text = `Thiếu hụt Data mẫu trong Database.Yêu cầu nạp thêm dữ liệu để tiếp tục huấn luyện AI.`
  } else if (text.includes('Waiting for approval')) {
    text = `AI đã lên phương án Trade.Đang chờ xác nhận từ Quản trị viên(Manual Approval).`
  } else if (text.includes('Order placed successfully')) {
    text = `Bot đã đặt lệnh thành công lên sàn Binance.`
  } else if (text.includes('Worker sleeping')) {
    text = `Nhịp Worker tạm nghỉ chờ phiên làm việc tiếp theo.`
  } else if (text.includes('Syncing fallback trades')) {
    text = `Đang gọi API đồng bộ dự phòng lịch sử lệnh vào Database.`
  } else if (text.includes('Khởi động chu kỳ quét')) {
    text = `🔄 ${text} `
  } else if (text.includes('Đang quét dữ liệu thị trường')) {
    text = `🔍 ${text} `
  } else if (text.includes('AI đã soi')) {
    text = `💎 ${text} `
  } else if (text.includes('AI phát hiện tín hiệu')) {
    text = `🚀 ${text} `
  } else if (text.includes('Lỗi phân tích AI')) {
    text = `⚠️ ${text} `
  }

  // Common keyword bolding
  return text
}

export const EventsPage: React.FC = () => {
  const location = useLocation()
  const { events, setEvents } = useEventsStore()
  const [auditLog, setAuditLog] = useState<any[]>([])
  const [filter, setFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all')
  const [loading, setLoading] = useState(false)

  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token, location.search])

  useEffect(() => {
    const fetchAuditData = async () => {
      setLoading(true)
      try {
        const logs = await api.getAuditLog(100, 0)
        setAuditLog(logs || [])

        // Populate initial events
        if (events.length === 0) {
          const eventsResponse = await api.getEvents(200)
          if (eventsResponse && eventsResponse.events) {
            setEvents(eventsResponse.events)
          }
        }
      } catch (error) {
        console.error('Failed to fetch data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAuditData()
    const interval = setInterval(fetchAuditData, 15000)
    return () => clearInterval(interval)
  }, [api])

  const filteredEvents = events.filter((e) => filter === 'all' || e.level.toLowerCase() === filter.toLowerCase())

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <History className="text-purple-400" size={14} />
            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-purple-400">System Trace Logs</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-white">Events & Audit</h1>
          <p className="text-slate-400 font-medium">Deterministic audit trail and neural event propagation</p>
        </div>

        <div className="flex gap-3 bg-white/5 p-1.5 rounded-2xl border border-white/5">
          {(['all', 'info', 'warning', 'error'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px - 4 py - 2 text - [10px] font - black uppercase tracking - widest rounded - xl transition - all ${filter === f
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                  : 'text-slate-500 hover:text-slate-300'
                } `}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">
        {/* System Events Timeline */}
        <div className="xl:col-span-7 card glass-dark border-white/5 overflow-hidden flex flex-col h-[700px]">
          <div className="p-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
            <h2 className="text-xl font-black tracking-tight flex items-center gap-3 text-white">
              <Terminal className="text-blue-400" size={20} />
              Neural Event Stream
            </h2>
            <div className="flex items-center gap-2 text-[10px] font-black text-slate-500 uppercase tracking-widest">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
              Live Ingestion
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-0">
            {filteredEvents.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-30 gap-4">
                <Database size={48} />
                <span className="text-xs font-black uppercase tracking-[0.2em]">No signals recorded in current buffer</span>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {filteredEvents.map((event, idx) => (
                  <div key={event.id || idx} className="p-5 hover:bg-white/[0.02] transition-colors group">
                    <div className="flex gap-5">
                      <div className="flex flex-col items-center gap-2 pt-1">
                        <div className={`p - 1.5 rounded - lg ${event.level.toLowerCase() === 'error' ? 'bg-rose-500/20 text-rose-400' :
                            event.level.toLowerCase() === 'warning' ? 'bg-amber-500/20 text-amber-400' :
                              'bg-blue-500/20 text-blue-400'
                          } `}>
                          {event.level.toLowerCase() === 'error' ? <AlertOctagon size={14} /> :
                            event.level.toLowerCase() === 'warning' ? <AlertTriangle size={14} /> :
                              <Info size={14} />}
                        </div>
                        <div className="w-[1px] flex-1 bg-white/5 group-last:hidden"></div>
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex justify-between items-center">
                          <span className={`text - [9px] font - black uppercase tracking - widest flex items - center gap - 1.5 ${event.level.toLowerCase() === 'error' ? 'text-rose-500' :
                              event.level.toLowerCase() === 'warning' ? 'text-amber-500' :
                                'text-blue-500'
                            } `}>
                            <Code2 size={10} className="opacity-70" />
                            NODE_EVENT // {event.id ? String(event.id).slice(0, 8) : 'SYSTEM'}
                          </span>
                          <span className="text-[10px] font-mono text-slate-600 font-bold">
                            {format(new Date(event.timestamp), 'HH:mm:ss.SSS')}
                          </span>
                        </div>
                        <p className="text-sm text-slate-200 font-medium leading-relaxed">
                          {formatSystemLog(event.message)}
                        </p>
                        {event.details && (
                          <div className="mt-3 p-3 bg-black/30 rounded-xl border border-white/5 font-mono text-[10px] text-slate-500">
                            {JSON.stringify(event.details, null, 2)}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Audit Log Sidebar */}
        <div className="xl:col-span-5 flex flex-col gap-8 h-[700px]">
          <div className="card border-purple-500/10 bg-gradient-to-br from-slate-950 to-purple-950/20 flex-1 overflow-hidden flex flex-col relative">
            <div className="p-6 border-b border-white/5 bg-white/[0.02] relative z-10 flex justify-between items-center">
              <h2 className="text-xl font-black tracking-tight flex items-center gap-3 text-white">
                <User className="text-purple-400" size={20} />
                Action Audit Trail
              </h2>
              {loading && <div className="spinner w-3 h-3 border-2 border-purple-500/30 border-t-purple-500"></div>}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar relative z-10">
              {auditLog.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center opacity-20 gap-4">
                  <List size={40} />
                  <span className="text-xs font-black uppercase tracking-widest">No audit immutable records</span>
                </div>
              ) : (
                <div className="p-4 space-y-4">
                  {auditLog.map((log, idx) => (
                    <div key={idx} className="p-4 bg-white/5 rounded-2xl border border-white/5 hover:border-purple-500/30 transition-all cursor-default group">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center gap-2">
                          <CheckCircle size={12} className="text-emerald-400" />
                          <span className="text-xs font-black text-white uppercase tracking-tighter">{log.action}</span>
                        </div>
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                          {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 mb-3">
                        <div className="p-2 bg-black/20 rounded-lg">
                          <span className="text-[8px] font-black text-slate-500 uppercase block mb-1">Actor</span>
                          <span className="text-[10px] font-bold text-purple-300">{log.actor}</span>
                        </div>
                        <div className="p-2 bg-black/20 rounded-lg">
                          <span className="text-[8px] font-black text-slate-500 uppercase block mb-1">Target</span>
                          <span className="text-[10px] font-bold text-slate-200">{log.target || 'N/A'}</span>
                        </div>
                      </div>
                      {log.details_json && (
                        <div className="p-3 bg-black/40 rounded-xl font-mono text-[9px] text-slate-600 line-clamp-2 group-hover:line-clamp-none transition-all">
                          {JSON.stringify(log.details_json)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            {/* Subtle background element */}
            <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-purple-500/5 blur-[100px] pointer-events-none"></div>
          </div>

          <div className="card glass-dark border-white/5 p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-500/10 rounded-2xl flex items-center justify-center border border-blue-500/20">
                <Clock className="text-blue-400" size={24} />
              </div>
              <div className="flex-1">
                <span className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em] block">Journal Capacity</span>
                <div className="flex justify-between items-end mt-1">
                  <span className="text-xl font-black text-white font-mono">100 / 1000</span>
                  <span className="text-[10px] font-bold text-blue-500">10% ALLOCATED</span>
                </div>
                <div className="w-full h-1 bg-white/5 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-blue-500 w-[10%]"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
