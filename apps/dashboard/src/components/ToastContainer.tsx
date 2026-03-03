import React, { useEffect, useState } from 'react'
import { toast as toastManager, Toast } from '../utils/toast'
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react'

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    const unsubscribe = toastManager.subscribe(setToasts)
    return unsubscribe
  }, [])

  const getIcon = (type: Toast['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5" />
      case 'error':
        return <XCircle className="w-5 h-5" />
      case 'warning':
        return <AlertCircle className="w-5 h-5" />
      case 'info':
        return <Info className="w-5 h-5" />
    }
  }

  const getColors = (type: Toast['type']) => {
    switch (type) {
      case 'success':
        return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
      case 'error':
        return 'bg-rose-500/10 border-rose-500/30 text-rose-400'
      case 'warning':
        return 'bg-amber-500/10 border-amber-500/30 text-amber-400'
      case 'info':
        return 'bg-blue-500/10 border-blue-500/30 text-blue-400'
    }
  }

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            pointer-events-auto
            flex items-center gap-3
            px-5 py-4 rounded-2xl
            border backdrop-blur-xl
            shadow-2xl
            animate-slideInRight
            min-w-[300px] max-w-md
            ${getColors(toast.type)}
          `}
          style={{
            animation: 'slideInRight 0.3s ease-out'
          }}
        >
          {getIcon(toast.type)}
          <span className="flex-1 font-medium text-sm">{toast.message}</span>
          <button
            onClick={() => toastManager.remove(toast.id)}
            className="opacity-50 hover:opacity-100 transition-opacity"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        .animate-slideInRight {
          animation: slideInRight 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
