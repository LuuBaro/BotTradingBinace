import React, { useState, useEffect, useMemo } from 'react'
import { useConfigStore, useAuthStore } from '../store'
import { useLocation } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Save, RotateCcw, History, AlertTriangle, CheckCircle2, Cpu, Lock, Terminal, ShieldCheck, ChevronRight, Info, X } from 'lucide-react'
import { format } from 'date-fns'

export const RiskConfigPage: React.FC = () => {
  const { currentConfig, setConfig, versions, setVersions } = useConfigStore()
  const { user } = useAuthStore()
  const location = useLocation()
  const [editedConfig, setEditedConfig] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [riskLogs, setRiskLogs] = useState<any[]>([])
  const [selectedVersion, setSelectedVersion] = useState<any | null>(null)

  const formatVnDate = (iso: string) => {
    const d = new Date(iso)
    return new Intl.DateTimeFormat('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(d)
  }

  const formatVnTime = (iso: string) => {
    const d = new Date(iso)
    return new Intl.DateTimeFormat('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(d)
  }

  // Memoized API client
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token, location.search])

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true)
        const [config, vers, logs] = await Promise.all([
          api.getRiskConfig(),
          api.getRiskConfigVersions(),
          api.getRiskLogs(20)
        ])
        console.log('📋 Loaded risk config:', config)
        console.log('📊 Loaded versions:', vers)
        setConfig(config)
        setVersions(vers)
        setRiskLogs(logs || [])
        setEditedConfig({ ...config })
      } catch (error) {
        console.error('Failed to fetch config:', error)
        setMessage({ type: 'error', text: 'Failed to synchronize with Global Risk Cluster' })
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [api, setConfig, setVersions])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.updateRiskConfig(editedConfig)
      setConfig(updated)
      setMessage({ type: 'success', text: 'Risk parameters successfully updated and deployed.' })
      setTimeout(() => setMessage(null), 4000)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Verification failed during deployment' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-40 gap-6 opacity-50 bg-mesh min-h-screen">
        <div className="spinner w-12 h-12"></div>
        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-400 animate-pulse">Decrypting Risk Vault</p>
      </div>
    )
  }

  return (
    <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
      {/* Header Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <ShieldCheck className="text-blue-400" size={24} />
            </div>
            <span className="text-[10px] font-black text-blue-400 uppercase tracking-[0.3em]">Guardian Protocol</span>
          </div>
          <h1 className="text-5xl font-black text-gradient">Risk Vault</h1>
          <p className="text-slate-400 max-w-xl font-medium">Fine-tune the neural guardrails and execution limits for autonomous trading cycles.</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="px-5 py-3 glass-dark border-white/5 rounded-2xl flex items-center gap-3">
            <div className="w-8 h-8 bg-amber-500/10 rounded-lg flex items-center justify-center border border-amber-500/20">
              <Lock className="text-amber-400" size={16} />
            </div>
            <div>
              <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block">Access Level</span>
              <span className="text-xs font-black text-white uppercase font-mono">
                {user?.role === 'admin' ? 'SECURE_ADMIN_ACCESS_LVL_1' : 'RESTRICTED_ACCESS_LVL_0'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {message && (
        <div className={`p-5 rounded-2xl border-l-[6px] animate-slideInRight shadow-2xl flex items-center gap-4 ${message.type === 'success'
          ? 'glass-dark border-emerald-500/50 bg-emerald-500/5 text-emerald-100 shadow-emerald-500/10'
          : 'glass-dark border-rose-500/50 bg-rose-500/5 text-rose-100 shadow-rose-500/10'
          }`}>
          {message.type === 'success' ? <CheckCircle2 size={20} className="text-emerald-400" /> : <AlertTriangle size={20} className="text-rose-400" />}
          <p className="text-sm font-bold tracking-tight">{message.text}</p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 items-start">
        {/* Config Editor - Neural Parameters */}
        <div className="xl:col-span-8 flex flex-col gap-6 xl:sticky xl:top-8">
          <div className="card glass-dark border-white/5 shadow-3xl overflow-hidden relative flex flex-col h-full">
            <div className="p-8 border-b border-white/5 bg-white/[0.01]">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <Cpu className="text-blue-400" size={20} />
                  <h2 className="text-xl font-black text-white uppercase tracking-tight">Active Parameters</h2>
                </div>
                <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">NODE_ID: DC-88-ALPHA</span>
              </div>
            </div>

            <div className="p-10 flex-grow">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
                {editedConfig && Object.entries(editedConfig).length > 0 ? (
                  Object.entries(editedConfig).map(([key, value]: [string, any]) => {
                    const isObject = typeof value === 'object' && value !== null;
                    const displayValue = isObject ? JSON.stringify(value) : value;

                    const displayKey = key
                      .replace(/([A-Z])/g, ' $1')
                      .replace(/_/g, ' ')
                      .trim()
                      .split(' ')
                      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
                      .join(' ')

                    const meta: Record<string, { unit: string, desc: string }> = {
                      max_leverage: { unit: 'x', desc: 'Hệ số đòn bẩy tối đa cho mỗi vị thế (VD: 5 = đòn bẩy 5x)' },
                      max_position_size: { unit: '%', desc: 'Kích thước lệnh (vol) tối đa tính theo phần trăm tổng số dư khả dụng (VD: 0.1 = 10% ví)' },
                      max_position_pct: { unit: '%', desc: 'Kích thước lệnh (vol) tối đa tính theo phần trăm tổng số dư khả dụng (VD: 0.1 = 10% ví)' },
                      max_daily_loss: { unit: '%', desc: 'Mức thua lỗ tối đa cho phép trong ngày, tính theo % số dư (VD: 0.02 = ngừng trade nếu lỗ 2%)' },
                      max_drawdown_day_pct: { unit: '%', desc: 'Giới hạn sụt giảm vốn (drawdown) tối đa trong ngày tính theo % tổng số dư' },
                      min_win_rate: { unit: '%', desc: 'Tỷ lệ thắng (Win rate) tối thiểu hệ thống phải giữ để tiếp tục giao dịch' },
                      max_risk_per_trade_pct: { unit: '%', desc: 'Mức rủi ro vốn lớn nhất trên MỘT lệnh dựa trên số dư (VD: 0.02 = rủi ro 2% tài khoản cho 1 lệnh)' },
                      max_orders_per_hour: { unit: 'Lệnh', desc: 'Số lượng lệnh giao dịch (vào lệnh) tối đa được thực hiện trong khoảng thời gian một giờ' },
                      max_concurrent_positions: { unit: 'Lệnh', desc: 'Số lệnh (vị thế) đang chạy cùng lúc tối đa' },
                      cooldown_after_loss: { unit: 'Giây', desc: 'Thời gian treo máy (tạm nghỉ) tính bằng giây sau khi dính 1 lệnh stoploss' },
                      mandatory_sl_tp: { unit: 'Bật/Tắt', desc: 'Bắt buộc mọi vị thế mở do AI tạo ra đều phải cài sẵn Cắt lỗ (SL) và Chốt lời (TP)' }
                    }

                    const fieldMeta = meta[key.toLowerCase()] || { unit: typeof value === 'number' ? 'NUM' : 'VAL', desc: 'Thông số hệ thống nâng cao' };

                    return (
                      <div key={key} className="space-y-3 group">
                        <div className="flex justify-between items-center px-1">
                          <div className="relative group/tooltip">
                            <label
                              className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] group-focus-within:text-blue-400 transition-colors flex items-center gap-2 cursor-help"
                            >
                              {displayKey}
                              <Info size={12} className="opacity-50 group-hover/tooltip:opacity-100 group-hover/tooltip:text-blue-400 transition-all" />
                            </label>
                            {/* Custom Tooltip */}
                            <div className="absolute left-0 bottom-full mb-2 hidden group-hover/tooltip:block z-50 w-[240px] pointer-events-none">
                              <div className="bg-slate-900 border border-white/10 p-3 rounded-lg shadow-2xl backdrop-blur-md">
                                <p className="text-[11px] font-medium leading-relaxed text-slate-300 normal-case tracking-normal">{fieldMeta.desc}</p>
                              </div>
                              <div className="absolute -bottom-1 left-4 w-2 h-2 bg-slate-900 border-r border-b border-white/10 transform rotate-45"></div>
                            </div>
                          </div>
                          <span className="text-[9px] font-mono text-slate-700 opacity-0 group-hover:opacity-100 transition-opacity uppercase">{typeof value}</span>
                        </div>
                        <div className="relative">
                          <input
                            type={typeof value === 'number' ? 'number' : 'text'}
                            value={displayValue}
                            onChange={(e) => {
                              let newVal: any = e.target.value;
                              if (typeof value === 'number') {
                                // Strip leading zeros to fix the '010' issue user encountered
                                if (newVal.length > 1 && newVal.startsWith('0') && !newVal.startsWith('0.')) {
                                  newVal = newVal.replace(/^0+/, '');
                                  if (newVal === '') newVal = '0';
                                }
                                newVal = newVal === '' ? '' : Number(newVal);
                              } else if (isObject) {
                                try {
                                  newVal = JSON.parse(e.target.value);
                                } catch (err) {
                                  // Keep as string if invalid JSON during typing
                                }
                              }
                              setEditedConfig({
                                ...editedConfig,
                                [key]: newVal,
                              })
                            }}
                            className="w-full bg-slate-950/50 border border-white/5 py-3 px-5 rounded-2xl text-white font-bold font-mono outline-none transition-all text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 group-hover:bg-slate-900/50 cursor-text"
                            step={typeof value === 'number' && Math.abs(value) < 1 ? '0.01' : '1'}
                          />
                          <div
                            className="absolute right-4 top-1/2 -translate-y-1/2 opacity-30 text-[10px] font-black uppercase pointer-events-none"
                            title={fieldMeta.desc}
                          >
                            {fieldMeta.unit}
                          </div>
                        </div>
                      </div>
                    )
                })
              ) : (
                <div className="col-span-2 py-20 text-center opacity-30 select-none">
                  <Terminal size={40} className="mx-auto mb-4" />
                  <p className="text-xs font-black uppercase tracking-[0.3em]">No valid parameters detected</p>
                </div>
              )}
            </div>
          </div>
            
          <div className="p-10 pt-0">
            <div className="flex gap-4 pt-10 border-t border-white/5">
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn btn-primary flex-[2] py-4 rounded-2xl shadow-xl shadow-blue-500/20 active:scale-[0.98] disabled:opacity-50 group overflow-hidden min-h-[56px] relative"
              >
                <div className="relative z-10 flex items-center justify-center gap-3">
                  {saving ? (
                    <div className="spinner w-4 h-4 border-2"></div>
                  ) : (
                    <Save size={18} className="group-hover:scale-110 transition-transform" />
                  )}
                  <span className="font-black uppercase tracking-widest text-xs">
                    {saving ? 'Broadcasting...' : 'Apply Deployment Changes'}
                  </span>
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </button>
              <button
                onClick={() => setEditedConfig({ ...currentConfig })}
                className="flex-1 py-4 glass-dark border-white/10 rounded-2xl text-slate-400 hover:text-white transition-all flex items-center justify-center gap-3 font-bold text-xs uppercase tracking-widest active:scale-95 min-h-[56px]"
              >
                <RotateCcw size={18} />
                Reset
              </button>
            </div>
          </div>

            {/* Subtle background glow */}
            <div className="absolute bottom-0 right-0 w-[50%] h-[50%] bg-blue-500/[0.01] blur-[120px] pointer-events-none"></div>
          </div>

          <div className="p-6 glass-dark border border-white/5 rounded-3xl flex items-center gap-4 text-slate-500">
            <AlertTriangle size={20} className="text-amber-500 shrink-0" />
            <p className="text-[10px] font-bold uppercase tracking-wide leading-relaxed">
              <span className="text-amber-400">Security Warning:</span> Modifying risk parameters directly affects the neural execution engine's ability to minimize capital loss. Drastic changes should only be made following systemic review of backtest traces.
            </p>
          </div>
        </div>

        {/* Version History - Registry Timeline */}
        <div className="xl:col-span-4 flex flex-col gap-6">
          <div className="card glass-dark border-white/5 shadow-2xl h-full relative overflow-hidden flex flex-col">
            <div className="p-8 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
              <div className="flex items-center gap-3">
                <History className="text-blue-400" size={20} />
                <h2 className="text-xl font-black text-white uppercase tracking-tight text-gradient">Audit History</h2>
              </div>
              <div className="p-2 bg-white/5 rounded-lg border border-white/5">
                <Terminal size={12} className="text-slate-500" />
              </div>
            </div>
            <div className="p-4 flex-grow overflow-y-auto custom-scrollbar">
              <div className="space-y-4">
                {versions.length === 0 ? (
                  <div className="py-20 flex flex-col items-center gap-4 opacity-20">
                    <Lock size={40} />
                    <p className="text-xs font-black uppercase tracking-[0.2em] text-center">No previous states found in registry</p>
                  </div>
                ) : (
                  versions.map((version) => (
                    <div
                      key={version.id}
                      className="p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all group relative animate-slideUp"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 group-hover:animate-ping"></span>
                            <span className="text-[10px] font-black font-mono text-blue-400 uppercase tracking-tighter">REGISTRY_ID: {version.id.substring(0, 12)}</span>
                          </div>
                          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                            {formatVnDate(version.created_at)} · {formatVnTime(version.created_at)} (GMT+7)
                          </p>
                        </div>
                      </div>

                      <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 italic">
                        <p className="text-[11px] text-slate-400 leading-relaxed font-medium line-clamp-2 italic">"{version.description || 'System-generated snapshot following parameter recalibration.'}"</p>
                      </div>

                      <div className="mt-4 flex items-center justify-between text-[8px] font-black uppercase tracking-[0.2em] text-slate-600">
                        <span>Author: {version.created_by.toUpperCase() || 'SYSTEM_CORE'}</span>
                        <button
                          onClick={() => setSelectedVersion(version)}
                          className="flex items-center gap-1 group-hover:text-blue-400 transition-colors"
                        >
                          <span>Inspect JSON</span>
                          <ChevronRight size={10} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            {/* Background Glow */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 blur-3xl opacity-50"></div>
          </div>
        </div>
      </div>

      {/* Risk Rejection Logs - The actual "Vault" of intercepted risks */}
      <div className="card glass-dark border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl">
        <div className="p-8 border-b border-white/5 bg-gradient-to-r from-rose-500/10 to-transparent flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-rose-600 rounded-2xl shadow-lg shadow-rose-500/20">
              <ShieldCheck size={20} className="text-white" />
            </div>
            <div>
              <h3 className="text-xl font-black text-white tracking-tight uppercase italic">Risk Rejection Vault</h3>
              <p className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">Nhật ký các lệnh bị chặn bởi hệ thống quản trị rủi ro</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 rounded-xl border border-rose-500/20">
            <div className="w-2 h-2 bg-rose-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] font-black text-rose-400 uppercase">Live Interception</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-white/[0.02]">
                <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-wider whitespace-nowrap">Timestamp</th>
                <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-wider whitespace-nowrap">Symbol</th>
                <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-wider">Reason / Violation</th>
                <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-wider text-right whitespace-nowrap">Action taken</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {riskLogs.map(log => (
                <tr key={log.id} className="hover:bg-white/5 transition-colors group">
                  <td className="px-4 py-3 text-xs font-mono text-slate-400 whitespace-nowrap max-w-[180px]">
                    <div className="truncate">
                      {formatVnDate(log.timestamp)} {formatVnTime(log.timestamp)}
                    </div>
                  </td>
                  <td className="px-4 py-3 max-w-[120px]">
                    <span className="text-sm font-black font-mono text-white italic tracking-tight truncate block">{log.symbol}</span>
                  </td>
                  <td className="px-4 py-3 max-w-[400px]">
                    <p className="text-xs text-rose-200 truncate" title={log.reason}>{log.reason}</p>
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <span className="px-2 py-1 bg-slate-900 border border-slate-800 rounded text-[10px] font-black text-slate-400 uppercase tracking-wide group-hover:border-rose-500/50 group-hover:text-rose-400 transition-all">TERMINATED</span>
                  </td>
                </tr>
              ))}
              {riskLogs.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-3 opacity-20">
                      <ShieldCheck size={40} />
                      <p className="text-xs font-black uppercase tracking-wider">No risk violations detected - System is clean</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedVersion && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-3xl glass-dark border border-white/10 rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-mono">VERSION_ID: {selectedVersion.id}</p>
                <h4 className="text-lg font-black text-white">Config JSON Snapshot</h4>
              </div>
              <button
                onClick={() => setSelectedVersion(null)}
                className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            <div className="p-6 max-h-[70vh] overflow-auto">
              <pre className="text-xs text-slate-200 bg-slate-950/70 border border-white/10 rounded-xl p-4 overflow-auto">
{JSON.stringify(selectedVersion.config || {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
