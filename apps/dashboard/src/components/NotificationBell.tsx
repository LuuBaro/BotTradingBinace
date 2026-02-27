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
    const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    const fetchAIAnalysis = async () => {
        try {
            setLoading(true)
            // 1. Get Learning Metrics
            const response = await api.get('learning/dashboard-metrics')

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

                    <div className="fixed sm:absolute right-4 sm:right-0 top-24 sm:top-full mt-2 w-[calc(100vw-32px)] sm:w-[480px] max-h-[80vh] sm:max-h-[85vh] bg-[#0f172a] border border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-[2rem] sm:rounded-[2.5rem] z-[70] overflow-hidden flex flex-col animate-slideUp">
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
                                    <div className="p-6 rounded-[2rem] bg-gradient-to-br from-slate-900 to-black border border-white/5 space-y-4 shadow-inner relative overflow-hidden">
                                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl pointer-events-none"></div>
                                        <div className="flex justify-between items-center relative z-1">
                                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Trạng thái thị trường (Bias)</span>
                                            <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full">
                                                <Waves size={10} className="text-blue-400" />
                                                <span className="text-[9px] font-black text-blue-400 uppercase tracking-tighter">
                                                    {report.market_intelligence?.market_bias ||
                                                        (report.latest_regime === 'TREND' ? 'XU HƯỚNG MẠNH' :
                                                            report.latest_regime === 'RANGE' ? 'BIÊN ĐỘ HẸP' :
                                                                report.latest_regime === 'VOLATILITY_SPIKE' ? 'BIẾN ĐỘNG CAO' :
                                                                    report.latest_regime || (report.stats?.win_rate > 0.5 ? 'XU HƯỚNG' : 'TÍCH LŨY'))}
                                                </span>
                                            </div>
                                        </div>

                                        <div className="space-y-3 relative z-1">
                                            <div className="flex justify-between items-end">
                                                <span className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Độ tin cậy hệ thống</span>
                                                <span className="text-lg font-black font-mono text-blue-400">
                                                    {report.market_intelligence?.global_sentiment_index || (report.latest_confidence ? `${(report.latest_confidence * 100).toFixed(0)}%` : '72%')}
                                                </span>
                                            </div>
                                            <div className="h-2 bg-slate-800 rounded-full overflow-hidden flex">
                                                <div
                                                    className="bg-gradient-to-r from-blue-600 to-purple-400 h-full shadow-[0_0_15px_rgba(59,130,246,0.4)]"
                                                    style={{ width: `${report.market_intelligence?.global_sentiment_index || (report.latest_confidence || 0.72) * 100}%` }}
                                                ></div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Real-time Intel (News & Blockchain) */}
                                    {report.market_intelligence && (
                                        <div className="space-y-4 animate-fadeIn">
                                            {/* News Headlines */}
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <Clock size={12} className="text-slate-500" />
                                                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Tin tức thị trường (Real-time News)</span>
                                                </div>
                                                <div className="space-y-2">
                                                    {report.market_intelligence.headlines.map((news: string, i: number) => (
                                                        <div key={i} className="p-3 bg-white/[0.02] border border-white/5 rounded-xl flex items-start gap-2 hover:bg-white/5 transition-colors">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0"></div>
                                                            <p className="text-[11px] text-slate-300 leading-snug">{news}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* On-Chain Signals */}
                                            <div className="grid grid-cols-2 gap-3">
                                                {report.market_intelligence.signals.map((signal: any, i: number) => (
                                                    <div key={i} className="p-3 bg-slate-900/50 border border-white/5 rounded-xl space-y-1">
                                                        <div className="flex justify-between items-center mb-1">
                                                            <span className="text-[8px] font-black text-blue-400/60 uppercase">{signal.source}</span>
                                                            <span className={`text-[7px] px-1 rounded-sm font-black ${signal.sentiment?.includes('Lạc quan') || signal.sentiment?.includes('Tăng trưởng') || signal.sentiment?.includes('Mạnh') ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-400'}`}>
                                                                {signal.sentiment}
                                                            </span>
                                                        </div>
                                                        <p className="text-[10px] font-bold text-white leading-tight">{signal.signal}</p>
                                                        <span className="text-[8px] text-slate-500 font-medium">Độ mạnh: {signal.strength}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* AI Deep Analysis Section */}
                                    <div className="space-y-3 text-left">
                                        <div className="flex items-center gap-2">
                                            <Target size={14} className="text-blue-400" />
                                            <h4 className="text-[11px] font-black text-blue-400 uppercase tracking-widest">Phân tích từ Neural Core</h4>
                                        </div>
                                        <div className="p-5 bg-white/[0.03] rounded-2xl border border-white/5 text-sm text-slate-200 leading-relaxed italic font-medium selection:bg-blue-500/30">
                                            "{report.market_intelligence?.ai_summary || report.latest_rationale || report.recommendations?.[0] || 'Hệ thống đang quan sát dòng tiền để xác định điểm xoay chuyển của thị trường.'}"
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
                                                {report.latest_action === 'HOLD' ? 'ĐỨNG NGOÀI (HOLD)' :
                                                    report.latest_action === 'OPEN' ? 'VÀO LỆNH (OPEN)' :
                                                        report.latest_action === 'CLOSE' ? 'ĐÓNG LỆNH (CLOSE)' : 'QUAN SÁT'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Key Insights (Accordion) */}
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest block">Chiến lược đề xuất</span>
                                            <span className="text-[9px] text-blue-400/60 uppercase font-black">Click để xem chi tiết</span>
                                        </div>
                                        <div className="space-y-2">
                                            {(report.suggested_adaptations?.strategies?.length > 0
                                                ? report.suggested_adaptations.strategies
                                                : (report.stats ? [
                                                    { title: `Tỷ lệ thắng mục tiêu: >${(report.stats.win_rate * 100).toFixed(1)}%`, detail: "Dựa trên hiệu suất lịch sử, đây là ngưỡng xác suất cao nhất để bảo toàn vốn trong giai đoạn này." },
                                                    { title: `Cặp giao dịch tối ưu: BTC, ETH, SOL`, detail: "Tập trung vào các cặp tiền có độ lệch chuẩn thấp và volume tương đối ổn định theo phân tích của Neural Core." },
                                                    { title: `Tỷ lệ Rủi ro/Lợi nhuận: >1:1.5`, detail: "Thiết lập điểm chốt lời gấp ít nhất 1.5 lần điểm dừng lỗ để bù đắp các lệnh sai và duy trì Profit Factor > 1.0." },
                                                    { title: `Xu hướng ưu tiên: ${report.latest_regime || 'Dòng tiền chính'}`, detail: "Ưu tiên các lệnh theo xu hướng chủ đạo của thị trường thay vì đánh ngược sóng (counter-trend) trong bối cảnh hiện tại." }
                                                ] : [
                                                    { title: "Vào lệnh khi độ tin cậy > 75%", detail: "Chỉ kích hoạt vị thế khi hệ thống đạt độ tin cậy tuyệt đối để giảm thiểu nhiễu thị trường." },
                                                    { title: "Duy trì đòn bẩy an toàn < 5x", detail: "Quản lý rủi ro bằng cách hạn chế đòn bẩy cao, tránh việc bị quét thanh khoản (liquidation) trong các pha râu nến (wicks)." },
                                                    { title: "Kiểm tra vùng hỗ trợ/kháng cự khung lớn", detail: "Đối soát với các mốc khung thời gian lớn (H4/D1) để xác định điểm xoay chiều (pivot) quan trọng." },
                                                    { title: "Theo dõi sát các tin tức vĩ mô và Binance", detail: "AI đang quét các nguồn tin Web3 và dữ liệu sàn Binance để cảnh báo các đợt biến động mạnh do tin vĩ mô hoặc cá voi di chuyển." }
                                                ])).map((item: any, idx: number) => (
                                                    <div
                                                        key={idx}
                                                        className="group cursor-pointer"
                                                        onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                                                    >
                                                        <div className={`flex items-center gap-3 p-4 bg-white/[0.02] border rounded-2xl transition-all ${expandedIdx === idx ? 'border-blue-500/50 bg-blue-500/5 shadow-lg' : 'border-white/5 hover:bg-white/5'}`}>
                                                            <ChevronRight size={12} className={`text-blue-500 transition-transform ${expandedIdx === idx ? 'rotate-90' : ''}`} />
                                                            <span className={`text-xs font-bold transition-colors ${expandedIdx === idx ? 'text-white' : 'text-slate-300'}`}>{item.title}</span>
                                                        </div>
                                                        {expandedIdx === idx && (
                                                            <div className="mx-4 p-4 bg-blue-500/5 border-x border-b border-blue-500/20 rounded-b-2xl animate-fadeIn">
                                                                <p className="text-[10px] text-slate-400 font-medium leading-relaxed italic">
                                                                    {item.detail}
                                                                </p>
                                                            </div>
                                                        )}
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
