import React, { useEffect, useState } from 'react'
import { useEventsStore } from '../store'
import { createApiClient } from '../api/client'
import { formatDistanceToNow } from 'date-fns'

export const EventsPage: React.FC = () => {
  const { events } = useEventsStore()
  const [auditLog, setAuditLog] = useState<any[]>([])
  const [filter, setFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all')
  const [loading, setLoading] = useState(false)
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchAuditLog = async () => {
      setLoading(true)
      try {
        const logs = await api.getAuditLog(100, 0)
        setAuditLog(logs || [])
      } catch (error) {
        console.error('Failed to fetch audit log:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAuditLog()
    const interval = setInterval(fetchAuditLog, 10000)
    return () => clearInterval(interval)
  }, [api])

  const filteredEvents = events.filter((e) => filter === 'all' || e.level === filter)

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Events & Audit</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Events Timeline */}
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h2 className="text-xl font-bold">System Events</h2>
            <div className="flex gap-2">
              {(['all', 'error', 'warning', 'info'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`btn btn-sm ${
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

          <div className="card-body max-h-96 overflow-auto">
            <div className="space-y-2">
              {filteredEvents.length === 0 ? (
                <p className="text-slate-400 text-sm text-center py-4">No events</p>
              ) : (
                filteredEvents.map((event) => (
                  <div
                    key={event.id}
                    className={`alert ${
                      event.level === 'error'
                        ? 'alert-danger'
                        : event.level === 'warning'
                        ? 'alert-warning'
                        : 'alert-info'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {event.level === 'error' && '🔴'}
                        {event.level === 'warning' && '🟡'}
                        {event.level === 'info' && '🔵'}
                      </div>
                      <div className="flex-1">
                        <p>{event.message}</p>
                        <p className="text-xs text-slate-400 mt-1">
                          {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Audit Log */}
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h2 className="text-xl font-bold">Audit Log</h2>
            {loading && <span className="text-xs text-slate-400">Updating...</span>}
          </div>

          <div className="card-body max-h-96 overflow-auto">
            <div className="space-y-2">
              {auditLog.length === 0 ? (
                <p className="text-slate-400 text-sm text-center py-4">No audit entries</p>
              ) : (
                auditLog.map((log, idx) => (
                  <div key={idx} className="p-3 bg-slate-700/50 rounded-lg border border-slate-600/50 text-sm">
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-semibold text-slate-200">{log.action}</span>
                      <span className="text-xs text-slate-500">
                        {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      <p>Actor: <span className="text-slate-300">{log.actor}</span></p>
                      <p>Target: <span className="text-slate-300">{log.target}</span></p>
                      {log.details_json && (
                        <p className="mt-1 text-slate-500 font-mono break-all">
                          {JSON.stringify(log.details_json).substring(0, 100)}...
                        </p>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Timeline View */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-xl font-bold">Command Timeline</h2>
        </div>
        <div className="card-body">
          <div className="space-y-4">
            {auditLog
              .filter((log) => log.action.includes('_'))
              .slice(0, 20)
              .map((log, idx) => (
                <div key={idx} className="flex gap-4">
                  <div className="w-32 text-xs text-slate-400 flex-shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="flex-1">
                    <div className="text-white font-semibold">{log.action}</div>
                    <div className="text-sm text-slate-400">
                      {log.actor} → {log.target}
                    </div>
                  </div>
                  <div className="text-xs px-2 py-1 rounded bg-slate-700">
                    {log.details_json?.status || '?'}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}
