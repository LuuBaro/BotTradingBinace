import React, { useEffect, useState, useMemo } from 'react'
import { useDashboardStore, useEventsStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { formatDistanceToNow, format } from 'date-fns'
import { Activity, Shield, TrendingUp, Server, Clock, Database, Brain, ChevronRight, Info, Power } from 'lucide-react'

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
  const [healthStatus, setHealthStatus] = useState<any>(null)
  const [pnlBreakdown, setPnlBreakdown] = useState({ realized: 0, realizedTotal: 0, unrealized: 0 })
  const [walletBalance, setWalletBalance] = useState<any>(null)
  const [hoveredCardIndex, setHoveredCardIndex] = useState<number | null>(null)
  const [tokenUsage, setTokenUsage] = useState<any>(null)
  const [isPauseLoading, setIsPauseLoading] = useState(false)

  // Memoized API client
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const days = timeRange === '1W' ? 7 : 1
        const [status, posResponse, ordResponse, decisionsResponse, historyData, latencyData, healthData, walletData, tokenData] = await Promise.all([
          api.getBotStatus(),
          api.getPositions(),
          api.getOrders(),
          api.getDecisions(10),
          api.getPnlHistory(days),
          api.getLatencyMetrics().catch(() => null),
          api.getHealthStatus().catch(() => null),
            api.getWalletBalance().catch(() => null),
            api.getLlmTokenUsage().catch(() => null)
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
        const realizedTotal = status.realized_pnl_total || 0
        const currentTotalPnL = realizedPnL + unrealizedPnL // Today's total (Daily perspective)
        setPnlToday(currentTotalPnL)
        setPnlBreakdown({ realized: realizedPnL, realizedTotal: realizedTotal, unrealized: unrealizedPnL })

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

        if (latencyData) {
          setLatency(latencyData)
        }

        if (healthData) {
          setHealth(healthData)
          setHealthStatus(healthData)
        }

        if (walletData) {
          setWalletBalance(walletData)

                if (tokenData) {
                  setTokenUsage(tokenData)
                }
        }

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

  const handleTogglePause = async () => {
    if (!botStatus) return
    
    setIsPauseLoading(true)
    
    try {
      const action = botStatus.paused ? api.resumeTrading() : api.pauseTrading()
      await action
      
      // Update local state immediately for UX feedback
      setBotStatus({
        ...botStatus,
        paused: !botStatus.paused
      })
    } catch (error) {
      console.error('Toggle pause error:', error)
    } finally {
      setIsPauseLoading(false)
    }
  }

  // Effect to boost main container z-index when tooltip is open to prevent header overlap
  useEffect(() => {
    const mainContainer = document.querySelector('main');
    if (hoveredCardIndex !== null) {
      if (mainContainer) mainContainer.style.zIndex = '9999';
      document.body.style.overflow = 'hidden';
    } else {
      if (mainContainer) mainContainer.style.zIndex = '';
      document.body.style.overflow = '';
    }
    return () => {
      if (mainContainer) mainContainer.style.zIndex = '';
      document.body.style.overflow = '';
    };
  }, [hoveredCardIndex]);

  return (
    <div className="space-y-6 md:space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-3 md:px-6 pt-4 overflow-x-hidden">
      {/* Hero Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6 mb-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-glow shadow-[0_0_8px_#10b981]"></span>
            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-emerald-400">Trạng thái: Tối ưu (Optimized)</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-white">Neural Hub</h1>
          <p className="text-slate-400 font-medium text-xs md:text-base">Tổng hợp trí tuệ AI và dữ liệu hệ thống</p>
        </div>
        <div className="grid grid-cols-2 lg:flex gap-3 md:gap-4 w-full lg:w-auto">
          <div className="px-4 md:px-5 py-3 glass-dark border-white/5 rounded-2xl flex items-center gap-3">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
              <Activity className="text-blue-400" size={16} />
            </div>
            <div>
              <span className="text-[8px] md:text-[10px] font-black text-slate-500 uppercase tracking-widest block">Độ trễ</span>
              <span className="text-sm md:text-lg font-black font-mono text-blue-100">{latency?.ws_p95 || 24}ms</span>
            </div>
          </div>
          <div className="px-4 md:px-5 py-3 glass-dark border-white/5 rounded-2xl flex items-center gap-3">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-purple-500/10 rounded-xl flex items-center justify-center border border-purple-500/20">
              <Shield className="text-purple-400" size={16} />
            </div>
            <div>
              <span className="text-[8px] md:text-[10px] font-black text-slate-500 uppercase tracking-widest block">Chế độ</span>
              <span className={`text-sm md:text-lg font-black uppercase ${botStatus?.approval_mode ? 'text-amber-400' : 'text-emerald-400'}`}>
                {botStatus?.approval_mode ? 'Thủ công' : 'Auto'}
              </span>
            </div>
          </div>
          <button
            onClick={handleTogglePause}
            disabled={isPauseLoading}
            className={`col-span-2 lg:col-span-1 px-4 md:px-5 py-3 rounded-2xl flex items-center gap-3 transition-all ${
              botStatus?.paused
                ? 'bg-red-500/10 border-red-500/30 hover:bg-red-500/20 hover:border-red-500/50'
                : 'glass-dark border-white/5 hover:bg-emerald-500/10 hover:border-emerald-500/30'
            } disabled:opacity-50 disabled:cursor-not-allowed group`}
          >
            <div className={`w-8 h-8 md:w-10 md:h-10 rounded-xl flex items-center justify-center border transition-all ${
              botStatus?.paused
                ? 'bg-red-500/10 border-red-500/20'
                : 'bg-emerald-500/10 border-emerald-500/20 group-hover:bg-emerald-500/20'
            }`}>
              <Power className={botStatus?.paused ? 'text-red-400' : 'text-emerald-400'} size={16} />
            </div>
            <div>
              <span className="text-[8px] md:text-[10px] font-black text-slate-500 uppercase tracking-widest block">Bot</span>
              <span className={`text-sm md:text-lg font-black uppercase ${botStatus?.paused ? 'text-red-400' : 'text-emerald-400'}`}>
                {isPauseLoading ? '...' : (botStatus?.paused ? 'Paused' : 'Running')}
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* 3D-like Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 overflow-visible">
        {[
          { label: 'Môi trường (Risk Mode)', value: botStatus?.mode || 'Demo', sub: botStatus?.paused ? 'SYSTEM PAUSED' : 'LIVE TRADING', color: 'text-blue-400', icon: <Server size={14} />, gradient: 'from-blue-500/10' },
          { label: 'Thời gian hoạt động', value: `${uptimeHours}h ${uptimeMinutes}m`, sub: `${positions.length} Vị thế đang mở`, color: 'text-purple-400', icon: <Clock size={14} />, gradient: 'from-purple-500/10' },
          { label: 'Alpha Hôm Nay (PnL)', value: `$${pnlToday.toFixed(2)}`, sub: `Kết quả giao dịch trong ngày`, color: pnlToday >= 0 ? 'text-emerald-400' : 'text-rose-400', icon: <TrendingUp size={14} />, gradient: pnlToday >= 0 ? 'from-emerald-500/10' : 'from-rose-500/10', tooltip: true },
          { label: 'Token Usage LLM', value: tokenUsage ? `${(tokenUsage.total_tokens || tokenUsage.tokens_actual || tokenUsage.total_tokens_estimated || tokenUsage.tokens_estimated || 0).toLocaleString()}` : '0', sub: tokenUsage ? `${tokenUsage.ai_calls_today || 0} AI calls hôm nay` : 'Đang tải...', color: 'text-cyan-400', icon: <Brain size={14} />, gradient: 'from-cyan-500/10', tooltip: true, tokenTooltip: true },
        ].map((stat, i) => (
          <div
            key={i}
            className={`relative card ${stat.tooltip ? 'overflow-visible cursor-pointer' : ''} ${hoveredCardIndex === i ? 'z-50' : 'z-0'} bg-gradient-to-br ${stat.gradient} to-transparent border-white/5 p-5 md:p-6 hover:scale-[1.02] active:scale-[0.98] transition-all group`}
            onClick={() => stat.tooltip && setHoveredCardIndex(i)}
            onMouseEnter={() => !stat.tooltip && setHoveredCardIndex(null)}
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 bg-white/5 rounded-lg text-slate-400 group-hover:text-white transition-colors">
                {stat.icon}
              </div>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{stat.label}</span>
            </div>
            <div className={`text-4xl font-black ${stat.color} tracking-tighter mb-1`}>{stat.value}</div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{stat.sub}</div>

            {/* PnL Tooltip */}
            {stat.tooltip && !stat.tokenTooltip && hoveredCardIndex === i && (
              <>
                <div
                  className="fixed inset-0 bg-black/85 transition-opacity"
                  onClick={() => setHoveredCardIndex(null)}
                  style={{
                    zIndex: 99999998,
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)'
                  }}
                />
                <div className="fixed inset-0 z-[99999999] flex items-center justify-center p-4 pointer-events-none">
                  <div className="w-[340px] max-w-full max-h-[90vh] bg-[#020617] border-2 border-emerald-500/40 rounded-3xl p-6 shadow-[0_0_100px_rgba(0,0,0,0.9)] pointer-events-auto relative overflow-y-auto custom-scrollbar">
                    <button
                      onClick={(e) => { e.stopPropagation(); setHoveredCardIndex(null); }}
                      className="absolute top-4 right-4 w-8 h-8 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-all z-10"
                    >
                      ✕
                    </button>

                    <div className="space-y-4 relative z-1">
                      <div className="pb-3 border-b border-white/5">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-emerald-500/10 rounded-xl flex items-center justify-center border border-emerald-500/20">
                            <TrendingUp className="text-emerald-400" size={20} />
                          </div>
                          <div>
                            <h3 className="text-sm font-black uppercase tracking-wider text-emerald-300">Chi Tiết P&L</h3>
                            <p className="text-[9px] text-slate-500 uppercase tracking-wide">Profit & Loss Breakdown</p>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-emerald-500/20 transition-all">
                          <div className="flex justify-between items-center">
                            <div className="space-y-1">
                              <div className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">Realized (Today)</div>
                              <div className="text-[9px] text-emerald-300/60">Từ 00:00 UTC</div>
                            </div>
                            <div className={`text-xl font-black font-mono ${pnlBreakdown.realized >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {pnlBreakdown.realized >= 0 ? '+' : ''}${pnlBreakdown.realized.toFixed(2)}
                            </div>
                          </div>
                        </div>

                        <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-amber-500/20 transition-all">
                          <div className="flex justify-between items-center">
                            <div className="space-y-1">
                              <div className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">Realized (All-Time)</div>
                              <div className="text-[9px] text-amber-300/60">Tổng Từ Trước Đến Nay</div>
                            </div>
                            <div className={`text-xl font-black font-mono ${pnlBreakdown.realizedTotal >= 0 ? 'text-amber-400' : 'text-rose-400'}`}>
                              {pnlBreakdown.realizedTotal >= 0 ? '+' : ''}${pnlBreakdown.realizedTotal.toFixed(2)}
                            </div>
                          </div>
                        </div>

                        <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-blue-500/20 transition-all">
                          <div className="flex justify-between items-center">
                            <div className="space-y-1">
                              <div className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">Unrealized</div>
                              <div className="text-[9px] text-blue-300/60">Vị Thế Đang Mở</div>
                            </div>
                            <div className={`text-xl font-black font-mono ${pnlBreakdown.unrealized >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {pnlBreakdown.unrealized >= 0 ? '+' : ''}${pnlBreakdown.unrealized.toFixed(2)}
                            </div>
                          </div>
                        </div>

                        <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-purple-500/20 transition-all">
                          <div className="flex justify-between items-center">
                            <div className="space-y-1">
                              <div className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">Net PnL (All-Time)</div>
                              <div className="text-[9px] text-purple-300/60">Từ vốn ban đầu ${walletBalance?.initial_balance?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '5,000.00'}</div>
                            </div>
                            <div className={`text-xl font-black font-mono ${(walletBalance?.wallet_balance || 0) - (walletBalance?.initial_balance || 5000) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {(walletBalance?.wallet_balance || 0) - (walletBalance?.initial_balance || 5000) >= 0 ? '+' : ''}${((walletBalance?.wallet_balance || 0) - (walletBalance?.initial_balance || 5000)).toFixed(2)}
                            </div>
                          </div>
                        </div>

                        <div className="bg-emerald-500/10 rounded-xl p-5 border border-emerald-500/20 relative overflow-hidden mt-6">
                          <div className="relative flex justify-between items-center">
                            <div>
                              <div className="text-[11px] font-black text-white uppercase tracking-widest">Hiệu Suất Hôm Nay</div>
                              <div className="text-[8px] text-emerald-300/60 mt-0.5">Alpha Velocity</div>
                            </div>
                            <div className={`text-2xl font-black font-mono ${pnlToday >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {pnlToday >= 0 ? '+' : ''}${pnlToday.toFixed(2)}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-start gap-2 px-3 py-2 bg-white/5 rounded-lg">
                        <span className="text-emerald-400 text-xs mt-0.5">ℹ️</span>
                        <p className="text-[9px] text-slate-400 leading-relaxed uppercase tracking-tighter">
                          Realized = Lệnh chốt | Unrealized = Đang chạy
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* Token Usage Tooltip */}
            {stat.tokenTooltip && hoveredCardIndex === i && tokenUsage && (
              <>
                <div
                  className="fixed inset-0 bg-black/85 transition-opacity"
                  onClick={() => setHoveredCardIndex(null)}
                  style={{
                    zIndex: 99999998,
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)'
                  }}
                />
                <div className="fixed inset-0 z-[99999999] flex items-center justify-center p-4 pointer-events-none">
                  <div className="w-[340px] max-w-full max-h-[90vh] bg-[#020617] border-2 border-cyan-500/40 rounded-3xl p-6 shadow-[0_0_100px_rgba(0,0,0,0.9)] pointer-events-auto relative overflow-y-auto custom-scrollbar">
                    <button
                      onClick={(e) => { e.stopPropagation(); setHoveredCardIndex(null); }}
                      className="absolute top-4 right-4 w-8 h-8 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-all z-10"
                    >
                      ✕
                    </button>

                    <div className="space-y-4 relative z-1">
                      <div className="pb-3 border-b border-white/5">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-cyan-500/10 rounded-xl flex items-center justify-center border border-cyan-500/20">
                            <Brain className="text-cyan-400" size={20} />
                          </div>
                          <div>
                            <h3 className="text-sm font-black uppercase tracking-wider text-cyan-300">Token Usage</h3>
                            <p className="text-[9px] text-slate-500 uppercase tracking-wide">LLM API Consumption</p>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
                          <div className="flex justify-between items-center">
                            <div className="space-y-1">
                              <div className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">Mode</div>
                              <div className="text-[9px] text-cyan-300/60">{tokenUsage.mode === 'two_tier' ? '2-Tier Cascade' : 'Single LLM'}</div>
                            </div>
                            <div className="text-lg font-black text-cyan-400 uppercase">
                              {tokenUsage.mode === 'two_tier' ? '🔀Scout→Verifier' : '🤖Single'}
                            </div>
                          </div>
                        </div>

                        {tokenUsage.mode === 'two_tier' ? (
                          <>
                            <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-emerald-500/20 transition-all">
                              <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                  <div className="text-[10px] text-emerald-400 uppercase tracking-wide font-semibold">Scout (Lightweight)</div>
                                  <div className="text-sm font-black font-mono text-emerald-400">{(tokenUsage.scout.tokens_estimated || 0).toLocaleString()}</div>
                                </div>
                                <div className="text-[9px] text-slate-500 space-y-0.5">
                                  <div>Provider: <span className="text-emerald-300">{tokenUsage.scout.provider}</span></div>
                                  <div>Model: <span className="text-emerald-300">{tokenUsage.scout.model}</span></div>
                                  <div>Calls: <span className="text-emerald-300">{tokenUsage.scout.calls_today}</span></div>
                                  <div className="text-[8px] text-emerald-300/60 italic">Estimated</div>
                                </div>
                              </div>
                            </div>

                            <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-purple-500/20 transition-all">
                              <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                  <div className="text-[10px] text-purple-400 uppercase tracking-wide font-semibold">Verifier (Detailed)</div>
                                  <div className="text-sm font-black font-mono text-purple-400">{(tokenUsage.verifier.tokens_actual || tokenUsage.verifier.tokens_estimated || 0).toLocaleString()}</div>
                                </div>
                                <div className="text-[9px] text-slate-500 space-y-0.5">
                                  <div>Provider: <span className="text-purple-300">{tokenUsage.verifier.provider}</span></div>
                                  <div>Model: <span className="text-purple-300">{tokenUsage.verifier.model}</span></div>
                                  <div>Calls: <span className="text-purple-300">{tokenUsage.verifier.calls_today}</span></div>
                                  <div className="text-[8px] text-purple-300/60 italic">{tokenUsage.verifier.tokens_actual ? 'Actual from API' : 'Estimated'}</div>
                                </div>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5 hover:border-cyan-500/20 transition-all">
                            <div className="space-y-2">
                              <div className="flex justify-between items-center">
                                <div className="text-[10px] text-cyan-400 uppercase tracking-wide font-semibold">LLM Provider</div>
                                <div className="text-sm font-black font-mono text-cyan-400">{(tokenUsage.tokens_actual || tokenUsage.tokens_estimated || 0).toLocaleString()}</div>
                              </div>
                              <div className="text-[9px] text-slate-500 space-y-0.5">
                                <div>Provider: <span className="text-cyan-300">{tokenUsage.provider}</span></div>
                                <div>Model: <span className="text-cyan-300">{tokenUsage.model}</span></div>
                                <div>Calls: <span className="text-cyan-300">{tokenUsage.ai_calls_today}</span></div>
                                <div className="text-[8px] text-cyan-300/60 italic">{tokenUsage.tokens_actual ? 'Actual from API' : 'Estimated'}</div>
                              </div>
                            </div>
                          </div>
                        )}

                        <div className="bg-cyan-500/10 rounded-xl p-5 border border-cyan-500/20 relative overflow-hidden mt-6">
                          <div className="relative flex justify-between items-center">
                            <div>
                              <div className="text-[11px] font-black text-white uppercase tracking-widest">Total Today</div>
                              <div className="text-[8px] text-cyan-300/60 mt-0.5">{tokenUsage.ai_calls_today} AI Decisions</div>
                            </div>
                            <div className="text-2xl font-black font-mono text-cyan-400">
                              {(tokenUsage.total_tokens || tokenUsage.tokens_actual || tokenUsage.total_tokens_estimated || tokenUsage.tokens_estimated || 0).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-start gap-2 px-3 py-2 bg-white/5 rounded-lg">
                        <span className="text-cyan-400 text-xs mt-0.5">ℹ️</span>
                        <p className="text-[9px] text-slate-400 leading-relaxed uppercase tracking-tighter">
                          {tokenUsage.note || 'Estimates based on average token usage'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            <div className={`absolute bottom-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity`}>
              {stat.icon && React.cloneElement(stat.icon as React.ReactElement, { size: 60 })}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-12 xl:col-span-8 card glass-dark border-white/5 p-8 relative overflow-hidden group">
          <div className="relative z-1 space-y-8">
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
          <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-blue-500/5 blur-[120px] pointer-events-none group-hover:bg-blue-500/10 transition-all"></div>
        </div>

        <div className="lg:col-span-12 xl:col-span-4 space-y-8">
          <div className="card border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/30 overflow-hidden relative group">
            <div className="p-8 space-y-6 relative z-1">
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
                      "{latestDecision.rationale || 'AI đang quan sát dòng tiền để xác định các thay đổi cấu trúc thị trường.'}"
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-950/60 rounded-xl border border-white/5 text-center">
                      <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-1">Intent</span>
                      <span className={`text-sm font-black uppercase ${latestDecision.action === 'OPEN' ? 'text-emerald-400' : latestDecision.action === 'CLOSE' ? 'text-rose-400' : 'text-slate-400'}`}>
                        {latestDecision.action === 'OPEN' ? 'MỞ VỊ THẾ' : latestDecision.action === 'CLOSE' ? 'ĐÓNG VỊ THẾ' : 'ĐỨNG NGOÀI'}
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
          </div>

          <div className="card glass-dark border-white/5">
            <div className="p-6 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <Server size={14} />
                Cơ sở hạ tầng Node (Infrastructure)
              </h3>
              <div className="space-y-4">
                {(healthStatus?.services || [
                  { name: 'market_streams', status: 'checking', label: 'Market Streams' },
                  { name: 'risk_validator', status: 'checking', label: 'Risk Validator' },
                  { name: 'binance_api', status: 'checking', label: 'Binance API' },
                  { name: 'database', status: 'checking', label: 'Internal DB' }
                ]).map((svc: any, i: number) => {
                  const label = svc.label || (svc.name === 'market_streams' ? 'Market Streams' :
                    svc.name === 'risk_validator' ? 'Risk Validator' :
                      svc.name === 'binance_api' ? 'Binance API' : 'Internal DB')
                  const statusText = svc.status === 'healthy' ? 'Optimal' :
                    svc.status === 'operational' ? 'Operational' :
                      svc.status === 'degraded' ? 'Degraded' :
                        svc.status === 'offline' ? 'Offline' : 'Checking...'
                  const statusColor = svc.status === 'healthy' ? 'text-emerald-400' :
                    svc.status === 'operational' ? 'text-emerald-400' :
                      svc.status === 'degraded' ? 'text-amber-400' : 'text-rose-400'
                  const glowColor = svc.status === 'healthy' || svc.status === 'operational' ? 'bg-emerald-500' :
                    svc.status === 'degraded' ? 'bg-amber-500' : 'bg-rose-500'

                  return (
                    <div key={i} className="flex justify-between items-center group cursor-default">
                      <span className="text-xs font-bold text-slate-400 group-hover:text-slate-200 transition-colors">{label}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-black uppercase tracking-tighter ${statusColor}`}>{statusText}</span>
                        <div className={`w-1 h-1 rounded-full ${glowColor} ${svc.status === 'healthy' || svc.status === 'operational' ? 'animate-glow' : ''}`}></div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card glass-dark border-white/5 overflow-hidden">
        <div className="p-4 px-8 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
            <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-blue-100">Luồng dữ liệu thời gian thực (Real-time Telemetry)</h2>
          </div>
        </div>
        <div className="max-h-64 overflow-y-auto custom-scrollbar bg-slate-950/40">
          {events.length === 0 ? (
            <div className="py-20 text-center opacity-30 flex flex-col items-center gap-4">
              <Activity size={32} />
              <span className="text-xs font-black uppercase tracking-widest">No signals recorded</span>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {events.slice(0, 50).map((event) => (
                <div key={event.id} className="p-4 px-8 hover:bg-white/[0.03] transition-colors flex items-center justify-between gap-6 group">
                  <div className="flex items-center gap-5 flex-grow">
                    <div className={`w-1 h-8 rounded-full ${event.level === 'error' ? 'bg-rose-500/50 shadow-[0_0_100px_#ef4444]' :
                      event.level === 'warning' ? 'bg-amber-500/50' : 'bg-blue-500/20'}`}></div>
                    <div className="space-y-0.5">
                      <span className="text-[8px] font-black uppercase tracking-widest text-slate-500">{event.level}</span>
                      <p className="text-sm text-slate-300 font-medium">{event.message}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-black font-mono text-slate-600 block">
                      {format(new Date(event.timestamp), 'HH:mm:ss')}
                    </span>
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
