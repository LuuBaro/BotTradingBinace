import React, { useState } from 'react'
import { useAuthStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setToken, setUser } = useAuthStore()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.login(username, password)

      if (response.access_token) {
        setToken(response.access_token)
        setUser({
          id: response.user.id,
          username: response.user.username,
          role: response.user.role,
        })
        window.location.href = '/'
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="card w-full max-w-md">
        <div className="card-body p-8">
          <h1 className="text-3xl font-bold mb-8 text-center text-gradient">Trading Bot</h1>

          <form onSubmit={handleLogin} className="space-y-4">
            {error && (
              <div className="alert alert-danger">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input w-full"
                placeholder="admin"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input w-full"
                placeholder="password"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full disabled:opacity-50"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>

          <p className="mt-8 text-center text-slate-400 text-sm">
            Demo Credentials: admin / admin
          </p>
        </div>
      </div>
    </div>
  )
}
