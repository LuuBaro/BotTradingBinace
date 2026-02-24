import axios, { AxiosInstance, AxiosError } from 'axios'

export interface ApiConfig {
  baseURL: string
  token?: string
}

export class ApiClient {
  private axiosInstance: AxiosInstance

  constructor(config: ApiConfig) {
    console.log('📡 API Client initialized with baseURL:', config.baseURL)
    this.axiosInstance = axios.create({
      baseURL: config.baseURL,
      headers: {
        'Content-Type': 'application/json',
        ...(config.token && { 'Authorization': `Bearer ${config.token}` }),
      },
    })

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

  // Auth endpoints
  async login(username: string, password: string) {
    console.log('🔐 Attempting login with:', { username })
    const res = await this.axiosInstance.post('/auth/login', {
      username,
      password,
    })
    console.log('✅ Login response:', res.data)
    return res.data
  }

  async logout() {
    return this.axiosInstance.post('/auth/logout')
  }

  async refreshToken(token: string) {
    const res = await this.axiosInstance.post('/auth/refresh', {
      token,
    })
    return res.data
  }

  // Dashboard endpoints
  async getBotStatus() {
    const res = await this.axiosInstance.get('/bot/status')
    return res.data
  }

  async getPositions() {
    const res = await this.axiosInstance.get('/positions')
    return res.data
  }

  async getOrders() {
    const res = await this.axiosInstance.get('/orders')
    return res.data
  }

  async getDecisions(limit = 100) {
    const res = await this.axiosInstance.get(`/decisions?limit=${limit}`)
    return res.data
  }

  async getDecisionTrace(traceId: string) {
    const res = await this.axiosInstance.get(`/decisions/${traceId}`)
    return res.data
  }

  async getReconSummary() {
    const res = await this.axiosInstance.get('/recon/summary')
    return res.data
  }

  async getLatencyMetrics() {
    const res = await this.axiosInstance.get('/health/latency')
    return res.data
  }

  async getHealthStatus() {
    const res = await this.axiosInstance.get('/health/status')
    return res.data
  }

  // Config endpoints
  async getRiskConfig() {
    const res = await this.axiosInstance.get('/config/risk')
    return res.data
  }

  async updateRiskConfig(config: Record<string, any>) {
    const res = await this.axiosInstance.post('/config/risk', config)
    return res.data
  }

  async getRiskConfigVersions() {
    const res = await this.axiosInstance.get('/config/risk/versions')
    return res.data
  }

  async rollbackRiskConfig(versionId: string) {
    const res = await this.axiosInstance.post(`/config/risk/rollback/${versionId}`)
    return res.data
  }

  // Audit endpoints
  async getAuditLog(limit = 100, offset = 0) {
    const res = await this.axiosInstance.get(
      `/audit?limit=${limit}&offset=${offset}`
    )
    return res.data
  }

  // Control endpoints
  async pauseTrading() {
    return this.axiosInstance.post('/actions/pause')
  }

  async resumeTrading() {
    return this.axiosInstance.post('/actions/resume')
  }

  async syncNow() {
    return this.axiosInstance.post('/actions/sync_now')
  }

  // Prompt packs endpoints
  async getPromptPacks() {
    const res = await this.axiosInstance.get('/prompt-packs')
    return res.data
  }

  async uploadPromptPack(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await this.axiosInstance.post('/prompt-packs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  }

  async activatePromptPack(packId: string) {
    return this.axiosInstance.post(`/prompt-packs/${packId}/activate`)
  }
}

export const createApiClient = (baseURL: string, token?: string) => {
  return new ApiClient({ baseURL, token })
}
