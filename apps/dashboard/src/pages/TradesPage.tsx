import React, { useEffect, useState, useMemo } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { format } from 'date-fns'
import { Brain, Shield, Zap, TrendingUp, Target, CheckCircle2, XCircle, Info, RefreshCw, ChevronRight } from 'lucide-react'

export const TradesPage: React.FC = () => {
  const [trades, setTrades] = useState<any[]>([])
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null)
  const [traceDetails, setTraceDetails] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  // Memoized API client
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        const response = await api.getDecisions(50)
        // API returns a direct array, not wrapped in { decisions: [] }
        setTrades(Array.isArray(response) ? response : [])
      } catch (error) {
        console.error('Failed to fetch trades:', error)
      }
    }

    fetchDecisions()
    const interval = setInterval(fetchDecisions, 10000)
    return () => clearInterval(interval)
  }, [api, refreshKey])

  const handleViewTrace = async (traceId: string) => {
    setLoading(true)
    try {
      const response = await api.getDecisionTrace(traceId)
      setTraceDetails(response)
      setSelectedTrace(traceId)
    } catch (error) {
      console.error('Failed to fetch trace:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const s = (status || 'unknown').toLowerCase()
    if (s === 'executed' || s === 'approved' || s === 'approved_manually') return 'badge-success'
    if (s === 'rejected' || s === 'failed') return 'badge-danger'
    if (s === 'pending' || s === 'awaiting_approval') return 'badge-info'
    return 'badge-secondary'
  }

  return (
    <div className="space-y-8 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <TrendingUp className="text-blue-400" size={24} />
            </div>
            <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Execution Engine</span>
          </div>
          <h1 className="text-5xl font-black text-gradient">Decision Insights</h1>
          <p className="text-slate-400 mt-2 max-w-xl">Deep trace exploration of AI-generated trade intents and risk validation logs.</p>
        </div>
        <button
          onClick={() => setRefreshKey(k => k + 1)}
          className="btn btn-secondary group active:scale-95"
        >
          <RefreshCw size={18} className="group-hover:rotate-180 transition-transform duration-500" />
          Synchronize
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Decisions List - Mission Control Table */}
        <div className="lg:col-span-12 xl:col-span-7 space-y-4">
          <div className="card glass-dark border-white/5 shadow-2xl overflow-hidden">
            <div className="table-container p-0 border-none">
              <table className="table">
                <thead>
                  <tr className="bg-white/5">
                    <th className="rounded-tl-xl">Time (UTC)</th>
                    <th>Asset</th>
                    <th>Neural Intent</th>
                    <th className="text-right">Sizing / Lev</th>
                    <th className="rounded-tr-xl">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {trades.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-24">
                        <div className="flex flex-col items-center gap-4 opacity-30">
                          <Info size={48} />
                          <p className="text-sm font-bold uppercase tracking-widest">No neural traces recorded</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    trades.map((trade) => (
                      <tr
                        key={trade.id}
                        className={`cursor-pointer group transition-all duration-300 hover:bg-white/5 ${selectedTrace === trade.trace_id ? 'bg-blue-600/10 border-l-4 border-l-blue-500' : ''
                          }`}
                        onClick={() => handleViewTrace(trade.trace_id)}
                      >
                        <td className="text-xs font-mono text-slate-500">
                          {format(new Date(trade.timestamp), 'HH:mm:ss.SSS')}
                        </td>
                        <td className="font-black font-mono text-blue-100 italic">{trade.symbol}</td>
                        <td className="relative">
                          <span className={`text-[10px] font-black uppercase tracking-widest flex items-center gap-2 ${trade.status === 'REJECTED' ? 'text-rose-500' :
                              trade.action === 'OPEN' ? 'text-emerald-400' :
                                trade.action === 'CLOSE' ? 'text-rose-400' : 'text-slate-400'
                            }`}>
                            {trade.action === 'OPEN' && trade.status !== 'REJECTED' ? <Zap size={10} className="fill-current" /> : null}
                            {trade.status === 'REJECTED' ? 'BỊ TỪ CHỐI' :
                              trade.action === 'OPEN' ? 'VÀO LỆNH' :
                                trade.action === 'CLOSE' ? 'ĐÓNG LỆNH' : 'QUAN SÁT'}
                          </span>
                        </td>
                        <td className="text-right">
                          <div className="flex flex-col items-end">
                            <span className="text-[11px] font-black text-white font-mono">
                              {((trade.decision_json?.size_pct || 0) * 100).toFixed(1)}% / {trade.decision_json?.leverage || 1}x
                            </span>
                            <span className="text-[9px] text-slate-500 uppercase font-bold">Allocated</span>
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center gap-3 justify-end lg:justify-start">
                            <span className={`badge ${getStatusBadge(trade.status)}`}>
                              {trade.status}
                            </span>
                            <ChevronRight size={14} className={`text-slate-700 transition-transform ${selectedTrace === trade.trace_id ? 'translate-x-1 text-blue-500' : 'group-hover:translate-x-1'}`} />
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Trace Details Panel - Neural Inspector */}
        <div className="lg:col-span-12 xl:col-span-5 lg:sticky lg:top-8">
          <div className="card glass-dark border-white/10 shadow-3xl h-[85vh] flex flex-col animate-slideUp">
            <div className="p-8 border-b border-white/5 flex items-center justify-between">
              <div className="flex flex-col">
                <h2 className="text-2xl font-black tracking-tighter text-white">Neural Inspector</h2>
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  Active Trace: <span className="text-blue-400">{selectedTrace ? selectedTrace.slice(0, 12) : 'NONE'}</span>
                </span>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20">
                <Brain className="text-blue-400" size={24} />
              </div>
            </div>

            <div className="p-8 overflow-y-auto flex-grow custom-scrollbar space-y-10">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-6 opacity-50">
                  <div className="spinner w-12 h-12"></div>
                  <div className="text-center">
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-400 animate-pulse">Decompressing Trace Logs</p>
                    <p className="text-[10px] text-slate-500 mt-2">Connecting to distributed memory cluster...</p>
                  </div>
                </div>
              ) : traceDetails ? (
                <div className="space-y-10 animate-fadeIn">
                  {/* AI Rationale - The "Why" */}
                  <section className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Info size={14} className="text-blue-400" />
                      <h3 className="text-[11px] font-black text-blue-400 uppercase tracking-widest">Strategic Rationale</h3>
                    </div>
                    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 relative group">
                      <div className="absolute top-0 left-4 w-px h-full bg-gradient-to-b from-blue-500/40 via-blue-500/10 to-transparent"></div>
                      <p className="text-sm text-slate-300 leading-relaxed pl-6 italic font-medium">
                        "{traceDetails.decision.rationale || traceDetails.decision.decision_json?.rationale || 'Neural network provided zero-sum rationale for this specific intent sequence.'}"
                      </p>
                    </div>
                  </section>

                  {/* Context Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-5 bg-white/5 rounded-2xl border border-white/5 group hover:border-blue-500/20 transition-colors">
                      <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-2">Market Regime</span>
                      <div className="flex items-center gap-2">
                        <Target size={14} className="text-amber-400" />
                        <span className="text-sm font-black text-white uppercase">{traceDetails.decision.regime}</span>
                      </div>
                    </div>
                    <div className="p-5 bg-white/5 rounded-2xl border border-white/5 group hover:border-blue-500/20 transition-colors">
                      <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-2">Neural Confidence</span>
                      <div className="flex items-center gap-3">
                        <div className="flex-grow h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="bg-blue-500 h-full shadow-[0_0_10px_rgba(59,130,246,0.6)]"
                            style={{ width: `${(traceDetails.decision.confidence * 100)}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-black font-mono">{(traceDetails.decision.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Action Rejection Hub - IF AWAITING APPROVAL */}
                  {traceDetails.decision.status === 'AWAITING_APPROVAL' && (
                    <div className="p-8 rounded-3xl bg-gradient-to-br from-blue-500/20 via-slate-900 to-slate-900 border border-blue-500/30 shadow-2xl relative overflow-hidden group">
                      <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                        <Shield size={120} />
                      </div>
                      <div className="relative space-y-6">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-blue-500/20 rounded-xl flex items-center justify-center border border-blue-500/30">
                            <Shield size={20} className="text-blue-400" />
                          </div>
                          <div>
                            <h4 className="text-lg font-black text-white tracking-tight">Pending Approval</h4>
                            <p className="text-[10px] text-blue-400 uppercase font-black tracking-widest">Operator Override Active</p>
                          </div>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed font-medium">
                          The Risk Engine has passed this trade, but manual gatekeeping is active. Review the rationale above before finalizing execution.
                        </p>
                        <div className="flex gap-3">
                          <button
                            onClick={async () => {
                              try {
                                await api.approveDecision(selectedTrace!)
                                handleViewTrace(selectedTrace!) // Refresh details
                              } catch (e) {
                                alert('Failed to approve decision')
                              }
                            }}
                            className="btn btn-primary flex-1 shadow-2xl shadow-blue-500/20 border border-blue-400/30"
                          >
                            <CheckCircle2 size={16} />
                            Confirm & Deploy
                          </button>
                          <button className="btn btn-secondary border-rose-500/20 hover:bg-rose-500/10 hover:text-rose-400">
                            <XCircle size={16} />
                            Deny
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Advanced Audit Logs */}
                  <section className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="text-[11px] font-black text-blue-400 uppercase tracking-widest">Validation Integrity</h3>
                      <span className="text-[10px] font-mono text-slate-600 italic">BLOCK_ID: {traceDetails.decision.id}</span>
                    </div>

                    <div className={`p-6 rounded-2xl border-l-[6px] ${traceDetails.decision.risk_passed ? 'bg-emerald-500/5 border-l-emerald-500/50' : 'bg-rose-500/5 border-l-rose-500/50'}`}>
                      <div className="flex items-center gap-3 mb-4">
                        {traceDetails.decision.risk_passed ? <CheckCircle2 size={18} className="text-emerald-400" /> : <XCircle size={18} className="text-rose-400" />}
                        <span className="text-sm font-black uppercase tracking-tight">Risk Guard: {traceDetails.decision.risk_passed ? 'APPROVED' : 'REJECTED'}</span>
                      </div>
                      <div className="bg-slate-950/40 p-4 rounded-xl text-xs font-mono text-slate-400 border border-white/5">
                        {traceDetails.decision.risk_approval_reason || 'NO_AUDIT_LOG_ENTRY_FOUND'}
                      </div>
                    </div>

                    {/* Sequential Events */}
                    <div className="space-y-3">
                      <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block px-2">Sequential Event Stack</span>
                      <div className="space-y-2">
                        {traceDetails.events && traceDetails.events.map((ev: any, idx: number) => (
                          <div key={ev.id || idx} className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/5 rounded-xl group hover:bg-white/5 transition-colors">
                            <div className="flex items-center gap-3">
                              <div className={`w-1.5 h-1.5 rounded-full ${ev.level === 'INFO' ? 'bg-blue-400' : 'bg-rose-400'}`}></div>
                              <span className="text-[10px] font-mono text-slate-300">{ev.code}</span>
                            </div>
                            <span className="text-[9px] text-slate-600">{format(new Date(ev.timestamp), 'HH:mm:ss')}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </section>

                  {/* Inspector Footer */}
                  <div className="pt-10 border-t border-white/5 opacity-30 group hover:opacity-100 transition-opacity">
                    <div className="flex justify-between items-center text-[8px] font-mono text-slate-500 uppercase tracking-[0.3em]">
                      <span>Neural Trace v4.2.1</span>
                      <span>Region: {(traceDetails.decision.symbol || traceDetails.decision.decision_json?.symbol || 'N/A').slice(0, 3).toUpperCase()}_DOCK</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full gap-8 opacity-20">
                  <div className="w-24 h-24 border-2 border-dashed border-slate-600 rounded-3xl flex items-center justify-center animate-float">
                    <Target size={40} className="text-slate-400" />
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-sm font-black uppercase tracking-[0.3em]">Ready for Analysis</p>
                    <p className="text-xs">Select a decision hash from the terminal to begin deep inspection.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

