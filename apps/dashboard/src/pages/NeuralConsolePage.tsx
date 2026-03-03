import React, { useState, useEffect, useRef } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Send, User, Cpu, Brain, Zap, Shield, ChevronRight } from 'lucide-react'

interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    isThinking?: boolean
}

export const NeuralConsolePage: React.FC = () => {
    const api = createApiClient(getApiBaseUrl(), localStorage.getItem('token') || '')
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: 'Chào sếp! Tôi là Antigravity AI, người trực tiếp quản lý các lệnh trade của sếp. Sếp muốn hỏi gì về tình hình thị trường hay các lệnh tôi đang giữ không?',
            timestamp: new Date()
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [lastEvent, setLastEvent] = useState<any>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        const loadHistory = async () => {
            try {
                // Check for existing history in API client
                const history = await api.get('/ai/chat/history')
                if (history && history.data && history.data.length > 0) {
                    const formatted = history.data.map((m: any) => ({
                        id: m.id.toString(),
                        role: m.role,
                        content: m.content,
                        timestamp: new Date(m.timestamp)
                    }))
                    setMessages(formatted)
                }
            } catch (err) {
                console.error('Failed to load chat history:', err)
            }
        }

        const fetchStatus = async () => {
            try {
                const res = await api.get('events?limit=1')
                if (res.data?.events?.length > 0) {
                    setLastEvent(res.data.events[0])
                }
            } catch (e) { }
        }

        loadHistory()
        fetchStatus()
        const interval = setInterval(fetchStatus, 3000)

        scrollToBottom()
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSend = async (e?: React.FormEvent) => {
        e?.preventDefault()
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)

        // Add thinking message
        const thinkingId = (Date.now() + 1).toString()
        setMessages(prev => [...prev, {
            id: thinkingId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isThinking: true
        }])

        try {
            const res = await api.chatWithAi(input)

            setMessages(prev => prev.filter(m => m.id !== thinkingId).concat({
                id: Date.now().toString(),
                role: 'assistant',
                content: res.message,
                timestamp: new Date()
            }))
        } catch (err) {
            setMessages(prev => prev.filter(m => m.id !== thinkingId).concat({
                id: Date.now().toString(),
                role: 'assistant',
                content: 'Xin lỗi sếp, kết nối với bộ não AI của tôi đang bị gián đoạn. Sếp thử lại sau nhé!',
                timestamp: new Date()
            }))
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="flex flex-col h-[calc(100vh-140px)] animate-fadeIn">
            {/* Console Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <Cpu className="text-blue-400" size={14} />
                        <span className="text-[10px] uppercase font-black tracking-[0.3em] text-blue-400">Direct Neural Interface</span>
                    </div>
                    <h1 className="text-4xl font-black tracking-tighter text-white flex items-center gap-3">
                        Neural Console
                        <span className="px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/20 text-[10px] font-black text-blue-400 uppercase tracking-widest align-middle">Beta</span>
                    </h1>
                    <p className="text-slate-400 font-medium">Đối thoại trực tiếp với AI Trading Agent để quản lý và theo dõi hiệu suất.</p>
                </div>

                <div className="hidden lg:flex items-center gap-4 bg-slate-900/50 p-4 rounded-2xl border border-white/5">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                            <Brain size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Active Agent</p>
                            <p className="text-xs font-bold text-white uppercase tracking-tighter">Antigravity-v4.2</p>
                        </div>
                    </div>
                    <div className="h-8 w-[1px] bg-white/5"></div>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                            <Shield size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Protocol</p>
                            <p className="text-xs font-bold text-white uppercase tracking-tighter">Secure-Sudo</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Live Engine Status (Overlay) */}
            <div className="mb-6 flex items-center gap-4 px-6 py-3 bg-blue-500/5 border border-blue-500/10 rounded-2xl animate-fadeIn">
                <div className="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)] animate-pulse"></div>
                <div className="flex-1 flex items-center justify-between">
                    <p className="text-[10px] font-black uppercase tracking-widest text-blue-400">
                        {lastEvent ? lastEvent.message : "Engine Initializing..."}
                    </p>
                    <span className="text-[9px] font-mono text-blue-500/30 uppercase">{lastEvent ? lastEvent.code : "SYNC"}</span>
                </div>
            </div>

            {/* Terminal Viewport */}
            <div className="flex-1 flex flex-col glass-dark border-white/5 rounded-3xl overflow-hidden relative shadow-2xl">
                {/* Background Grid Layer */}
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none"></div>
                <div className="absolute inset-0 bg-gradient-to-b from-blue-500/[0.02] to-transparent pointer-events-none"></div>

                {/* Console Content */}
                <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-8 custom-scrollbar">
                    {messages.map((msg) => (
                        <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slideUp`}>
                            <div className={`flex gap-4 max-w-[85%] md:max-w-[70%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                {/* Avatar */}
                                <div className={`p-3 h-12 w-12 rounded-2xl border flex-shrink-0 flex items-center justify-center transition-all shadow-lg ${msg.role === 'user'
                                    ? 'bg-slate-800 border-white/10 text-slate-400 group-hover:border-blue-500/50'
                                    : 'bg-blue-600/10 border-blue-500/20 text-blue-400 shadow-blue-500/5'
                                    }`}>
                                    {msg.role === 'user' ? <User size={20} /> : <Zap size={20} />}
                                </div>

                                {/* Content Bubble */}
                                <div className="space-y-2">
                                    <div className={`flex items-center gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                                            {msg.role === 'user' ? 'System Administrator' : 'Neural Agent v4'}
                                        </span>
                                        <span className="text-[9px] text-slate-600 font-mono">
                                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>

                                    <div className={`p-5 rounded-3xl border whitespace-pre-wrap leading-relaxed text-sm shadow-xl transition-all ${msg.role === 'user'
                                        ? 'bg-slate-800/80 border-white/5 text-white rounded-tr-none'
                                        : 'bg-blue-600/5 border-blue-500/20 text-slate-200 rounded-tl-none hover:border-blue-500/40'
                                        }`}>
                                        {msg.isThinking ? (
                                            <div className="flex gap-1 items-center py-1">
                                                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                                                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-.15s]"></div>
                                                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-.3s]"></div>
                                                <span className="text-[10px] font-black uppercase text-blue-500/50 tracking-widest ml-2">Analyzing Context...</span>
                                            </div>
                                        ) : (
                                            msg.content
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Console Input */}
                <div className="p-6 md:p-8 bg-white/[0.02] border-t border-white/5 relative z-10 backdrop-blur-xl">
                    <form onSubmit={handleSend} className="relative group max-w-4xl mx-auto">
                        <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                            <ChevronRight size={18} />
                        </div>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={isLoading}
                            placeholder="Type your command or question to the AI Trader..."
                            className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 pl-14 pr-32 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all shadow-inner"
                        />
                        <div className="absolute inset-y-0 right-3 flex items-center gap-2">
                            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-white/5 rounded-lg border border-white/5 text-[10px] text-slate-500 font-mono">
                                <span className="opacity-50 font-sans">CMD</span>
                                <span>Enter</span>
                            </div>
                            <button
                                type="submit"
                                disabled={!input.trim() || isLoading}
                                className="p-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:bg-slate-700 text-white rounded-xl transition-all shadow-lg shadow-blue-500/20 active:scale-95 flex items-center justify-center"
                            >
                                <Send size={18} />
                            </button>
                        </div>
                    </form>
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                        {[
                            "Tình hình các lệnh trade?",
                            "Tại sao hôm nay không có lệnh nào?",
                            "Giải thích chiến lược hiện tại?",
                            "Phân tích BTC giúp tôi"
                        ].map(suggestion => (
                            <button
                                key={suggestion}
                                onClick={() => setInput(suggestion)}
                                className="px-4 py-1.5 rounded-full bg-white/5 border border-white/5 hover:border-blue-500/30 hover:bg-blue-500/5 text-[10px] font-bold text-slate-500 hover:text-blue-400 transition-all uppercase tracking-widest"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
