import React, { useEffect, useMemo, useState } from 'react'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Brain, Clock3, Send, Sparkles, RefreshCw, Plus } from 'lucide-react'

type Conversation = {
  id: number
  title: string
  created_at: string
  updated_at: string
  last_message_at: string
}

type Message = {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  intent?: string
  confidence?: number
  status?: string
  processing_ms?: number
  created_at: string
}

const fmtTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString('vi-VN')
  } catch {
    return iso
  }
}

const orderQuestionThenAnswer = (items: Message[]) => {
  const out: Message[] = []
  let i = 0
  while (i < items.length) {
    const current = items[i]
    const next = items[i + 1]

    if (
      current?.role === 'assistant' &&
      next?.role === 'user' &&
      next.id < current.id
    ) {
      out.push(next, current)
      i += 2
      continue
    }

    out.push(current)
    i += 1
  }

  return out
}

export const MessageCenterPage: React.FC = () => {
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])

  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([])
  const [error, setError] = useState('')
  const messagesContainerRef = React.useRef<HTMLDivElement>(null)

  const loadConversations = async () => {
    const res = await api.getMessageConversations()
    const list = res.conversations || []
    setConversations(list)
    if (!activeConversationId && list.length > 0) {
      setActiveConversationId(list[0].id)
    }
  }

  const loadMessages = async (conversationId: number) => {
    const res = await api.getMessageConversationMessages(conversationId)
    setMessages(orderQuestionThenAnswer(res.messages || []))
  }

  const loadSuggestedQuestions = async () => {
    const res = await api.getMessageSuggestedQuestions()
    setSuggestedQuestions(res.questions || [])
  }

  const bootstrap = async () => {
    try {
      setLoading(true)
      setError('')
      await Promise.all([loadConversations(), loadSuggestedQuestions()])
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Không tải được Message Center')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    bootstrap()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([])
      return
    }
    loadMessages(activeConversationId).catch(() => setError('Không tải được lịch sử hội thoại'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConversationId])

  // Keep viewport pinned to top because newest messages are shown first
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = 0
    }
  }, [messages])

  const handleCreateConversation = async () => {
    try {
      setError('')
      const res = await api.createMessageConversation('Phiên trao đổi mới')
      const conv = res.conversation as Conversation
      setConversations((prev) => [conv, ...prev])
      setActiveConversationId(conv.id)
      setMessages([])
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Không tạo được phiên mới')
    }
  }

  const handleAsk = async () => {
    const q = question.trim()
    if (!q) return

    try {
      setSending(true)
      setError('')

      const res = await api.askMessageCenter(q, activeConversationId || undefined)
      const convId = res.conversation_id as number

      if (!activeConversationId) {
        setActiveConversationId(convId)
      }

      setQuestion('')
      await loadConversations()
      await loadMessages(convId)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Gửi câu hỏi thất bại')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-300">
          <RefreshCw className="animate-spin" size={18} />
          <span className="text-sm font-bold">Đang tải Message Ops Center...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 md:space-y-6 bg-mesh min-h-full pb-20 px-4 pt-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Brain size={20} className="md:w-[22px] md:h-[22px] text-blue-400" />
            <span className="text-[10px] md:text-xs font-black uppercase tracking-widest text-blue-400">Trader Communication Function</span>
          </div>
          <h1 className="text-2xl md:text-4xl font-black text-gradient">Message Ops Center</h1>
          <p className="text-slate-400 text-xs md:text-sm mt-1">Hỏi đáp vận hành trading theo dữ liệu thật của hệ thống (không phải chatbot demo).</p>
        </div>
        <button
          onClick={handleCreateConversation}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-black text-xs uppercase tracking-wider whitespace-nowrap"
        >
          <Plus size={14} />
          Phiên mới
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 md:gap-6">
        <div className="xl:col-span-3 card p-3 md:p-4 border border-white/10 bg-slate-900/40 rounded-2xl">
          <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-3">Lịch sử phiên</h3>
          <div className="space-y-2 max-h-[40vh] md:max-h-[65vh] overflow-auto custom-scrollbar">
            {conversations.length === 0 ? (
              <p className="text-xs text-slate-500">Chưa có hội thoại. Hãy gửi câu hỏi đầu tiên.</p>
            ) : (
              conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActiveConversationId(c.id)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    activeConversationId === c.id
                      ? 'bg-blue-500/10 border-blue-500/40'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <p className="text-xs font-bold text-slate-200 line-clamp-2">{c.title}</p>
                  <p className="text-[10px] text-slate-500 mt-1">{fmtTime(c.last_message_at)}</p>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="xl:col-span-9 space-y-3 md:space-y-4">
          <div className="card p-3 md:p-4 border border-white/10 bg-slate-900/40 rounded-2xl">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-3">Đặt câu hỏi vận hành</h3>
            <div className="flex flex-col lg:grid lg:grid-cols-12 gap-2 md:gap-3">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ví dụ: Ê hôm nay bot trade thế nào rồi? Sao chưa vào lệnh?"
                className="lg:col-span-10 min-h-[80px] md:min-h-[86px] bg-slate-950/40 border border-white/10 rounded-xl p-2 md:p-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50"
              />
              <button
                onClick={handleAsk}
                disabled={sending || question.trim().length < 3}
                className="lg:col-span-2 h-[44px] lg:h-auto rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-black text-xs uppercase tracking-wider disabled:opacity-50"
              >
                {sending ? (
                  <span className="flex items-center justify-center gap-2"><RefreshCw size={14} className="animate-spin" />Đang xử lý</span>
                ) : (
                  <span className="flex items-center justify-center gap-2"><Send size={14} />Gửi</span>
                )}
              </button>
            </div>

            {suggestedQuestions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {suggestedQuestions.map((sq, idx) => (
                  <button
                    key={idx}
                    onClick={() => setQuestion(sq)}
                    className="px-3 py-1.5 rounded-full text-[11px] font-semibold bg-white/5 hover:bg-blue-500/20 border border-white/10 text-slate-300"
                  >
                    <Sparkles size={10} className="inline mr-1 text-blue-400" />
                    {sq}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="card p-3 md:p-4 border border-white/10 bg-slate-900/40 rounded-2xl">
            <h3 className="text-[10px] md:text-xs font-black uppercase tracking-widest text-slate-400 mb-3">📍 Timeline phản hồi (mới nhất ở trên, hỏi trước đáp sau)</h3>
            <div ref={messagesContainerRef} className="space-y-2 md:space-y-3 max-h-[50vh] md:max-h-[62vh] overflow-y-auto custom-scrollbar pr-1">
              {messages.length === 0 ? (
                <div className="p-6 text-center text-slate-500 text-sm">
                  Chưa có dữ liệu trong phiên này.
                </div>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className={`p-3 md:p-4 rounded-xl border transition ${
                      m.role === 'user'
                        ? 'border-cyan-500/30 bg-cyan-500/5 hover:bg-cyan-500/10'
                        : 'border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 sm:gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${m.role === 'user' ? 'bg-cyan-400' : 'bg-emerald-400'}`}></div>
                        <span className="text-xs md:text-sm font-black uppercase tracking-wider text-slate-200">
                          {m.role === 'user' ? '👤 Trader Question' : '🤖 AI Operational Reply'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 md:gap-2 text-[10px] md:text-xs text-slate-300 flex-wrap justify-start sm:justify-end">
                        <span className="flex items-center gap-1"><Clock3 size={10} />{fmtTime(m.created_at)}</span>
                        {m.intent && <span className="px-2 py-0.5 rounded bg-white/5 text-cyan-200">intent: {m.intent}</span>}
                        {typeof m.confidence === 'number' && <span className="px-2 py-0.5 rounded bg-white/5 text-slate-200">conf: {(m.confidence * 100).toFixed(0)}%</span>}
                        {typeof m.processing_ms === 'number' && m.role === 'assistant' && <span className="px-2 py-0.5 rounded bg-white/5 text-slate-200">{m.processing_ms}ms</span>}
                      </div>
                    </div>
                    <div className="whitespace-pre-wrap break-words text-[15px] md:text-base text-slate-50 leading-8 font-medium">{m.content}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MessageCenterPage
