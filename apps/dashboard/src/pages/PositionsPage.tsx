import React, { useEffect, useState } from 'react'
import { useDashboardStore } from '../store'
import { createApiClient } from '../api/client'

export const PositionsPage: React.FC = () => {
  const { positions } = useDashboardStore()
  const [filter, setFilter] = useState('all')
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const pos = await api.getPositions()
        // Update dashboard store
      } catch (error) {
        console.error('Failed to fetch positions:', error)
      }
    }

    fetchPositions()
    const interval = setInterval(fetchPositions, 5000)
    return () => clearInterval(interval)
  }, [api])

  const filteredPositions = positions.filter((p) => {
    if (filter === 'profit') return p.unrealized_pnl > 0
    if (filter === 'loss') return p.unrealized_pnl < 0
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Positions ({positions.length})</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('profit')}
            className={`btn ${filter === 'profit' ? 'btn-success' : 'btn-secondary'}`}
          >
            Profit
          </button>
          <button
            onClick={() => setFilter('loss')}
            className={`btn ${filter === 'loss' ? 'btn-danger' : 'btn-secondary'}`}
          >
            Loss
          </button>
        </div>
      </div>

      {filteredPositions.length === 0 ? (
        <div className="card">
          <div className="card-body text-center py-12 text-slate-400">No positions</div>
        </div>
      ) : (
        <div className="card">
          <div className="card-body">
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th className="text-right">Quantity</th>
                    <th className="text-right">Entry Price</th>
                    <th className="text-right">PnL</th>
                    <th className="text-right">%</th>
                    <th className="text-right">SL</th>
                    <th className="text-right">TP</th>
                    <th className="text-right">Leverage</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPositions.map((pos) => {
                    const pnlPercent = ((pos.unrealized_pnl / (pos.entry_price * pos.qty)) * 100).toFixed(2)
                    return (
                      <tr key={pos.id}>
                        <td className="font-mono">{pos.symbol}</td>
                        <td className="text-right">{pos.qty}</td>
                        <td className="text-right">${pos.entry_price.toFixed(2)}</td>
                        <td className={`text-right font-semibold ${
                          pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          ${pos.unrealized_pnl.toFixed(2)}
                        </td>
                        <td className={`text-right ${
                          parseFloat(pnlPercent) >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {pnlPercent}%
                        </td>
                        <td className="text-right">${pos.stop_loss?.toFixed(2) || '-'}</td>
                        <td className="text-right">${pos.take_profit?.toFixed(2) || '-'}</td>
                        <td className="text-right">{pos.leverage}x</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
