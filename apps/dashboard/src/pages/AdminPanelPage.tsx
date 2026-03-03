import React, { useState, useMemo, useEffect } from 'react'
import { Users, Shield, Send, Terminal, ShieldAlert, UserPlus, ShieldCheck, ShieldOff, Smartphone, Monitor as DesktopIcon, Activity, Zap, TrendingUp, Cpu, Server, Globe, MousePointer2, BarChart3, Binary, Target } from 'lucide-react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { useAuthStore } from '../store'
import { format } from 'date-fns'

interface UserRecord {
    id: string
    username: string
    email: string
    role: string
    is_active: boolean
    is_whitelisted: boolean
    is_blacklisted: boolean
    last_login_at: string | null
    created_at: string
}

interface LoginLog {
    id: number
    username: string
    ip: string
    user_agent: string
    os: string
    browser: string
    timestamp: string
}

interface SystemStats {
    total_users: number
    active_bots: number
    global_pnl_24h: number
    total_trades: number
    system_health?: {
        cpu: number
        ram: number
        latency_ms: number
        db_status: string
    }
    uptime_status: string
    last_updated: string
}

interface ActivityItem {
    type: 'event' | 'decision' | 'trade'
    id: string
    username: string
    code: string
    message: string
    level: string
    timestamp: string
}

export const AdminPanelPage: React.FC = () => {
    const { user } = useAuthStore()
    const token = localStorage.getItem('token') || ''
    const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

    const [notifTitle, setNotifTitle] = useState('')
    const [notifMessage, setNotifMessage] = useState('')
    const [notifLevel, setNotifLevel] = useState('info')
    const [targetUserId, setTargetUserId] = useState('')

    // User Management State
    const [users, setUsers] = useState<UserRecord[]>([])
    const [logs, setLogs] = useState<LoginLog[]>([])
    const [stats, setStats] = useState<SystemStats | null>(null)
    const [activity, setActivity] = useState<ActivityItem[]>([])
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'trader' })

    const [loading, setLoading] = useState(false)
    const [_fetching, setFetching] = useState(true)
    const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null)

    const fetchAdminData = async () => {
        try {
            const [usersRes, logsRes, statsRes, activityRes] = await Promise.all([
                api.get<UserRecord[]>('admin/users'),
                api.get<LoginLog[]>('admin/login-logs'),
                api.get<SystemStats>('admin/stats'),
                api.get<ActivityItem[]>('admin/activity')
            ])
            setUsers(usersRes.data)
            setLogs(logsRes.data)
            setStats(statsRes.data)
            setActivity(activityRes.data)
        } catch (error) {
            console.error("Admin fetch failed", error)
        } finally {
            setFetching(false)
        }
    }

    useEffect(() => {
        if (user?.role?.toLowerCase() !== 'admin') return

        fetchAdminData()
        const interval = setInterval(fetchAdminData, 5000) // Fast refresh for "realtime" feel
        return () => clearInterval(interval)
    }, [user])

    const sendNotification = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!notifTitle || !notifMessage) return

        try {
            setLoading(true)
            await api.post('system/notifications', {
                title: notifTitle,
                message: notifMessage,
                level: notifLevel,
                target_user_id: targetUserId || null
            })
            setStatus({ type: 'success', message: 'Thông báo đã được gửi thành công!' })
            setNotifTitle('')
            setNotifMessage('')
        } catch (error) {
            setStatus({ type: 'error', message: 'Không thể gửi thông báo hệ thống.' })
        } finally {
            setLoading(false)
            setTimeout(() => setStatus(null), 3000)
        }
    }

    const createUser = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            setLoading(true)
            await api.post('admin/users', newUser)
            setShowCreateModal(false)
            setNewUser({ username: '', email: '', password: '', role: 'trader' })
            fetchAdminData()
            setStatus({ type: 'success', message: `Người dùng ${newUser.username} đã được tạo!` })
        } catch (error) {
            setStatus({ type: 'error', message: 'Không thể tạo tài khoản.' })
        } finally {
            setLoading(false)
        }
    }

    const toggleUserStatus = async (userId: string, currentStatus: boolean) => {
        try {
            await api.put(`admin/users/${userId}`, { is_active: !currentStatus })
            fetchAdminData()
        } catch (error) {
            console.error("Status update failed", error)
        }
    }

    if (user?.role?.toLowerCase() !== 'admin') {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
                <ShieldAlert size={64} className="text-rose-500 animate-pulse" />
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Truy cập bị từ chối</h2>
                <p className="text-slate-500">Chỉ quản trị viên Web Mẹ mới có quyền truy cập vào bảng điều khiển này.</p>
            </div>
        )
    }

    return (
        <div className="space-y-8 pb-20 animate-fadeIn">
            {/* Header / System Health */}
            <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
                <div className="flex items-center gap-5">
                    <div className="relative">
                        <div className="p-4 bg-yellow-500 rounded-[2rem] shadow-2xl shadow-yellow-500/20 rotate-3 z-10 relative">
                            <Shield size={32} className="text-slate-950" />
                        </div>
                        <div className="absolute -inset-2 bg-yellow-500/20 blur-2xl rounded-full"></div>
                    </div>
                    <div>
                        <h1 className="text-5xl font-black text-white tracking-tighter uppercase italic leading-none">HQ COMMAND</h1>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-black text-emerald-500 uppercase">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                {stats?.uptime_status || 'Checking...'}
                            </span>
                            <p className="text-slate-500 font-bold text-[10px] tracking-widest uppercase">Admin SaaS Interface v4.5</p>
                        </div>
                    </div>
                </div>

                {/* Real-time Health Monitor */}
                <div className="flex flex-wrap items-center gap-4">
                    {stats?.system_health && (
                        <div className="flex items-center gap-6 px-8 py-4 bg-white/[0.03] border border-white/10 rounded-[2rem] backdrop-blur-md">
                            <div className="flex items-center gap-3">
                                <Cpu size={16} className="text-blue-400" />
                                <div className="flex flex-col">
                                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">CPU LOAD</span>
                                    <span className="text-sm font-black text-white tabular-nums">{stats.system_health.cpu.toFixed(1)}%</span>
                                </div>
                            </div>
                            <div className="w-px h-8 bg-white/10"></div>
                            <div className="flex items-center gap-3">
                                <Server size={16} className="text-emerald-400" />
                                <div className="flex flex-col">
                                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">RAM USE</span>
                                    <span className="text-sm font-black text-white tabular-nums">{stats.system_health.ram.toFixed(1)}%</span>
                                </div>
                            </div>
                            <div className="w-px h-8 bg-white/10"></div>
                            <div className="flex items-center gap-3">
                                <Activity size={16} className="text-amber-400" />
                                <div className="flex flex-col">
                                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">LATENCY</span>
                                    <span className="text-sm font-black text-white tabular-nums">{stats.system_health.latency_ms}ms</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="hidden lg:flex flex-col items-end">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em]">SYNCHRONIZING</span>
                        <span className="text-xs font-black text-white uppercase italic">{stats ? format(new Date(stats.last_updated), 'HH:mm:ss.SS') : '--:--:--'}</span>
                    </div>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { label: 'Tổng User', value: stats?.total_users || 0, icon: Users, color: 'text-blue-400', bg: 'bg-blue-400/10', trend: '+12% m/m' },
                    { label: 'Bot Đang Chạy', value: stats?.active_bots || 0, icon: Zap, color: 'text-yellow-400', bg: 'bg-yellow-400/10', trend: 'Live Now' },
                    { label: 'Sản Lượng 24h', value: `$${stats?.global_pnl_24h.toFixed(2) || '0.00'}`, icon: TrendingUp, color: (stats?.global_pnl_24h || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400', bg: 'bg-emerald-400/10', trend: 'Global Net' },
                    { label: 'Tổng Giao Dịch', value: stats?.total_trades || 0, icon: Target, color: 'text-indigo-400', bg: 'bg-indigo-400/10', trend: 'All Time' },
                ].map((stat, i) => (
                    <div key={i} className="glass-dark border border-white/5 p-6 rounded-[2.5rem] flex items-center justify-between hover:border-white/20 transition-all group relative overflow-hidden">
                        <div className="flex items-center gap-5 relative z-10">
                            <div className={`p-4 rounded-2xl ${stat.bg} ${stat.color} transition-transform group-hover:scale-110 shadow-lg`}>
                                <stat.icon size={24} />
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">{stat.label}</p>
                                <p className={`text-2xl font-black tracking-tighter ${stat.color}`}>{stat.value}</p>
                            </div>
                        </div>
                        <div className="flex flex-col items-end relative z-10">
                            <span className="text-[9px] font-black text-slate-600 uppercase tracking-tighter">{stat.trend}</span>
                        </div>
                        <div className={`absolute -right-4 -bottom-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity`}>
                            <stat.icon size={120} />
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Main Control Column */}
                <div className="lg:col-span-8 space-y-8">
                    {/* User Management */}
                    <div className="glass-dark border border-white/5 rounded-[2.5rem] overflow-hidden">
                        <div className="p-8 border-b border-white/5 bg-gradient-to-r from-indigo-600/10 to-transparent flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-indigo-600 rounded-2xl shadow-xl shadow-indigo-600/20">
                                    <Binary size={20} className="text-white" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-white tracking-tight leading-tight">NODE MANAGEMENT</h3>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest italic">Cấu trúc hạ tầng tài khoản người dùng</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] flex items-center gap-2 transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
                            >
                                <UserPlus size={14} /> Provision Node
                            </button>
                        </div>

                        <div className="p-0">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="bg-white/[0.02]">
                                            <th className="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center w-16">Rank</th>
                                            <th className="px-4 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Identification Key</th>
                                            <th className="px-4 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Access Layer</th>
                                            <th className="px-4 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Health</th>
                                            <th className="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest text-right">Ops</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {users.map((u, i) => (
                                            <tr key={u.id} className="group hover:bg-white/[0.03] transition-colors">
                                                <td className="px-8 py-6">
                                                    <span className="text-xs font-black text-slate-600 font-mono tracking-tighter">{(i + 1).toString().padStart(3, '0')}</span>
                                                </td>
                                                <td className="px-4 py-6">
                                                    <div className="flex flex-col">
                                                        <span className="text-sm font-black text-white uppercase leading-none mb-1.5 group-hover:text-indigo-400 transition-colors">{u.username}</span>
                                                        <span className="text-[10px] text-slate-500 font-mono tracking-tighter truncate w-32">{u.id}</span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-6 font-mono">
                                                    <span className={`px-2.5 py-1 rounded-lg text-[9px] font-black uppercase border ${u.role === 'admin' ? 'bg-amber-500/10 border-amber-500/20 text-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.1)]' : 'bg-blue-500/10 border-blue-500/20 text-blue-500'}`}>
                                                        {u.role}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-6">
                                                    <div className="flex items-center gap-2">
                                                        <div className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]'}`}></div>
                                                        <span className={`text-[10px] font-black uppercase ${u.is_active ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                            {u.is_active ? 'ENABLED' : 'TERMINATED'}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-8 py-6 text-right">
                                                    <div className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-all translate-x-4 group-hover:translate-x-0">
                                                        <button
                                                            onClick={() => window.open(`/?user_id=${u.id}`, '_blank')}
                                                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600/10 border border-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-all text-[9px] font-black uppercase tracking-widest"
                                                        >
                                                            <DesktopIcon size={12} /> HYPER-TRACE
                                                        </button>
                                                        <button
                                                            onClick={() => toggleUserStatus(u.id, u.is_active)}
                                                            className={`p-2 rounded-xl border transition-all ${u.is_active ? 'bg-rose-600/10 border-rose-600/20 text-rose-500 hover:bg-rose-600' : 'bg-emerald-600/10 border-emerald-600/20 text-emerald-500 hover:bg-emerald-600'} hover:text-white shadow-lg`}
                                                        >
                                                            {u.is_active ? <ShieldOff size={16} /> : <ShieldCheck size={16} />}
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    {/* Broadcast Module */}
                    <div className="glass-dark border border-white/5 rounded-[2.5rem] p-8 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-10 opacity-[0.02] pointer-events-none group-hover:scale-110 transition-transform">
                            <Send size={240} className="text-blue-500" />
                        </div>
                        <div className="flex items-center gap-4 mb-10 relative z-10">
                            <div className="p-4 bg-blue-600 rounded-3xl rotate-12 shadow-2xl shadow-blue-600/30">
                                <Send size={24} className="text-white" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-black text-white tracking-tighter italic uppercase">TACTICAL BROADCAST</h3>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em] mt-1">Global Communication Override</p>
                            </div>
                        </div>

                        <form onSubmit={sendNotification} className="space-y-8 relative z-10">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-4 block">Packet Header</label>
                                    <input
                                        type="text"
                                        value={notifTitle}
                                        onChange={(e) => setNotifTitle(e.target.value)}
                                        placeholder="SYSTEM ALERT: CORE UPGRADE..."
                                        className="w-full bg-white/[0.03] border border-white/10 rounded-2xl px-6 py-5 text-white focus:border-blue-500 outline-none font-black italic tracking-tight placeholder:text-slate-700 transition-all focus:bg-white/[0.06]"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-4 block">Transmission Class</label>
                                    <select
                                        value={notifLevel}
                                        onChange={(e) => setNotifLevel(e.target.value)}
                                        className="w-full bg-white/[0.03] border border-white/10 rounded-2xl px-6 py-5 text-white focus:border-blue-500 outline-none font-black uppercase tracking-widest text-xs appearance-none transition-all focus:bg-white/[0.06]"
                                    >
                                        <option value="info">🔵 CLASS-I: INFORMATION</option>
                                        <option value="success">🟢 CLASS-II: OPERATIONAL SUCCESS</option>
                                        <option value="warning">🟡 CLASS-III: SYSTEM CAVEAT</option>
                                        <option value="error">🔴 CLASS-IV: CRITICAL OVERRIDE</option>
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-4 block">Transmission Payload</label>
                                <textarea
                                    value={notifMessage}
                                    onChange={(e) => setNotifMessage(e.target.value)}
                                    placeholder="Enter encrypted or plain-text message relay..."
                                    rows={4}
                                    className="w-full bg-white/[0.03] border border-white/10 rounded-[2rem] px-8 py-6 text-white focus:border-blue-500 outline-none font-bold text-sm tracking-wide placeholder:text-slate-700 resize-none transition-all focus:bg-white/[0.06]"
                                />
                            </div>

                            <div className="flex flex-col xl:flex-row items-end gap-8">
                                <div className="flex-1 w-full space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-4 block">Destination Signature (PID)</label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            value={targetUserId}
                                            onChange={(e) => setTargetUserId(e.target.value)}
                                            placeholder="BROADCAST_TO_ALL_NODES"
                                            className="w-full bg-white/[0.03] border border-white/10 rounded-2xl px-6 py-5 text-white focus:border-blue-500 outline-none font-mono text-xs tracking-tight placeholder:text-slate-700 pr-24"
                                        />
                                        {targetUserId && <span className="absolute right-6 top-1/2 -translate-y-1/2 px-3 py-1 bg-blue-600 rounded-lg text-[8px] font-black text-white uppercase tracking-widest">Targeting</span>}
                                    </div>
                                </div>
                                <button
                                    type="submit"
                                    disabled={loading || !notifTitle || !notifMessage}
                                    className="h-16 w-full xl:w-72 bg-white text-slate-950 rounded-[1.5rem] font-black uppercase tracking-[0.2em] text-[11px] hover:bg-blue-400 disabled:opacity-30 disabled:hover:bg-white transition-all flex items-center justify-center gap-3 group shadow-2xl shadow-white/5 active:scale-95"
                                >
                                    {loading ? 'Transmitting Data...' : <><Zap size={16} className="group-hover:animate-pulse" /> Finalize Relay</>}
                                </button>
                            </div>

                            {status && (
                                <div className={`p-5 rounded-2xl border flex items-center gap-4 animate-bounce ${status.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
                                    <ShieldCheck size={20} />
                                    <span className="text-xs font-black uppercase tracking-widest">{status.message}</span>
                                </div>
                            )}
                        </form>
                    </div>
                </div>

                {/* Tactical Side Column */}
                <div className="lg:col-span-4 space-y-8">
                    {/* Global Activity Feed (NEW Logic) */}
                    <div className="glass-dark border border-white/5 rounded-[3rem] p-10 h-full relative overflow-hidden">
                        <div className="flex items-center gap-4 mb-10 relative z-10">
                            <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-[1.5rem] shadow-inner">
                                <Globe size={24} className="text-indigo-400" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-black text-white tracking-tighter uppercase italic">Global Intel</h3>
                                <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Real-time Node Activity Feed</p>
                            </div>
                        </div>

                        <div className="space-y-6 max-h-[680px] overflow-y-auto pr-4 custom-scrollbar relative z-10">
                            {activity.length > 0 ? activity.map((act) => (
                                <div key={act.id} className="relative group/act">
                                    <div className={`absolute -left-2 top-0 bottom-0 w-1 rounded-full transition-all group-hover/act:w-1.5 ${act.type === 'trade' ? 'bg-emerald-500' : act.type === 'decision' ? 'bg-indigo-500' : 'bg-slate-700'}`}></div>
                                    <div className="pl-6 py-2">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <div className="w-5 h-5 rounded-md bg-white/5 flex items-center justify-center">
                                                    {act.type === 'trade' ? <TrendingUp size={10} className="text-emerald-400" /> : act.type === 'decision' ? <Zap size={10} className="text-indigo-400" /> : <Activity size={10} className="text-slate-500" />}
                                                </div>
                                                <span className="text-[10px] font-black text-white uppercase italic tracking-tight">{act.username}</span>
                                                <span className={`text-[8px] px-2 py-0.5 rounded-full font-black uppercase tracking-tighter ${act.level === 'success' ? 'bg-emerald-500/10 text-emerald-500' : act.level === 'error' ? 'bg-rose-500/10 text-rose-500' : 'bg-indigo-500/10 text-indigo-400'}`}>
                                                    {act.code}
                                                </span>
                                            </div>
                                            <span className="text-[8px] font-black text-slate-600 font-mono italic">{format(new Date(act.timestamp), 'HH:mm:ss')}</span>
                                        </div>
                                        <p className="text-[11px] text-slate-400 font-bold leading-relaxed uppercase tracking-tight italic line-clamp-2 transition-colors group-hover/act:text-slate-200">
                                            {act.message}
                                        </p>
                                    </div>
                                </div>
                            )) : (
                                <div className="text-center py-20">
                                    <MousePointer2 className="mx-auto text-slate-800 mb-4 animate-bounce" size={48} />
                                    <p className="text-[10px] font-black text-slate-700 uppercase tracking-[0.3em]">No Intelligence Received</p>
                                </div>
                            )}
                        </div>

                        {/* Background Decor */}
                        <div className="absolute -right-20 -bottom-20 opacity-[0.05] pointer-events-none scale-150">
                            <BarChart3 size={300} />
                        </div>
                    </div>

                    {/* Security - Mini View */}
                    <div className="glass-dark border border-white/5 rounded-[2.5rem] p-8 bg-amber-950/5">
                        <div className="flex items-center gap-4 mb-8">
                            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-2xl">
                                <Terminal size={20} className="text-amber-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-black text-white tracking-tighter uppercase italic">Access Audit</h3>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Global Authentication Logs</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {logs.slice(0, 4).map(log => (
                                <div key={log.id} className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-2xl hover:border-amber-500/20 transition-all cursor-crosshair">
                                    <div className="flex items-center gap-4">
                                        <div className="p-2.5 bg-slate-900 rounded-xl border border-white/5">
                                            {log.os?.toLowerCase().includes('win') ? <DesktopIcon size={12} className="text-indigo-400" /> : <Smartphone size={12} className="text-amber-400" />}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2 mb-0.5">
                                                <span className="text-xs font-black text-white uppercase italic">{log.username}</span>
                                                <span className="text-[8px] font-mono text-amber-500 font-black opacity-60 tracking-tighter">{log.ip}</span>
                                            </div>
                                            <p className="text-[8px] text-slate-500 font-black uppercase tracking-widest italic">{log.browser} on {log.os}</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Creation Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-950/95 backdrop-blur-3xl animate-fadeIn">
                    <div className="absolute inset-0" onClick={() => setShowCreateModal(false)}></div>
                    <div className="relative w-full max-w-lg overflow-hidden glass-dark border border-white/10 rounded-[4rem] shadow-[0_0_100px_rgba(79,70,229,0.2)] p-12 transition-all scale-100 animate-modalEnter">
                        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-transparent via-indigo-600 to-transparent"></div>
                        <div className="flex items-center gap-6 mb-12">
                            <div className="p-6 bg-indigo-600 rounded-[2rem] shadow-2xl shadow-indigo-600/30 rotate-6">
                                <UserPlus className="text-white" size={36} />
                            </div>
                            <div>
                                <h3 className="text-4xl font-black text-white tracking-tighter italic uppercase leading-none">Global Deployment</h3>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.4em] mt-2">Provisioning Authorized Node Credentials</p>
                            </div>
                        </div>

                        <form onSubmit={createUser} className="space-y-10">
                            <div className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-6 block">Assigned Code-Name</label>
                                    <input
                                        type="text" required
                                        value={newUser.username}
                                        onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                                        className="w-full bg-white/[0.04] border border-white/10 rounded-2xl px-8 py-5 text-white focus:border-indigo-500 outline-none font-black italic tracking-tight placeholder:text-slate-800 transition-all focus:bg-white/[0.08]"
                                        placeholder="ALFA_TRANSMISSION_NODE"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-6 block">Transmission Relay Hub</label>
                                    <input
                                        type="email" required
                                        value={newUser.email}
                                        onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                                        className="w-full bg-white/[0.04] border border-white/10 rounded-2xl px-8 py-5 text-white focus:border-indigo-500 outline-none font-black italic tracking-tight placeholder:text-slate-800 transition-all focus:bg-white/[0.08]"
                                        placeholder="operational@antigravity.io"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-6 block">Master Access Keyphrase</label>
                                    <input
                                        type="password" required
                                        value={newUser.password}
                                        onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                        className="w-full bg-white/[0.04] border border-white/10 rounded-2xl px-8 py-5 text-white focus:border-indigo-500 outline-none font-black italic tracking-tight placeholder:text-slate-800 transition-all focus:bg-white/[0.08]"
                                        placeholder="••••••••••••••••"
                                    />
                                </div>
                            </div>

                            <div className="pt-6 flex gap-6">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="flex-1 py-6 bg-white/5 border border-white/10 text-white rounded-[2rem] font-black uppercase tracking-widest text-[10px] hover:bg-rose-600/20 hover:border-rose-600/30 transition-all active:scale-95"
                                >
                                    Abort Ops
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="flex-[2] py-6 bg-indigo-600 text-white rounded-[2rem] font-black uppercase tracking-[0.2em] text-[11px] shadow-2xl shadow-indigo-600/40 hover:scale-[1.02] transition-all hover:bg-indigo-500 active:scale-95"
                                >
                                    {loading ? 'DEPLOYING NODE...' : 'Commit Deployment'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
