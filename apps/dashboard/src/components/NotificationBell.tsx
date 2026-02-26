import React, { useState, useEffect, useMemo } from 'react'
import { Bell, Brain, AlertTriangle, Shield, X, ChevronRight, Clock, Target, Zap, Waves } from 'lucide-react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { format } from 'date-fns'
import { vi } from 'date-fns/locale'

export const NotificationBell: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false)
    const [report, setReport] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [unread, setUnread] = useState(false)

    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    const fetchAIAnalysis = async () => {
        try {
            setLoading(true)
            // 1. Get Learning Metrics
            const response = await api.get('/api/learning/dashboard-metrics')

            // 2. Also get recent decisions for immediate context
            const decisionsRes = await api.getDecisions(1)
            const latest = decisionsRes && decisionsRes.length > 0 ? decisionsRes[0] : null

            if (response && response.data) {
                const data = response.data
                // If insufficient data for learning, we combine with latest decision
                if (data.status === 'insufficient_data' && latest) {
                    setReport({
                        ...data,
                        latest_rationale: latest.rationale || latest.decision_json?.rationale,
                        latest_action: latest.action,
                        latest_confidence: latest.confidence,
                        latest_regime: latest.regime,
                        is_fallback: true
                    })
                } else {
                    setReport(data)
                }

                if (!isOpen) setUnread(true)
            }
        } catch (error) {
            console.error('Failed to fetch AI analysis:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchAIAnalysis()
        // Refresh every 30 minutes for a new "Market Briefing"
        const interval = setInterval(fetchAIAnalysis, 30 * 60 * 1000)
        return () => clearInterval(interval)
    }, [])

    const toggle = () => {
        setIsOpen(!isOpen)
        if (!isOpen) setUnread(false)
    }

    return (
        <div className="relative">
            {/* The Bell Icon */}
            <button
                onClick={toggle}
                className={`relative p-3 rounded-2xl transition-all active:scale-95 border group ${isOpen ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-500/20' : 'bg-white/5 border-white/5 text-slate-400 hover:text-white hover:bg-white/10'
                    }`}
            >
                <Bell size={20} className={unread ? 'animate-bounce' : ''} />
                {unread && (
                    <span className="absolute top-2 right-2 w-3 h-3 bg-rose-500 border-2 border-[#020617] rounded-full shadow-[0_0_10px_#ef4444]"></span>
                )}
            </button>

            {/* Popover Panel */}
            {isOpen && (
                <>
                    {/* Backdrop to close and blur background */}
                    <div className="fixed inset-0 z-[60] bg-[#020617]/80 backdrop-blur-sm transition-opacity" onClick={toggle}></div>

                    <div className="absolute right-0 mt-4 w-[480px] max-h-[85vh] bg-[#0f172a] border border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-[2.5rem] z-[70] overflow-hidden flex flex-col animate-slideUp">
                        {/* Header */}
                        <div className="p-6 border-b border-white/5 bg-gradient-to-r from-blue-600/10 to-purple-600/10 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-blue-500 rounded-xl shadow-lg shadow-blue-500/20">
                                    <Brain size={20} className="text-white" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-white leading-none">AI Market Briefing</h3>
                                    <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Chiến lược & Phân tích tổng hợp</span>
                                </div>
                            </div>
                            <button onClick={toggle} className="p-2 hover:bg-white/10 rounded-xl transition-colors">
                                <X size={18} className="text-slate-500" />
                            </button>
                        </div>

                        {/* Content Area */}
                        <div className="overflow-y-auto custom-scrollbar flex-grow p-6 space-y-6">
                            {loading && !report ? (
                                <div className="py-20 flex flex-col items-center justify-center gap-4">
                                    <div className="spinner w-10 h-10"></div>
                                    <span className="text-[10px] font-black uppercase text-slate-500 animate-pulse">Neural Core Analyzing Markets...</span>
                                </div>
                            ) : report && (report.status === 'success' || report.is_fallback) ? (
                                <div className="space-y-6 animate-fadeIn">
                                    {/* Market Sentiment / Status */}
                                    <div className="p-6 rounded-[2rem] bg-gradient-to-br from-slate-900 to-black border border-white/5 space-y-4 shadow-inner">
                                        <div className="flex justify-between items-center">
                                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Trạng thái thị trường (Bias)</span>
                                            <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full">
                                                <Waves size={10} className="text-blue-400" />
                                                <span className="text-[9px] font-black text-blue-400 uppercase tracking-tighter">
                                                    {report.latest_regime || (report.stats?.win_rate > 0.5 ? 'TRENDING' : 'CONSOLIDATING')}
                                                </span>
                                            </div>
                                        </div>

                                        <div className="space-y-3">
                                            <div className="flex justify-between items-end">
                                                <span className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Độ tin cậy hệ thống</span>
                                                <span className="text-lg font-black font-mono text-blue-400">
                                                    {report.latest_confidence ? `${(report.latest_confidence * 100).toFixed(0)}%` : '72%'}
                                                </span>
                                            </div>
                                            <div className="h-2 bg-slate-800 rounded-full overflow-hidden flex">
                                                <div
                                                    className="bg-gradient-to-r from-blue-600 to-purple-400 h-full shadow-[0_0_15px_rgba(59,130,246,0.4)]"
                                                    style={{ width: `${(report.latest_confidence || 0.72) * 100}%` }}
                                                ></div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* AI Deep Analysis Section */}
                                    <div className="space-y-3 text-left">
                                        <div className="flex items-center gap-2">
                                            <Target size={14} className="text-blue-400" />
                                            <h4 className="text-[11px] font-black text-blue-400 uppercase tracking-widest">Phân tích từ Neural Core</h4>
                                        </div>
                                        <div className="p-5 bg-white/[0.03] rounded-2xl border border-white/5 text-sm text-slate-200 leading-relaxed italic font-medium selection:bg-blue-500/30">
                                            "{report.latest_rationale || report.recommendations?.[0] || 'Hệ thống đang quan sát dòng tiền để xác định điểm xoay chuyển của thị trường.'}"
                                        </div>
                                    </div>

                                    {/* Risk & Strategy Grid */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-5 bg-slate-900 border border-white/5 rounded-2xl space-y-1">
                                            <Shield className="text-amber-400 mb-2" size={16} />
                                            <span className="text-[9px] text-slate-500 block font-bold uppercase">Mức rủi ro</span>
                                            <span className="text-sm font-black text-amber-400 uppercase">
                                                {report.latest_confidence > 0.8 ? 'THẤP (LOW)' : 'VỪA (MED)'}
                                            </span>
                                        </div>
                                        <div className="p-5 bg-slate-900 border border-white/5 rounded-2xl space-y-1">
                                            <Zap className="text-blue-400 mb-2" size={16} />
                                            <span className="text-[9px] text-slate-500 block font-bold uppercase">Gợi ý hành động</span>
                                            <span className="text-sm font-black text-blue-400 uppercase">
                                                {report.latest_action || 'QUAN SÁT'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Key Insights (Bullet points) */}
                                    <div className="space-y-3">
                                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">Chiến lược đề xuất</span>
                                        <div className="space-y-2">
                                            {(report.stats ? [
                                                `Win Rate mục tiêu: >${(report.stats.win_rate * 100).toFixed(1)}%`,
                                                `Vùng hoạt động: Optimized Symbols`,
                                                `Risk/Reward: >1:1.5`,
                                                `Focus: ${report.latest_regime || 'Dòng tiền chính'}`
                                            ] : [
                                                "Vào lệnh khi Confidence > 75%",
                                                "Duy trì đòn bẩy an toàn < 5x",
                                                "Kiểm tra vùng hỗ trợ/kháng cự HTF",
                                                "Theo dõi sát các tin tức vĩ mô"
                                            ]).map((item, idx) => (
                                                <div key={idx} className="flex items-center gap-3 p-4 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/5 transition-colors">
                                                    <ChevronRight size={12} className="text-blue-500" />
                                                    <span className="text-xs font-bold text-slate-300">{item}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="py-20 text-center space-y-4">
                                    <AlertTriangle className="mx-auto text-amber-500" size={32} />
                                    <p className="text-xs text-slate-500 px-10">
                                        Hiện chưa có đủ dữ liệu giao dịch (cần ít nhất 5 lệnh) để phân tích sâu.
                                        Bot đang quét dữ liệu thị trường trực tiếp...
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="p-4 bg-white/5 border-t border-white/5 flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <Clock size={12} className="text-slate-600" />
                                <span className="text-[9px] font-mono text-slate-500">Cập nhật: {report?.analysis_time ? format(new Date(report.analysis_time), 'HH:mm (dd/MM)', { locale: vi }) : 'Vừa xong'}</span>
                            </div>
                            <button
                                onClick={fetchAIAnalysis}
                                className="text-[9px] font-black text-blue-500 hover:text-white uppercase tracking-widest transition-colors flex items-center gap-1"
                            >
                                Làm mới (Sync)
                                <RefreshCw size={10} />
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

const RefreshCw: React.FC<{ size?: number; className?: string }> = ({ size = 16, className = "" }) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
    >
        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
        <path d="M21 3v5h-5" />
        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
        <path d="M3 21v-5h5" />
    </svg>
)
