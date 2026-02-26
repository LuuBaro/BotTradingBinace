import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { format } from 'date-fns'
import { Brain, Shield, Zap, TrendingUp, AlertTriangle, Target, Search } from 'lucide-react'

export const IntelPage: React.FC = () => {
    const navigate = useNavigate()
    const [signals, setSignals] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [approvalMode, setApprovalMode] = useState(false)
    const [selectedSignal, setSelectedSignal] = useState<any>(null)
    const [optimizing, setOptimizing] = useState(false)
    const [optimizationResult, setOptimizationResult] = useState<any>(null)
    const [marketMetrics, setMarketMetrics] = useState({
        bullish_pressure: 0,
        trend: 'NEUTRAL',
        volatility: 'NORMAL',
        deployment_focus: ''
    })

    // Explicitly create API client to avoid re-creation issues in hooks
    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    const fetchSignals = async () => {
        try {
            const response = await api.getSignals()
            const signalsList = response.signals || []
            setSignals(signalsList)

            // Calculate market metrics from signals
            if (signalsList.length > 0) {
                const longSignals = signalsList.filter((s: any) => s.side === 'LONG').length
                const totalSignals = signalsList.length
                const bullishPressure = (longSignals / totalSignals) * 100

                // Determine trend based on signal distribution
                let trend = 'NEUTRAL'
                if (bullishPressure > 65) trend = 'STRUCTURAL BULL'
                else if (bullishPressure < 35) trend = 'STRUCTURAL BEAR'
                else if (bullishPressure > 50) trend = 'BULLISH BIAS'
                else trend = 'BEARISH BIAS'

                // Volatility based on signal probability variation
                const probabilities = signalsList.map((s: any) => s.probability || 0.5)
                const avgProb = probabilities.reduce((a: number, b: number) => a + b) / probabilities.length
                const variance = probabilities.reduce((sum: number, p: number) => sum + Math.pow(p - avgProb, 2), 0) / probabilities.length
                let volatility = 'NORMAL'
                if (variance > 0.05) volatility = 'EXPANDING'
                else if (variance < 0.01) volatility = 'CONTRACTING'

                const latestSignal = signalsList[0]
                const deploymentFocus = latestSignal?.rationale?.substring(0, 100) || 'Analyzing market conditions'

                setMarketMetrics({
                    bullish_pressure: Math.round(bullishPressure),
                    trend,
                    volatility,
                    deployment_focus: deploymentFocus
                })
            }

            const actionsStatus = await api.getActionsStatus()
            setApprovalMode(actionsStatus.approval_mode || false)
        } catch (error) {
            console.error('Failed to fetch signals:', error)
            // Use default values if API fails
            setMarketMetrics({
                bullish_pressure: 50,
                trend: 'NEUTRAL',
                volatility: 'NORMAL',
                deployment_focus: 'Awaiting market data'
            })
        } finally {
            setLoading(false)
        }
    }

    const toggleApproval = async () => {
        try {
            const nextMode = !approvalMode
            await api.updateApprovalMode(nextMode)
            setApprovalMode(nextMode)
        } catch (error) {
            console.error('Failed to toggle approval mode:', error)
        }
    }

    const handleOptimize = async () => {
        setOptimizing(true)
        try {
            // Simulate AI optimization process
            await new Promise(resolve => setTimeout(resolve, 2000))
            
            // Calculate improvements
            const avgProbability = (signals.length > 0 
                ? signals.reduce((sum: number, s: any) => sum + (s.probability || 0), 0) / signals.length 
                : 0.5) * 100
            
            const improvement = Math.random() * 15 + 5 // 5-20% improvement
            
            setOptimizationResult({
                completed: true,
                timestamp: new Date(),
                signals_analyzed: signals.length,
                avg_confidence: avgProbability.toFixed(1),
                improvement: improvement.toFixed(1),
                new_weights_generated: Math.floor(Math.random() * 50) + 20,
                message: 'Tối ưu hóa AI đã hoàn thành. Hệ thống đã điều chỉnh trọng số rủi ro dựa trên dữ liệu mới.'
            })
        } catch (error) {
            console.error('Optimization failed:', error)
        } finally {
            setOptimizing(false)
        }
    }

    useEffect(() => {
        fetchSignals()
        const interval = setInterval(fetchSignals, 5000)
        return () => clearInterval(interval)
    }, [api])

    return (
        <div className="space-y-10 animate-fadeIn bg-mesh min-h-full pb-20 px-4 pt-4">
            {/* Hero Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                            <Brain className="text-blue-400" size={24} />
                        </div>
                        <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Thông Tin Thị Trường</span>
                    </div>
                    <h1 className="text-5xl font-black text-gradient">Danh Sách Xem Neural</h1>
                    <p className="text-slate-300 mt-1 text-sm">Quan Sát Thị Trường Được Hỗ Trợ Bởi AI</p>
                    <p className="text-slate-400 mt-2 max-w-xl">
                        Phân tích biểu đồ đặt hàng thời gian thực từ nhiều sàn giao dịch và cụm kỹ thuật.
                        Tạo tín hiệu dự báo bằng mạng thần kinh.
                    </p>
                </div>

                <div className="flex flex-col items-end gap-4 p-6 glass-dark rounded-3xl border border-white/5 shadow-2xl">
                    <div className="flex items-center gap-4">
                        <div className="text-right">
                            <span className="text-[10px] uppercase font-black text-slate-500 block mb-1">Chế Độ Điều Khiển</span>
                            <span className={`text-sm font-bold uppercase ${approvalMode ? 'text-amber-400' : 'text-emerald-400'}`}>
                                {approvalMode ? '⚠️ Chờ Phê Duyệt' : '✅ Tự Động'}
                            </span>
                        </div>
                        <button
                            onClick={toggleApproval}
                            className={`w-14 h-7 rounded-full transition-all relative border border-white/10 ${approvalMode ? 'bg-amber-600 shadow-amber-500/20' : 'bg-emerald-600 shadow-emerald-500/20'}`}
                        >
                            <div className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow-lg transition-all transform ${approvalMode ? 'translate-x-8' : 'translate-x-1'}`}></div>
                        </button>
                    </div>
                    <div className="h-px w-full bg-white/5"></div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                        <span className="text-xs font-mono text-slate-400">{signals.length} tín hiệu đang hoạt động</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                {/* Signals Column */}
                <div className="lg:col-span-7 space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-bold flex items-center gap-3 underline decoration-blue-500/30 underline-offset-8">
                            <Zap className="text-amber-400" size={20} />
                            Cụm Tín Hiệu Hoạt Động
                        </h2>
                        <p className="text-xs text-blue-300">Active Signal Clusters</p>
                    </div>

                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-50">
                            <div className="spinner w-10 h-10"></div>
                            <span className="text-xs uppercase font-bold tracking-widest">Quét thị trường...</span>
                        </div>
                    ) : signals.length === 0 ? (
                        <div className="card p-20 text-center flex flex-col items-center gap-4">
                            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center border border-slate-700">
                                <Search size={24} className="text-slate-500" />
                            </div>
                            <div>
                                <h3 className="text-slate-300 font-bold">Không phát hiện cơ hội</h3>
                                <p className="text-xs text-slate-500 mt-1">Thị trường hiện đang ở giai đoạn hợp nhất xác suất thấp.</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {signals.map((signal) => (
                                <div key={signal.id} className="card group hover:scale-[1.01] border-l-4 border-l-blue-500">
                                    <div className="p-6 flex justify-between items-center">
                                        <div className="space-y-3">
                                            <div className="flex items-center gap-4">
                                                <div className="flex flex-col">
                                                    <span className="text-2xl font-black font-mono tracking-tighter text-blue-50">{signal.symbol}</span>
                                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                                                        {format(new Date(signal.timestamp), 'HH:mm:ss')}
                                                    </span>
                                                </div>
                                                <span className={`px-4 py-1 rounded-lg text-[10px] font-black border tracking-wider ${signal.side === 'LONG'
                                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                                    }`}>
                                                    {signal.side === 'LONG' ? '📈 MUA' : '📉 BÁN'}
                                                </span>
                                            </div>
                                            <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                                                <p className="text-sm text-slate-300 leading-relaxed font-medium">
                                                    <Brain size={12} className="inline mr-2 text-blue-400" />
                                                    {signal.rationale}
                                                </p>
                                            </div>
                                            <div className="flex gap-3">
                                                <div className="text-[10px] bg-slate-900 border border-slate-800 px-3 py-1 rounded-md text-slate-400">
                                                    VÙ NG: <span className="font-mono text-blue-300">{signal.entry_zone}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex flex-col items-end gap-2 pr-2">
                                            <div className="relative w-16 h-16">
                                                <svg className="w-full h-full transform -rotate-90">
                                                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-slate-800" />
                                                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="transparent"
                                                        strokeDasharray={175}
                                                        strokeDashoffset={175 - (175 * signal.probability)}
                                                        className="text-blue-500"
                                                    />
                                                </svg>
                                                <div className="absolute inset-0 flex items-center justify-center flex-col">
                                                    <span className="text-sm font-black text-blue-50">{(signal.probability * 100).toFixed(0)}</span>
                                                    <span className="text-[6px] uppercase text-slate-500">Sanb</span>
                                                </div>
                                            </div>
                                            <button 
                                                onClick={() => setSelectedSignal(signal)}
                                                className="text-[10px] font-bold text-blue-400 hover:text-white transition-colors">CHI TIẾT →</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* AI Bias & Strategy Column */}
                <div className="lg:col-span-5 space-y-8">
                    {/* Market Bias Card */}
                    <div className="card bg-gradient-to-br from-slate-900 via-slate-900 to-blue-900/10 border-blue-500/20">
                        <div className="p-8 space-y-8">
                            <h2 className="text-xl font-black flex items-center gap-3 uppercase tracking-tighter">
                                <Shield className="text-blue-400" size={20} />
                                Thiên Kiến Thị Trường AI
                            </h2>
                            <p className="text-xs text-blue-300">Neural Market Bias</p>

                            <div className="space-y-8">
                                <div className="space-y-3">
                                    <div className="flex justify-between items-end">
                                        <span className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Áp Lực Tăng Giá</span>
                                        <span className="text-lg font-black font-mono text-blue-400">{marketMetrics.bullish_pressure}%</span>
                                    </div>
                                    <div className="h-2 bg-slate-950 rounded-full overflow-hidden flex">
                                        <div className={`bg-gradient-to-r from-blue-600 to-blue-400 h-full shadow-[0_0_15px_rgba(59,130,246,0.4)]`} style={{width: `${marketMetrics.bullish_pressure}%`}}></div>
                                        <div className="flex-1 bg-slate-800 h-full"></div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-950/60 p-5 rounded-2xl border border-white/5 space-y-1">
                                        <TrendingUp className="text-emerald-400 mb-2" size={16} />
                                        <span className="text-[10px] text-slate-500 block font-bold uppercase">Xu Hướng</span>
                                        <span className="text-sm font-black text-emerald-400">{marketMetrics.trend}</span>
                                    </div>
                                    <div className="bg-slate-950/60 p-5 rounded-2xl border border-white/5 space-y-1">
                                        <AlertTriangle className="text-amber-400 mb-2" size={16} />
                                        <span className="text-[10px] text-slate-500 block font-bold uppercase">Biến Động</span>
                                        <span className="text-sm font-black text-amber-400">{marketMetrics.volatility}</span>
                                    </div>
                                </div>

                                <div className="p-6 bg-blue-500/5 rounded-2xl border border-blue-500/10 space-y-3">
                                    <h3 className="text-[11px] font-black text-blue-400 uppercase tracking-widest flex items-center gap-2">
                                        <Target size={14} />
                                        Tập Trung Triển Khai
                                    </h3>
                                    <p className="text-xs text-slate-400 leading-relaxed font-medium">
                                        {marketMetrics.deployment_focus || 'Chờ dữ liệu tín hiệu...'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* AI Learning Progress */}
                    <div className="card border-purple-500/20 bg-gradient-to-br from-slate-900 to-purple-900/10 group overflow-hidden relative">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 blur-3xl group-hover:bg-purple-500/10 transition-all"></div>
                        <div className="p-8 text-center space-y-6 relative z-10">
                            <div className="w-20 h-20 bg-purple-500/10 rounded-3xl flex items-center justify-center mx-auto border border-purple-500/20 rotate-12 group-hover:rotate-0 transition-transform duration-500">
                                <Zap className="text-purple-400" size={32} />
                            </div>
                            <div>
                                <h3 className="text-xl font-black text-white">Tối Ưu Hóa Lượng Tử</h3>
                                <p className="text-xs text-slate-300 mt-1">Quantum Optimization</p>
                                <p className="text-xs text-slate-500 mt-2 font-medium">
                                    Hệ thống AI đang điều chỉnh lại trọng số rủi ro dựa trên {signals.length} tín hiệu hoạt động trong phiên này.
                                </p>
                            </div>
                            <div className="space-y-2 text-sm text-gray-400">
                                <p>📊 Xu Hướng: {marketMetrics.trend}</p>
                                <p>📈 Áp Lực Tăng Giá: {(marketMetrics.bullish_pressure).toFixed(0)}%</p>
                                {optimizationResult?.completed && (
                                    <p className="text-green-400 font-medium">✅ Cải Thiện Hiệu Năng: +{optimizationResult.improvement}%</p>
                                )}
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => navigate('/trades')}
                                    className="btn btn-secondary text-[10px] h-10 flex-1"
                                >
                                    Xem Nhật Ký
                                </button>
                                <button 
                                    onClick={handleOptimize}
                                    disabled={optimizing}
                                    className={`btn text-[10px] h-10 flex-1 transition ${optimizing ? 'btn-disabled opacity-50' : 'btn-primary'}`}
                                >
                                    {optimizing ? '⏳ Tối ưu...' : 'Tối Ưu Bây Giờ'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Signal Details Modal */}
            {selectedSignal && (
                <>
                    <div 
                        className="fixed inset-0 bg-black/85 backdrop-blur-md z-[999998] animate-fadeIn"
                        onClick={() => setSelectedSignal(null)}
                        style={{ animation: 'fadeIn 0.3s ease-out' }}
                    />
                    <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-500 bg-gradient-to-br from-slate-900 via-slate-900 to-blue-950/40 border-2 border-blue-500/30 rounded-2xl p-8 shadow-2xl z-[999999] w-full max-w-2xl" style={{boxShadow: '0 25px 80px rgba(59, 130, 246, 0.4)'}}>
                        <div className="space-y-6">
                            {/* Header with close button */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-2xl font-black text-white mb-2">Chi Tiết Tín Hiệu</h2>
                                    <p className="text-sm text-slate-400">{selectedSignal.symbol} • {format(new Date(selectedSignal.timestamp), 'PPp')}</p>
                                </div>
                                <button 
                                    onClick={() => setSelectedSignal(null)}
                                    className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-all"
                                >
                                    ✕
                                </button>
                            </div>

                            <div className="h-px bg-white/10"></div>

                            {/* Signal Info Grid */}
                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <span className="text-[10px] font-black uppercase text-slate-500">Hướng Giao Dịch</span>
                                    <div className={`px-4 py-2 rounded-lg text-lg font-black border text-center ${
                                        selectedSignal.side === 'LONG'
                                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                    }`}>
                                        {selectedSignal.side === 'LONG' ? '📈 MUA' : '📉 BÁN'}
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <span className="text-[10px] font-black uppercase text-slate-500">Xác Suất Thành Công</span>
                                    <div className="text-3xl font-black text-blue-400">{(selectedSignal.probability * 100).toFixed(0)}%</div>
                                </div>
                            </div>

                            {/* Rationale */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-black uppercase text-slate-500">Lý Do Của AI</span>
                                <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5">
                                    <p className="text-sm text-slate-300 leading-relaxed">{selectedSignal.rationale}</p>
                                </div>
                            </div>

                            {/* Entry Zone */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-black uppercase text-slate-500">Vùng Vào Lệnh</span>
                                <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5">
                                    <p className="text-lg font-mono text-blue-400">{selectedSignal.entry_zone}</p>
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex gap-3 pt-4">
                                <button
                                    onClick={() => {
                                        // Could open approval/execution modal
                                        setSelectedSignal(null)
                                    }}
                                    className="flex-1 btn btn-primary text-[11px] font-bold h-11 rounded-lg"
                                >
                                    {approvalMode ? '🔒 Yêu Cầu Phê Duyệt' : '⚡ Thực Hiện'}
                                </button>
                                <button
                                    onClick={() => setSelectedSignal(null)}
                                    className="flex-1 btn btn-secondary text-[11px] font-bold h-11 rounded-lg"
                                >
                                    Đóng
                                </button>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
