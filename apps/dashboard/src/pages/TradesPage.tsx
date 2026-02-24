import React, { useEffect, useState } from 'react'
import { createApiClient } from '../api/client'
import { formatDistanceToNow } from 'date-fns'

export const TradesPage: React.FC = () => {
  const [trades, setTrades] = useState<any[]>([])
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null)
  const [traceDetails, setTraceDetails] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        const decisions = await api.getDecisions(50)
        setTrades(decisions || [])
      } catch (error) {
        console.error('Failed to fetch trades:', error)
      }
    }

    fetchDecisions()
  }, [api])

  const handleViewTrace = async (traceId: string) => {
    setLoading(true)
    try {
      const trace = await api.getDecisionTrace(traceId)
      setTraceDetails(trace)
      setSelectedTrace(traceId)
    } catch (error) {
      console.error('Failed to fetch trace:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Trade History</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trades List */}
        <div className="lg:col-span-2 card">
          <div className="card-body">
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Action</th>
                    <th className="text-right">Confidence</th>
                    <th>Regime</th>
                    <th>Time</th>
                    <th className="text-center">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trade) => (
                    <tr
                      key={trade.id}
                      className={`cursor-pointer ${
                        selectedTrace === trade.trace_id ? 'bg-slate-700/50' : ''
                      }`}
                      onClick={() => handleViewTrace(trade.trace_id)}
                    >
                      <td className="font-mono">{trade.symbol}</td>
                      <td className={`font-semibold ${
                        trade.action === 'BUY' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {trade.action}
                      </td>
                      <td className="text-right">{(trade.confidence * 100).toFixed(0)}%</td>
                      <td>{trade.regime}</td>
                      <td className="text-xs text-slate-400">
                        {formatDistanceToNow(new Date(trade.timestamp), { addSuffix: true })}
                      </td>
                      <td className="text-center">
                        <button
                          onClick={() => handleViewTrace(trade.trace_id)}
                          className="text-blue-400 hover:text-blue-300 font-mono text-xs"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Trace Details */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-bold">Trace Details</h2>
          </div>
          <div className="card-body max-h-96 overflow-auto">
            {loading ? (
              <p className="text-slate-400">Loading...</p>
            ) : traceDetails ? (
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-slate-400">Trace ID:</span>
                  <p className="font-mono text-blue-400 break-all">{traceDetails.trace_id}</p>
                </div>
                <div>
                  <span className="text-slate-400">Decision:</span>
                  <pre className="bg-slate-900 p-2 rounded text-xs text-slate-300 mt-1 overflow-auto max-h-40">
                    {JSON.stringify(traceDetails.decision_json, null, 2)}
                  </pre>
                </div>
                <div>
                  <span className="text-slate-400">Risk Check:</span>
                  <p className="text-white">
                    {traceDetails.risk_passed ? '✅ Passed' : '❌ Failed'}
                  </p>
                </div>
                <div>
                  <span className="text-slate-400">Order ID:</span>
                  <p className="font-mono text-slate-300">{traceDetails.order_id || 'N/A'}</p>
                </div>
              </div>
            ) : (
              <p className="text-slate-400">Select a trade to view details</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
