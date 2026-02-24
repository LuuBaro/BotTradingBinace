import React, { useEffect, useState } from 'react'
import { useDashboardStore } from '../store'
import { createApiClient } from '../api/client'
import { formatDistanceToNow } from 'date-fns'

export const OrdersPage: React.FC = () => {
  const { orders } = useDashboardStore()
  const [filter, setFilter] = useState<'open' | 'filled' | 'cancelled' | 'all'>('all')
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        await api.getOrders()
      } catch (error) {
        console.error('Failed to fetch orders:', error)
      }
    }

    fetchOrders()
    const interval = setInterval(fetchOrders, 5000)
    return () => clearInterval(interval)
  }, [api])

  const filteredOrders = orders.filter((o) => {
    if (filter === 'all') return true
    return o.status.toLowerCase() === filter.toLowerCase()
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Orders ({orders.length})</h1>
        <div className="flex gap-2">
          {(['all', 'open', 'filled', 'cancelled'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`btn ${
                filter === f
                  ? 'btn-primary'
                  : 'btn-secondary'
              } capitalize`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {filteredOrders.length === 0 ? (
        <div className="card">
          <div className="card-body text-center py-12 text-slate-400">No {filter} orders</div>
        </div>
      ) : (
        <div className="card">
          <div className="card-body">
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th className="text-right">Quantity</th>
                    <th className="text-right">Price</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.id}>
                      <td className="font-mono">{order.symbol}</td>
                      <td className={`font-semibold ${
                        order.side === 'BUY' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {order.side}
                      </td>
                      <td className="text-right">{order.quantity}</td>
                      <td className="text-right">${order.quantity}</td>
                      <td>
                        <span className={`badge ${
                          order.status === 'FILLED' ? 'badge-success' :
                          order.status === 'CANCELLED' ? 'badge-danger' :
                          'badge-warning'
                        }`}>
                          {order.status}
                        </span>
                      </td>
                      <td className="text-xs text-slate-400">
                        {formatDistanceToNow(new Date(order.created_at), { addSuffix: true })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
