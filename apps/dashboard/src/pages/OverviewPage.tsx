import React, { useEffect, useState } from 'react'
import { useDashboardStore, useEventsStore } from '../store'
import { createApiClient } from '../api/client'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { formatDistanceToNow } from 'date-fns'

export const OverviewPage: React.FC = () => {
  const { botStatus, pnlToday, latency } = useDashboardStore()
  const { events } = useEventsStore()
  const [latestDecision, setLatestDecision] = useState<any>(null)
  const [pnlHistory, setPnlHistory] = useState<any[]>([])
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const decisions = await api.getDecisions(1)
        if (decisions.length > 0) {
          setLatestDecision(decisions[0])
        }

        // TODO: Fetch PnL history from API
        setPnlHistory([
          { time: '00:00', pnl: 0 },
          { time: '04:00', pnl: 120 },
          { time: '08:00', pnl: 340 },
          { time: '12:00', pnl: 220 },
          { time: '16:00', pnl: 450 },
          { time: '20:00', pnl: 380 },
          { time: '24:00', pnl: 520 },
        ])
      } catch (error) {
        console.error('Failed to fetch overview data:', error)
      }
    }

    fetchData()
  }, [api])

  const uptimeHours = botStatus?.uptime_seconds ? Math.floor(botStatus.uptime_seconds / 3600) : 0
  const uptimeMinutes = botStatus?.uptime_seconds ? Math.floor((botStatus.uptime_seconds % 3600) / 60) : 0

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-box">
          <div className="stat-label">📍 Mode</div>
          <div className="stat-value">{botStatus?.mode || 'N/A'}</div>
          <div className="stat-change">
            {botStatus?.paused ? (
              <span className="text-yellow-400">⏸️ Paused</span>
            ) : (
              <span className="text-green-400">▶️ Running</span>
            )}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">⏱️ Uptime</div>
          <div className="stat-value">{uptimeHours}h {uptimeMinutes}m</div>
          <div className="stat-change">{botStatus?.total_positions || 0} positions active</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">💰 P&L Today</div>
          <div className={`stat-value ${pnlToday >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${pnlToday.toFixed(2)}
          </div>
          <div className="stat-change">{botStatus?.total_orders || 0} orders open</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">🔌 Latency</div>
          <div className="stat-value">{latency?.ws_p95 || 0}ms</div>
          <div className="stat-change">REST: {latency?.rest_p95 || 0}ms</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* P&L Chart */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-bold">📈 PnL Trend</h2>
          </div>
          <div className="card-body pt-0">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={pnlHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                  labelStyle={{ color: '#e2e8f0' }}
                />
                <Legend wrapperStyle={{ color: '#9ca3af' }} />
                <Line 
                  type="monotone" 
                  dataKey="pnl" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Latest Decision */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-bold">Latest Decision</h2>
          </div>
          <div className="card-body">
            {latestDecision ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Symbol:</span>
                  <span className="font-mono text-white">{latestDecision.symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Action:</span>
                  <span className={`font-bold ${latestDecision.action === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                    {latestDecision.action}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Confidence:</span>
                  <span className="text-white">{(latestDecision.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Regime:</span>
                  <span className="text-white">{latestDecision.regime}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Trace ID:</span>
                  <span className="font-mono text-blue-400 text-xs">{latestDecision.trace_id.substring(0, 16)}...</span>
                </div>
              </div>
            ) : (
              <p className="text-slate-400">No decisions yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Events */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-xl font-bold">Recent Events</h2>
        </div>
        <div className="card-body">
          <div className="space-y-2 max-h-64 overflow-auto">
            {events.slice(0, 10).map((event) => (
              <div
                key={event.id}
                className={`p-3 rounded text-sm flex justify-between items-start ${
                  event.level === 'error'
                    ? 'bg-red-900/20 text-red-300'
                    : event.level === 'warning'
                    ? 'bg-yellow-900/20 text-yellow-300'
                    : 'bg-slate-700 text-slate-300'
                }`}
              >
                <span>{event.message}</span>
                <span className="text-xs text-slate-400">
                  {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
