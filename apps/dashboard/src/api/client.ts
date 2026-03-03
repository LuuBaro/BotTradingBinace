import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'

export interface ApiConfig {
  baseURL: string
  token?: string
}

export class ApiClient {
  private axiosInstance: AxiosInstance

  private targetUserId: string | null = null

  constructor(config: ApiConfig) {
    console.log('📡 API Client initialized with baseURL:', config.baseURL)
    this.axiosInstance = axios.create({
      baseURL: config.baseURL,
      headers: {
        'Content-Type': 'application/json',
        ...(config.token && { 'Authorization': `Bearer ${config.token}` }),
      },
    })

    // Check for user_id in URL to support admin monitoring
    const params = new URLSearchParams(window.location.search)
    this.targetUserId = params.get('user_id')

    // Response interceptor for error handling
    this.axiosInstance.interceptors.response.use(
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

  setTargetUserId(id: string | null) {
    this.targetUserId = id
  }

  // Generic helpers
  async get<T = any>(url: string, config?: AxiosRequestConfig) {
    const finalUrl = this.targetUserId && !url.includes('user_id=')
      ? `${url}${url.includes('?') ? '&' : '?'}user_id=${this.targetUserId}`
      : url
    const res = await this.axiosInstance.get<T>(finalUrl, config)
    return res
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig) {
    const finalUrl = this.targetUserId && !url.includes('user_id=')
      ? `${url}${url.includes('?') ? '&' : '?'}user_id=${this.targetUserId}`
      : url
    const res = await this.axiosInstance.post<T>(finalUrl, data, config)
    return res
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig) {
    const finalUrl = this.targetUserId && !url.includes('user_id=')
      ? `${url}${url.includes('?') ? '&' : '?'}user_id=${this.targetUserId}`
      : url
    const res = await this.axiosInstance.put<T>(finalUrl, data, config)
    return res
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig) {
    const finalUrl = this.targetUserId && !url.includes('user_id=')
      ? `${url}${url.includes('?') ? '&' : '?'}user_id=${this.targetUserId}`
      : url
    const res = await this.axiosInstance.delete<T>(finalUrl, config)
    return res
  }

  async request<T = any>(config: AxiosRequestConfig) {
    const res = await this.axiosInstance.request<T>(config)
    return res
  }

  // Auth endpoints
  async getSystemStatus() {
    const res = await this.axiosInstance.get('system/status')
    return res.data
  }

  async login(username: string, password: string) {
    console.log('🔐 Attempting login with:', { username })
    const res = await this.axiosInstance.post('auth/login', {
      username,
      password,
    })
    console.log('✅ Login response:', res.data)
    return res.data
  }

  async logout() {
    return this.axiosInstance.post('auth/logout')
  }

  async refreshToken(token: string) {
    const res = await this.axiosInstance.post('auth/refresh', {
      token,
    })
    return res.data
  }

  // Dashboard endpoints
  async getBotStatus() {
    const res = await this.get('bot/status')
    return res.data
  }

  async getPositions() {
    try {
      const res = await this.get('positions/live')
      return res.data?.positions || []
    } catch (error) {
      const res = await this.get('positions')
      return res.data
    }
  }

  async getOrders(limit = 100) {
    const res = await this.get(`orders?limit=${limit}`)
    return res.data
  }

  async getTrades(limit = 100) {
    const res = await this.get(`trades?limit=${limit}`)
    return res.data
  }

  async closePosition(symbol: string) {
    const res = await this.post(`positions/${symbol}/close`)
    return res.data
  }

  async openPosition(payload: { symbol: string, side: string, leverage: number, size_pct: number }) {
    const res = await this.post('positions/open', payload)
    return res.data
  }

  async getSignals(limit = 50) {
    const res = await this.get(`signals?limit=${limit}`)
    return res.data
  }

  async getDecisions(limit = 100) {
    const res = await this.get(`decisions?limit=${limit}`)
    return res.data
  }

  async getWalletBalance() {
    const res = await this.get('wallet/balance')
    return res.data
  }

  async getDecisionTrace(traceId: string) {
    const res = await this.get(`decisions/${traceId}`)
    return res.data
  }

  async getRiskLogs(limit = 100) {
    const res = await this.get(`risk/logs?limit=${limit}`)
    return res.data
  }

  async getReconSummary() {
    const res = await this.get('recon/summary')
    return res.data
  }

  async getLatencyMetrics() {
    const res = await this.get('health/latency')
    return res.data
  }

  async getHealthStatus() {
    const res = await this.get('health/status')
    return res.data
  }

  async getEvents(limit = 100) {
    const res = await this.get(`events?limit=${limit}`)
    return res.data
  }

  async getPnlHistory(days = 7) {
    const res = await this.get(`reports/pnl-history?days=${days}`)
    return res.data
  }

  // Config endpoints
  async getRiskConfig() {
    const res = await this.get('config/risk')
    return res.data
  }

  async updateRiskConfig(config: Record<string, any>) {
    const res = await this.axiosInstance.post('config/risk', config)
    return res.data
  }

  async getRiskConfigVersions() {
    const res = await this.get('config/risk/versions')
    return res.data
  }

  async rollbackRiskConfig(versionId: string) {
    const res = await this.axiosInstance.post(`config/risk/rollback/${versionId}`)
    return res.data
  }

  // Audit endpoints
  async getAuditLog(limit = 100, offset = 0) {
    const res = await this.get(
      `audit?limit=${limit}&offset=${offset}`
    )
    return res.data
  }

  // Control endpoints
  async pauseTrading() {
    return this.axiosInstance.post('actions/pause')
  }

  async resumeTrading() {
    return this.axiosInstance.post('actions/resume')
  }

  async syncNow() {
    return this.axiosInstance.post('actions/sync_now')
  }

  async getActionsStatus() {
    const res = await this.axiosInstance.get('actions/status')
    return res.data
  }

  async updateApprovalMode(enabled: boolean) {
    const res = await this.axiosInstance.post(`actions/approval-mode?enabled=${enabled}`)
    return res.data
  }

  async approveDecision(traceId: string) {
    const res = await this.axiosInstance.post(`actions/approve-decision/${traceId}`)
    return res.data
  }

  // Prompt packs endpoints
  async getPromptPacks() {
    const res = await this.axiosInstance.get('prompt-packs')
    return res.data
  }

  async uploadPromptPack(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await this.axiosInstance.post('prompt-packs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  }

  async activatePromptPack(packId: string) {
    return this.axiosInstance.post(`prompt-packs/${packId}/activate`)
  }

  // Settings endpoints
  async getSettings() {
    const res = await this.axiosInstance.get('settings')
    return res.data
  }

  async updateSettings(payload: Record<string, any>) {
    const res = await this.put('settings', payload)
    return res.data
  }

  async testBinance() {
    const res = await this.axiosInstance.post('settings/test/binance')
    return res.data
  }

  async testTelegram() {
    const res = await this.axiosInstance.post('settings/test/telegram')
    return res.data
  }

  // Intelligence / News Sources
  async getNewsSources() {
    const res = await this.axiosInstance.get('intelligence/sources')
    return res.data
  }

  async addNewsSource(payload: { name: string, url: string, source_type: string }) {
    const res = await this.axiosInstance.post('intelligence/sources', payload)
    return res.data
  }

  async deleteNewsSource(sourceId: number) {
    const res = await this.axiosInstance.delete(`intelligence/sources/${sourceId}`)
    return res.data
  }

  // AI Chat
  async chatWithAi(message: string, symbol?: string) {
    const res = await this.axiosInstance.post('ai/chat', { message, symbol })
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
