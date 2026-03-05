import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'

export interface ApiConfig {
  baseURL: string
  token?: string
}

export class ApiClient {
  private _axiosInstance: AxiosInstance

  constructor(config: ApiConfig) {
    console.log('📡 API Client initialized with baseURL:', config.baseURL)
    this._axiosInstance = axios.create({
      baseURL: config.baseURL,
      headers: {
        'Content-Type': 'application/json',
        ...(config.token && { 'Authorization': `Bearer ${config.token}` }),
      },
    })

    // Response interceptor for error handling
    this._axiosInstance.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired - trigger re-auth
          window.dispatchEvent(new Event('auth:expired'))
        }
        return Promise.reject(error)
      }
    )
  }

  // Public getter for axiosInstance
  get axiosInstance(): AxiosInstance {
    return this._axiosInstance
  }

  // Generic helpers
  async get<T = any>(url: string, config?: AxiosRequestConfig) {
    const res = await this._axiosInstance.get<T>(url, config)
    return res
  }

  async post<T = any>(url: string, data?: any) {
    const res = await this._axiosInstance.post<T>(url, data)
    return res
  }

  // Auth endpoints
  async getSystemStatus() {
    const res = await this._axiosInstance.get('system/status')
    return res.data
  }

  async login(username: string, password: string) {
    console.log('🔐 Attempting login with:', { username })
    const res = await this._axiosInstance.post('auth/login', {
      username,
      password,
    })
    console.log('✅ Login response:', res.data)
    return res.data
  }

  async logout() {
    return this._axiosInstance.post('auth/logout')
  }

  async refreshToken(token: string) {
    const res = await this._axiosInstance.post('auth/refresh', {
      token,
    })
    return res.data
  }

  // Dashboard endpoints
  async getBotStatus() {
    const res = await this._axiosInstance.get('bot/status')
    return res.data
  }

  async getPositions() {
    // Use /live endpoint to get real-time data directly from Binance
    // Falls back to regular /positions if /live is not available
    try {
      const res = await this._axiosInstance.get('positions/live')
      return res.data?.positions || []
    } catch (error) {
      // Fallback to local database positions if live endpoint fails
      const res = await this._axiosInstance.get('positions')
      return res.data
    }
  }

  async getOrders(limit = 100) {
    const res = await this._axiosInstance.get(`orders?limit=${limit}`)
    return res.data
  }

  async getTrades(limit = 100) {
    const res = await this._axiosInstance.get(`trades?limit=${limit}`)
    return res.data
  }

  async closePosition(symbol: string) {
    const res = await this._axiosInstance.post(`positions/${symbol}/close`)
    return res.data
  }

  async openPosition(payload: { symbol: string, side: string, leverage: number, size_pct: number }) {
    const res = await this._axiosInstance.post('positions/open', payload)
    return res.data
  }

  async getSignals(limit = 50) {
    const res = await this._axiosInstance.get(`signals?limit=${limit}`)
    return res.data
  }

  async getDecisions(limit = 100) {
    const res = await this._axiosInstance.get(`decisions?limit=${limit}`)
    return res.data
  }

  async getWalletBalance() {
    const res = await this._axiosInstance.get('wallet/balance')
    return res.data
  }

  async getDecisionTrace(traceId: string) {
    const res = await this._axiosInstance.get(`decisions/${traceId}`)
    return res.data
  }

  async getReconSummary() {
    const res = await this._axiosInstance.get('recon/summary')
    return res.data
  }

  async getLatencyMetrics() {
    const res = await this._axiosInstance.get('health/latency')
    return res.data
  }

  async getHealthStatus() {
    const res = await this._axiosInstance.get('health/status')
    return res.data
  }

  async getLlmTokenUsage() {
    const res = await this._axiosInstance.get('llm/token-usage')
    return res.data
  }

  async getEvents(limit = 100) {
    const res = await this._axiosInstance.get(`events?limit=${limit}`)
    return res.data
  }

  async logAccessTelemetry(payload: Record<string, any>) {
    const res = await this._axiosInstance.post('access/telemetry', payload)
    return res.data
  }

  async getPnlHistory(days = 7) {
    const res = await this._axiosInstance.get(`reports/pnl-history?days=${days}`)
    return res.data
  }

  // Config endpoints
  async getRiskConfig() {
    const res = await this._axiosInstance.get('config/risk')
    return res.data
  }

  async updateRiskConfig(config: Record<string, any>) {
    const res = await this._axiosInstance.post('config/risk', config)
    return res.data
  }

  async getRiskConfigVersions() {
    const res = await this._axiosInstance.get('config/risk/versions')
    return res.data
  }

  async rollbackRiskConfig(versionId: string) {
    const res = await this._axiosInstance.post(`config/risk/rollback/${versionId}`)
    return res.data
  }

  // Audit endpoints
  async getAuditLog(limit = 100, offset = 0) {
    const res = await this._axiosInstance.get(
      `audit?limit=${limit}&offset=${offset}`
    )
    return res.data
  }

  // Control endpoints
  async pauseTrading() {
    return this._axiosInstance.post('actions/pause')
  }

  async resumeTrading() {
    return this._axiosInstance.post('actions/resume')
  }

  async syncNow() {
    return this._axiosInstance.post('actions/sync_now')
  }

  async getActionsStatus() {
    const res = await this._axiosInstance.get('actions/status')
    return res.data
  }

  async updateApprovalMode(enabled: boolean) {
    const res = await this._axiosInstance.post(`actions/approval-mode?enabled=${enabled}`)
    return res.data
  }

  async approveDecision(traceId: string) {
    const res = await this._axiosInstance.post(`actions/approve-decision/${traceId}`)
    return res.data
  }

  // Prompt packs endpoints
  async getPromptPacks() {
    const res = await this._axiosInstance.get('prompt-packs')
    return res.data
  }

  async uploadPromptPack(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await this._axiosInstance.post('prompt-packs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  }

  async activatePromptPack(packId: string) {
    return this._axiosInstance.post(`prompt-packs/${packId}/activate`)
  }

  // Settings endpoints
  async getSettings() {
    const res = await this._axiosInstance.get('settings')
    return res.data
  }

  async updateSettings(payload: Record<string, any>) {
    const res = await this._axiosInstance.put('settings', payload)
    return res.data
  }

  async testBinance() {
    const res = await this._axiosInstance.post('settings/test/binance')
    return res.data
  }

  async testTelegram() {
    const res = await this._axiosInstance.post('settings/test/telegram')
    return res.data
  }

  // Intelligence / News Sources
  async getNewsSources() {
    const res = await this._axiosInstance.get('intelligence/sources')
    return res.data
  }

  async addNewsSource(payload: { name: string, url: string, source_type: string }) {
    const res = await this._axiosInstance.post('intelligence/sources', payload)
    return res.data
  }

  async deleteNewsSource(sourceId: number) {
    const res = await this._axiosInstance.delete(`intelligence/sources/${sourceId}`)
    return res.data
  }

  // Message Center endpoints
  async getMessageConversations() {
    const res = await this._axiosInstance.get('message-center/conversations')
    return res.data
  }

  async createMessageConversation(title?: string) {
    const res = await this._axiosInstance.post('message-center/conversations', {
      title,
    })
    return res.data
  }

  async getMessageConversationMessages(conversationId: number) {
    const res = await this._axiosInstance.get(`message-center/conversations/${conversationId}/messages`)
    return res.data
  }

  async askMessageCenter(question: string, conversationId?: number) {
    const res = await this._axiosInstance.post('message-center/ask', {
      question,
      conversation_id: conversationId,
      timezone_name: 'Asia/Ho_Chi_Minh',
    })
    return res.data
  }

  async getMessageSuggestedQuestions() {
    const res = await this._axiosInstance.get('message-center/suggested-questions')
    return res.data
  }
}

export const getApiBaseUrl = () => {
  const envUrl = (import.meta as any).env.VITE_API_BASE_URL
  return envUrl && envUrl.trim().length > 0
    ? envUrl
    : 'http://localhost:8000/api/'
}

export const createApiClient = (baseURL?: string, token?: string) => {
  return new ApiClient({ baseURL: baseURL ?? getApiBaseUrl(), token })
}
