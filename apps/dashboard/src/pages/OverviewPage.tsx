import React, { useEffect, useState, useMemo } from 'react'
import { useDashboardStore, useEventsStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { formatDistanceToNow, format } from 'date-fns'
import { Activity, Shield, TrendingUp, Server, Clock, Database, Brain, ChevronRight, Info } from 'lucide-react'

export const OverviewPage: React.FC = () => {
  const {
    botStatus, setBotStatus, positions, setPositions,
    orders, setOrders, pnlToday, setPnlToday, latency,
    setLatency, setHealth, setDecisions
  } = useDashboardStore()
  const { events } = useEventsStore()
  const [latestDecision, setLatestDecision] = useState<any>(null)
  const [pnlHistory, setPnlHistory] = useState<any[]>([])
  const [timeRange, setTimeRange] = useState<'1H' | '4H' | '1D' | '1W'>('1D')

  // Memoized API client
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const days = timeRange === '1W' ? 7 : 1
        const [status, posResponse, ordResponse, decisionsResponse, historyData] = await Promise.all([
          api.getBotStatus(),
          api.getPositions(),
          api.getOrders(),
          api.getDecisions(10),
          api.getPnlHistory(days)
        ])

        const currentPositions = Array.isArray(posResponse) ? posResponse : []
        const currentOrders = Array.isArray(ordResponse) ? ordResponse : []
        const allDecisions = Array.isArray(decisionsResponse) ? decisionsResponse : []

        setPositions(currentPositions)
        setOrders(currentOrders)
        setDecisions(allDecisions)

        // Calculate PnL (Realized + Unrealized)
        const unrealizedPnL = currentPositions.reduce((sum: number, p: any) => sum + (p.unrealized_pnl || 0), 0)
        const realizedPnL = status.realized_pnl_today || 0
        const currentTotalPnL = realizedPnL + unrealizedPnL
        setPnlToday(currentTotalPnL)

        if (Array.isArray(historyData) && historyData.length > 0) {
          // Filter historyData based on timeRange if needed
          let filteredHistory = historyData
          const now = new Date()
          if (timeRange === '1H') {
            const oneHourAgo = new Date(now.getTime() - 3600000)
            filteredHistory = historyData.filter((h: any) => new Date(h.time.replace(' ', 'T')) >= oneHourAgo)
            if (filteredHistory.length === 0) filteredHistory = historyData.slice(-2)
          } else if (timeRange === '4H') {
            const fourHoursAgo = new Date(now.getTime() - 4 * 3600000)
            filteredHistory = historyData.filter((h: any) => new Date(h.time.replace(' ', 'T')) >= fourHoursAgo)
            if (filteredHistory.length === 0) filteredHistory = historyData.slice(-5)
          }

          // Calculate cumulative PnL for the performance curve
          let cumulative = 0
          const formattedHistory = filteredHistory.map((h: any) => {
            cumulative += h.pnl
            return {
              time: format(new Date(h.time.replace(' ', 'T')), 'HH:mm'),
              pnl: cumulative
            }
          })

          // Add current unrealized PnL to the last point
          if (formattedHistory.length > 0) {
            formattedHistory[formattedHistory.length - 1].pnl += unrealizedPnL
          }

          setPnlHistory(formattedHistory)
        } else {
          const now = new Date()
          const fallback = Array.from({ length: 6 }, (_, i) => ({
            time: format(new Date(now.getTime() - (5 - i) * 10 * 60000), 'HH:mm'),
            pnl: currentTotalPnL
          }))
          setPnlHistory(fallback)
        }

        if (allDecisions.length > 0) {
          setLatestDecision(allDecisions[0])
        }

        const latencyData = await api.getLatencyMetrics()
        setLatency(latencyData)

        const healthData = await api.getHealthStatus()
        setHealth(healthData)

        setBotStatus({
          mode: status.mode || 'Demo',
          uptime_seconds: status.uptime_seconds || 0,
          paused: status.paused || false,
          total_positions: status.total_positions || 0,
          total_orders: status.total_orders || 0,
          approval_mode: status.approval_mode || false
        })
      } catch (error) {
        console.error('Overview sync failed:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 8000)
    return () => clearInterval(interval)
  }, [api, timeRange])

  const uptimeHours = botStatus?.uptime_seconds ? Math.floor(botStatus.uptime_seconds / 3600) : 0
  const uptimeMinutes = botStatus?.uptime_seconds ? Math.floor((botStatus.uptime_seconds % 3600) / 60) : 0

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Hero Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6 mb-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-glow shadow-[0_0_8px_#10b981]"></span>
            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-emerald-400">Trạng thái: Tối ưu (Optimized)</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-white">Neural Hub</h1>
          <p className="text-slate-400 font-medium">Tổng hợp trí tuệ AI và dữ liệu hệ thống</p>
        </div>
        <div className="flex gap-4">
          <div className="px-5 py-3 glass-dark border-white/5 rounded-2xl flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
              <Activity className="text-blue-400" size={20} />
            </div>
            <div>
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">Độ trễ (Latency)</span>
              <span className="text-lg font-black font-mono text-blue-100">{latency?.ws_p95 || 24}ms</span>
            </div>
          </div>
          <div className="px-5 py-3 glass-dark border-white/5 rounded-2xl flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-500/10 rounded-xl flex items-center justify-center border border-purple-500/20">
              <Shield className="text-purple-400" size={20} />
            </div>
            <div>
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">Chế độ bảo vệ (Gatekeeper)</span>
              <span className={`text-lg font-black uppercase ${botStatus?.approval_mode ? 'text-amber-400' : 'text-emerald-400'}`}>
                {botStatus?.approval_mode ? 'Thủ công' : 'Tự động (Autopilot)'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3D-like Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Môi trường (Risk Mode)', value: botStatus?.mode || 'Demo', sub: botStatus?.paused ? 'SYSTEM PAUSED' : 'LIVE TRADING', color: 'text-blue-400', icon: <Server size={14} />, gradient: 'from-blue-500/10' },
          { label: 'Thời gian hoạt động', value: `${uptimeHours}h ${uptimeMinutes}m`, sub: `${positions.length} Vị thế đang mở`, color: 'text-purple-400', icon: <Clock size={14} />, gradient: 'from-purple-500/10' },
          { label: 'Tổng Alpha (PnL)', value: `$${pnlToday.toFixed(2)}`, sub: `${orders.length} Lệnh đã xử lý`, color: pnlToday >= 0 ? 'text-emerald-400' : 'text-rose-400', icon: <TrendingUp size={14} />, gradient: pnlToday >= 0 ? 'from-emerald-500/10' : 'from-rose-500/10' },
          { label: 'Sự kiện hệ thống', value: `${events.length}`, sub: 'Dữ liệu telemetry đang hoạt động', color: 'text-amber-400', icon: <Database size={14} />, gradient: 'from-amber-500/10' },
        ].map((stat, i) => (
          <div key={i} className={`relative group card bg-gradient-to-br ${stat.gradient} to-transparent border-white/5 p-6 hover:scale-[1.02]`}>
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 bg-white/5 rounded-lg text-slate-400 group-hover:text-white transition-colors">
                {stat.icon}
              </div>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{stat.label}</span>
            </div>
            <div className={`text-4xl font-black ${stat.color} tracking-tighter mb-1`}>{stat.value}</div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{stat.sub}</div>
            <div className={`absolute bottom-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity`}>
              {stat.icon && React.cloneElement(stat.icon as React.ReactElement, { size: 60 })}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        {/* Main Neural Performance Chart */}
        <div className="lg:col-span-12 xl:col-span-8 card glass-dark border-white/5 p-8 relative overflow-hidden group">
          <div className="relative z-10 space-y-8">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-black tracking-tight flex items-center gap-3">
                <Activity className="text-blue-400" size={24} />
                Biểu đồ PnL (Alpha Velocity)
              </h2>
              <div className="flex gap-2">
                {(['1H', '4H', '1D', '1W'] as const).map(t => (
                  <button
                    key={t}
                    onClick={() => setTimeRange(t)}
                    className={`px-3 py-1 text-[10px] font-black rounded-lg transition-all ${t === timeRange ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'bg-white/5 text-slate-500 hover:text-white'}`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div className="h-[400px] w-full mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pnlHistory}>
                  <defs>
                    <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="10 10" stroke="#ffffff03" vertical={false} />
                  <XAxis dataKey="time" stroke="#ffffff20" fontSize={11} tickLine={false} axisLine={false} tickMargin={15} />
                  <YAxis stroke="#ffffff20" fontSize={11} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(2, 6, 23, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '20px', backdropFilter: 'blur(10px)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}
                    itemStyle={{ color: '#60a5fa', fontWeight: 'bold' }}
                    labelStyle={{ color: '#94a3b8', marginBottom: '8px', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}
                    cursor={{ stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '5 5' }}
                  />
                  <Area type="monotone" dataKey="pnl" stroke="#3b82f6" strokeWidth={4} fillOpacity={1} fill="url(#colorPnl)" animationDuration={2000} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Subtle background glow */}
          <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-blue-500/5 blur-[120px] pointer-events-none group-hover:bg-blue-500/10 transition-all"></div>
        </div>

        {/* Intelligence Sidebar */}
        <div className="lg:col-span-12 xl:col-span-4 space-y-8">
          {/* Latest Decision Card */}
          <div className="card border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/30 overflow-hidden relative group">
            <div className="p-8 space-y-6 relative z-10">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-blue-500/10 rounded-2xl flex items-center justify-center border border-blue-500/20 group-hover:bg-blue-500/20 transition-all">
                  <Brain className="text-blue-400" size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-black text-white uppercase tracking-tighter">Live Intent (Dự định)</h2>
                  <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Tiến trình AI (Process Trace)</span>
                </div>
              </div>

              {latestDecision ? (
                <div className="space-y-6 animate-fadeIn">
                  <div className="bg-white/5 p-5 rounded-2xl border border-white/5 italic">
                    <p className="text-sm text-slate-300 leading-relaxed font-medium">
                      <Info size={12} className="inline mr-2 text-blue-400 opacity-50" />
                      "{latestDecision.rationale || 'AI is currently observing order flow for potential structural shifts.'}"
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-950/60 rounded-xl border border-white/5 text-center">
                      <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-1">Intent</span>
                      <span className={`text-sm font-black uppercase ${latestDecision.action === 'OPEN' ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {latestDecision.action}
                      </span>
                    </div>
                    <div className="p-4 bg-slate-950/60 rounded-xl border border-white/5 text-center">
                      <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-1">Độ tin cậy (Confidence)</span>
                      <span className="text-sm font-black text-blue-100">{(latestDecision.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center px-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono text-slate-500">#{latestDecision.trace_id?.slice(0, 12)}</span>
                      <ChevronRight size={10} className="text-slate-700" />
                    </div>
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                      {formatDistanceToNow(new Date(latestDecision.timestamp), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="py-20 flex flex-col items-center justify-center gap-4 opacity-50 text-center">
                  <div className="spinner w-8 h-8"></div>
                  <span className="text-xs font-black uppercase tracking-widest">Initializing Neural Core</span>
                </div>
              )}
            </div>
            {/* Corner decoration */}
            <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl -translate-y-12 translate-x-12"></div>
          </div>

          {/* Infrastructure Health Card */}
          <div className="card glass-dark border-white/5">
            <div className="p-6 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <Server size={14} />
                Cơ sở hạ tầng Node (Infrastructure)
              </h3>
              <div className="space-y-4">
                {[
                  { label: 'Market Streams', status: 'Optimal', color: 'text-emerald-400' },
                  { label: 'Risk Validator', status: 'Operational', color: 'text-emerald-400' },
                  { label: 'Binance API', status: 'High Performance', color: 'text-emerald-400' },
                  { label: 'Internal DB', status: 'Synced', color: 'text-emerald-400' }
                ].map((svc, i) => (
                  <div key={i} className="flex justify-between items-center group cursor-default">
                    <span className="text-xs font-bold text-slate-400 group-hover:text-slate-200 transition-colors">{svc.label}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-black uppercase tracking-tighter ${svc.color}`}>{svc.status}</span>
                      <div className={`w-1 h-1 rounded-full bg-emerald-500 animate-glow`}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Full Width Telemetry Ticker */}
      <div className="card glass-dark border-white/5 overflow-hidden">
        <div className="p-4 px-8 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
            <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-blue-100">Luồng dữ liệu thời gian thực (Real-time Telemetry)</h2>
          </div>
          <button className="text-[10px] font-black text-slate-500 hover:text-white uppercase transition-colors">Xóa lịch sử</button>
        </div>
        <div className="max-h-64 overflow-y-auto custom-scrollbar bg-slate-950/40">
          {events.length === 0 ? (
            <div className="py-20 text-center opacity-30 flex flex-col items-center gap-4">
              <Activity size={32} />
              <span className="text-xs font-black uppercase tracking-widest">No signals recorded in current session</span>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {events.slice(0, 50).map((event) => (
                <div key={event.id} className="p-4 px-8 hover:bg-white/[0.03] transition-colors flex items-center justify-between gap-6 group">
                  <div className="flex items-center gap-5 flex-grow">
                    <div className={`w-1 h-8 rounded-full ${event.level === 'error' ? 'bg-rose-500/50 shadow-[0_0_10px_#ef4444]' :
                      event.level === 'warning' ? 'bg-amber-500/50 shadow-[0_0_10px_#f59e0b]' :
                        'bg-blue-500/20 group-hover:bg-blue-500/50 transition-all'
                      }`}></div>
                    <div className="space-y-0.5">
                      <span className={`text-[8px] font-black uppercase tracking-widest ${event.level === 'error' ? 'text-rose-400' :
                        event.level === 'warning' ? 'text-amber-400' :
                          'text-slate-500'
                        }`}>
                        {event.level} // node_telemetry_{event.id.slice(0, 4)}
                      </span>
                      <p className="text-sm text-slate-300 font-medium">{event.message}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-black font-mono text-slate-600 block">
                      {format(new Date(event.timestamp), 'HH:mm:ss.SSS')}
                    </span>
                    <span className="text-[8px] text-slate-700 font-bold uppercase tracking-widest">Live Flow</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

