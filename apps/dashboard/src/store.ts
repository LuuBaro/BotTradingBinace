import { create } from 'zustand'

// Auth Store
export interface AuthState {
  token: string | null
  user: { id: string; username: string; role: string } | null
  isAuthenticated: boolean
  setToken: (token: string) => void
  setUser: (user: AuthState['user']) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  isAuthenticated: !!localStorage.getItem('token'),
  setToken: (token) => {
    localStorage.setItem('token', token)
    set({ token, isAuthenticated: true })
  },
  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user))
    set({ user })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null, isAuthenticated: false })
  },
}))

// Dashboard State
export interface BotStatus {
  mode: string
  uptime_seconds: number
  paused: boolean
  total_positions: number
  total_orders: number
}

export interface Position {
  id: string
  symbol: string
  qty: number
  entry_price: number
  unrealized_pnl: number
  stop_loss: number | null
  take_profit: number | null
  leverage: number
}

export interface Order {
  id: string
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  status: string
  created_at: string
}

export interface Decision {
  id: string
  symbol: string
  action: string
  confidence: number
  regime: string
  timestamp: string
  trace_id: string
}

export interface DashboardState {
  botStatus: BotStatus | null
  positions: Position[]
  orders: Order[]
  latency: { ws_p95: number; rest_p95: number; clock_skew: number } | null
  health: Record<string, any> | null
  pnlToday: number
  setBotStatus: (status: BotStatus) => void
  setPositions: (positions: Position[]) => void
  setOrders: (orders: Order[]) => void
  setLatency: (latency: any) => void
  setHealth: (health: any) => void
  setPnlToday: (pnl: number) => void
  updatePosition: (position: Position) => void
  updateOrder: (order: Order) => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  botStatus: null,
  positions: [],
  orders: [],
  latency: null,
  health: null,
  pnlToday: 0,
  setBotStatus: (status) => set({ botStatus: status }),
  setPositions: (positions) => set({ positions }),
  setOrders: (orders) => set({ orders }),
  setLatency: (latency) => set({ latency }),
  setHealth: (health) => set({ health }),
  setPnlToday: (pnl) => set({ pnlToday: pnl }),
  updatePosition: (position) =>
    set((state) => ({
      positions: state.positions.map((p) => (p.id === position.id ? position : p)),
    })),
  updateOrder: (order) =>
    set((state) => ({
      orders: state.orders.map((o) => (o.id === order.id ? order : o)),
    })),
}))

// Events Store
export interface Event {
  id: string
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  details?: Record<string, any>
}

export interface EventsState {
  events: Event[]
  addEvent: (event: Event) => void
  clearEvents: () => void
}

export const useEventsStore = create<EventsState>((set) => ({
  events: [],
  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, 1000), // Keep last 1000
    })),
  clearEvents: () => set({ events: [] }),
}))

// Config Store
export interface RiskConfig {
  max_leverage: number
  max_position_size: number
  max_daily_loss: number
  min_win_rate: number
  [key: string]: any
}

export interface ConfigVersion {
  id: string
  config: RiskConfig
  created_at: string
  created_by: string
  description: string
}

export interface ConfigState {
  currentConfig: RiskConfig | null
  versions: ConfigVersion[]
  selectedVersionId: string | null
  setConfig: (config: RiskConfig) => void
  setVersions: (versions: ConfigVersion[]) => void
  setSelectedVersion: (versionId: string) => void
}

export const useConfigStore = create<ConfigState>((set) => ({
  currentConfig: null,
  versions: [],
  selectedVersionId: null,
  setConfig: (config) => set({ currentConfig: config }),
  setVersions: (versions) => set({ versions }),
  setSelectedVersion: (versionId) => set({ selectedVersionId: versionId }),
}))
