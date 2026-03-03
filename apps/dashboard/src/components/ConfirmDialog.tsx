import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  type?: 'danger' | 'warning' | 'info'
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmText = 'Xác nhận',
  cancelText = 'Hủy',
  onConfirm,
  onCancel,
  type = 'danger'
}) => {
  if (!isOpen) return null

  const getColors = () => {
    switch (type) {
      case 'danger':
        return {
          border: 'border-rose-500/30',
          bg: 'bg-rose-500/10',
          icon: 'text-rose-400',
          button: 'bg-rose-500 hover:bg-rose-600'
        }
      case 'warning':
        return {
          border: 'border-amber-500/30',
          bg: 'bg-amber-500/10',
          icon: 'text-amber-400',
          button: 'bg-amber-500 hover:bg-amber-600'
        }
      case 'info':
        return {
          border: 'border-blue-500/30',
          bg: 'bg-blue-500/10',
          icon: 'text-blue-400',
          button: 'bg-blue-500 hover:bg-blue-600'
        }
    }
  }

  const colors = getColors()

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 animate-fadeIn">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
        onClick={onCancel}
      ></div>

      {/* Dialog */}
      <div className="relative bg-[#0f172a] border border-white/10 rounded-3xl shadow-2xl max-w-md w-full animate-slideUp">
        {/* Close button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
        >
          <X size={20} />
        </button>

        {/* Content */}
        <div className="p-8 space-y-6">
          {/* Icon & Title */}
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-2xl ${colors.bg} border ${colors.border}`}>
              <AlertTriangle className={colors.icon} size={24} />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-black text-white mb-2">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{message}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="flex-1 px-6 py-3 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-bold transition-all border border-white/10"
            >
              {cancelText}
            </button>
            <button
              onClick={onConfirm}
              className={`flex-1 px-6 py-3 rounded-2xl ${colors.button} text-white font-bold transition-all border border-white/20 shadow-lg`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
