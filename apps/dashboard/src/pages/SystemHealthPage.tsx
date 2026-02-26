import React, { useEffect, useState, useMemo } from 'react'
import { useDashboardStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Activity, Shield, Wifi, Database, Zap, RefreshCw, CheckCircle2, Clock, Globe } from 'lucide-react'
import { format } from 'date-fns'

export const SystemHealthPage: React.FC = () => {
  const { health, latency, setHealth, setLatency } = useDashboardStore()
  const [reconStatus, setReconStatus] = useState<any>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  const fetchHealth = async () => {
    setIsRefreshing(true)
    try {
      const h = await api.getHealthStatus()
      const l = await api.getLatencyMetrics()
      const r = await api.getReconSummary()

      setHealth(h)
      setLatency(l)
      setReconStatus(r)
    } catch (error) {
      console.error('Failed to fetch health:', error)
    } finally {
      setTimeout(() => setIsRefreshing(false), 500)
    }
  }

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 8000)
    return () => clearInterval(interval)
  }, [api])

  const HealthCard = ({ title, status, icon: Icon, color, children }: any) => (
    <div className="card glass-dark border-white/5 overflow-hidden group">
      <div className="p-6 space-y-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl bg-${color}-500/10 border border-${color}-500/20 group-hover:scale-110 transition-transform`}>
              <Icon size={18} className={`text-${color}-400`} />
            </div>
            <h3 className="text-sm font-black uppercase tracking-widest text-slate-200">{title}</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-black uppercase tracking-tighter ${status ? 'text-emerald-400' : 'text-rose-400'}`}>
              {status ? 'Optimal' : 'Disturbed'}
            </span>
            <div className={`w-1.5 h-1.5 rounded-full ${status ? 'bg-emerald-500 animate-glow' : 'bg-rose-500 shadow-[0_0_10px_#ef4444]'}`}></div>
          </div>
        </div>
        <div className="space-y-3 pt-2">
          {children}
        </div>
      </div>
      <div className={`absolute bottom-0 left-0 h-[2px] bg-gradient-to-r from-${color}-500/50 to-transparent w-full opacity-30`}></div>
    </div>
  )

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Globe className="text-blue-400" size={14} />
            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-blue-400">Infrastructure Nexus</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-white">System Health</h1>
          <p className="text-slate-400 font-medium">Real-time infrastructure telemetry and heartbeat monitoring</p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={isRefreshing}
          className="px-6 py-3 glass-dark border-white/10 rounded-2xl flex items-center gap-3 hover:bg-white/5 transition-all disabled:opacity-50"
        >
          <RefreshCw size={18} className={`text-blue-400 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="text-xs font-black uppercase tracking-widest text-white">Manual Pulse Check</span>
        </button>
      </div>

      {/* Primary Nodes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <HealthCard title="WebSocket" status={health?.ws_connected} icon={Wifi} color="blue">
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">State</span>
            <span className="text-xs font-mono font-black text-white">{health?.ws_connected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          </div>
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Re-syncs</span>
            <span className="text-xs font-mono font-black text-blue-400">{health?.ws_reconnects || 0}</span>
          </div>
        </HealthCard>

        <HealthCard title="REST Gateway" status={health?.rest_healthy} icon={Zap} color="purple">
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Latency</span>
            <span className="text-xs font-mono font-black text-white">{latency?.rest_p95 || 0}ms</span>
          </div>
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Error Rate</span>
            <span className={`text-xs font-mono font-black ${health?.rest_errors > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {(health?.rest_errors || 0).toFixed(2)}%
            </span>
          </div>
        </HealthCard>

        <HealthCard title="Neural DB" status={health?.db_healthy} icon={Database} color="amber">
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Pool Usage</span>
            <span className="text-xs font-mono font-black text-white">
              {health?.db_pool_size || 0} / {health?.db_pool_max || 10}
            </span>
          </div>
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">State</span>
            <span className="text-xs font-mono font-black text-amber-400">READY</span>
          </div>
        </HealthCard>

        <HealthCard title="Risk Guard" status={health?.circuit_breaker_state === 'CLOSED'} icon={Shield} color="rose">
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">State</span>
            <span className={`text-xs font-mono font-black ${health?.circuit_breaker_state === 'CLOSED' ? 'text-emerald-400' : 'text-rose-400'}`}>
              {health?.circuit_breaker_state || 'UNKNOWN'}
            </span>
          </div>
          <div className="flex justify-between items-center px-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Trading Mode</span>
            <span className="text-xs font-mono font-black text-white">
              {health?.is_safe_for_trading ? 'SAFE-EXEC' : 'HALTED'}
            </span>
          </div>
        </HealthCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        {/* Latency Matrix */}
        <div className="lg:col-span-12 xl:col-span-7 card glass-dark border-white/5 p-8 relative overflow-hidden group">
          <div className="relative z-10 space-y-8">
            <h2 className="text-2xl font-black tracking-tight flex items-center gap-3">
              <Activity className="text-blue-400" size={24} />
              Latency Response Matrix
            </h2>
            <div className="grid grid-cols-3 gap-8">
              {[
                { label: 'WebSocket P95', value: latency?.ws_p95, sub: 'Live Stream' },
                { label: 'REST API P95', value: latency?.rest_p95, sub: 'Command Loop' },
                { label: 'Clock Skew', value: latency?.clock_skew, sub: 'Drift Variance' },
              ].map((m, i) => (
                <div key={i} className="space-y-2">
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 block">{m.label}</span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black text-white font-mono tracking-tighter">{m.value || 0}</span>
                    <span className="text-sm font-bold text-slate-500 uppercase">ms</span>
                  </div>
                  <span className="text-[9px] font-black uppercase text-blue-500/50 block">{m.sub}</span>
                </div>
              ))}
            </div>

            <div className="pt-6 border-t border-white/5">
              <div className="flex items-center gap-3 text-slate-400">
                <Clock size={14} />
                <span className="text-[10px] font-black uppercase tracking-widest">
                  Last Matrix Update: {health?.rest_last_request ? format(new Date(health.rest_last_request), 'HH:mm:ss.SSS') : 'Synchronizing...'}
                </span>
              </div>
            </div>
          </div>
          <div className="absolute top-0 right-0 w-[50%] h-full bg-blue-500/5 blur-[120px] pointer-events-none group-hover:bg-blue-500/10 transition-all"></div>
        </div>

        {/* Reconciliation Engine */}
        <div className="lg:col-span-12 xl:col-span-5 card border-blue-500/10 bg-gradient-to-br from-slate-950 to-blue-950/20 overflow-hidden relative group">
          <div className="p-8 space-y-6 relative z-10">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-emerald-500/10 rounded-2xl flex items-center justify-center border border-emerald-500/20 group-hover:bg-emerald-500/20 transition-all">
                  <RefreshCw className="text-emerald-400" size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-black text-white uppercase tracking-tighter">Sync Recon</h2>
                  <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Internal Order Matching</span>
                </div>
              </div>
              <div className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest ${reconStatus?.total_mismatches === 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                {reconStatus?.total_mismatches === 0 ? 'SYNCHRONIZED' : 'MISMATCH DETECTED'}
              </div>
            </div>

            <div className="space-y-5 pt-4">
              <div className="flex justify-between items-center">
                <span className="text-[11px] font-bold text-slate-400 uppercase">Total Variance</span>
                <span className={`text-2xl font-black font-mono ${reconStatus?.total_mismatches === 0 ? 'text-white' : 'text-rose-400'}`}>
                  {reconStatus?.total_mismatches || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[11px] font-bold text-slate-400 uppercase">Pos Diff</span>
                <span className="text-xl font-black font-mono text-white tracking-widest">
                  {reconStatus?.position_mismatches || 0}
                </span>
              </div>

              <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                <div className="flex items-center gap-3 mb-2">
                  <CheckCircle2 size={14} className="text-emerald-400" />
                  <span className="text-[10px] font-black text-slate-300 uppercase tracking-widest">Engine Status</span>
                </div>
                <p className="text-[11px] text-slate-500 font-medium leading-relaxed">
                  {reconStatus?.total_mismatches === 0
                    ? "Operational reconciliation completed. All local records match exchange states perfectly."
                    : "Reconciliation drift detected. Automatic synchronization pipeline is attempting to recover state."}
                </p>
              </div>
            </div>

            <div className="flex justify-between items-center pt-2">
              <span className="text-[10px] font-mono text-slate-600">RECON_ENGINE_V1.4</span>
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Last Sync: {reconStatus?.last_sync ? format(new Date(reconStatus.last_sync), 'HH:mm:ss') : 'LIVE'}
              </span>
            </div>
          </div>
          {/* Subtle decoration */}
          <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500/10"></div>
        </div>
      </div>
    </div>
  )
}
