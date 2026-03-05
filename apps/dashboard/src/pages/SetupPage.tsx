import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Lock, Mail, User, Check, AlertCircle, Loader } from 'lucide-react'

export const SetupPage: React.FC = () => {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [passwordStrength, setPasswordStrength] = useState<'weak' | 'fair' | 'good' | 'strong'>('weak')

  useEffect(() => {
    // Check if setup is already complete
    const checkSetup = async () => {
      try {
        const api = createApiClient(getApiBaseUrl())
        const response = await api.axiosInstance.get('auth/setup-status')
        if (response.data.setup_complete) {
          navigate('/login')
        }
      } catch (err) {
        console.error('Failed to check setup status')
      }
    }
    checkSetup()
  }, [navigate])

  const calculatePasswordStrength = (pwd: string) => {
    if (pwd.length < 8) return 'weak'
    if (pwd.length < 12) return 'fair'
    if (pwd.match(/[a-z]/) && pwd.match(/[A-Z]/) && pwd.match(/[0-9]/) && pwd.match(/[^a-zA-Z0-9]/)) {
      return 'strong'
    }
    if (pwd.match(/[a-z]/) && pwd.match(/[A-Z]/) && pwd.match(/[0-9]/)) {
      return 'good'
    }
    return 'fair'
  }

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const pwd = e.target.value
    setPassword(pwd)
    setPasswordStrength(calculatePasswordStrength(pwd))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    // Validation
    if (!username.trim()) {
      setError('Username is required')
      setLoading(false)
      return
    }

    if (username.length < 3) {
      setError('Username must be at least 3 characters')
      setLoading(false)
      return
    }

    if (!email.trim()) {
      setError('Email is required')
      setLoading(false)
      return
    }

    if (!email.includes('@')) {
      setError('Invalid email format')
      setLoading(false)
      return
    }

    if (!password.trim()) {
      setError('Password is required')
      setLoading(false)
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      setLoading(false)
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/setup', {
        username: username.trim(),
        password: password,
        email: email.trim(),
      })

      if (response.data.success) {
        setSuccess(true)
        setTimeout(() => {
          navigate('/login')
        }, 2000)
      } else {
        setError(response.data.detail || 'Setup failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Setup failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const strengthColor = {
    weak: 'bg-red-500',
    fair: 'bg-yellow-500',
    good: 'bg-blue-500',
    strong: 'bg-green-500',
  }

  const strengthText = {
    weak: 'Weak',
    fair: 'Fair',
    good: 'Good',
    strong: 'Strong',
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#020617] via-blue-950/20 to-[#020617] flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md">
        <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
          {/* Header */}
          <div className="bg-gradient-to-r from-green-600 to-emerald-400 px-8 py-12">
            <h1 className="text-3xl font-black text-white text-center">Initial Setup</h1>
            <p className="text-emerald-100 text-sm text-center mt-2 tracking-[0.15em] font-bold">Create your admin account</p>
          </div>

          {/* Content */}
          <div className="p-8">
            {error && (
              <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4 backdrop-blur-sm flex items-start gap-3">
                <AlertCircle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            {success && (
              <div className="mb-6 bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 backdrop-blur-sm flex items-start gap-3">
                <Check size={18} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-emerald-300 text-sm font-semibold">Setup complete!</p>
                  <p className="text-emerald-300/70 text-xs mt-1">Redirecting to login...</p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" disabled={loading || success}>
              {/* Username */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Admin Username</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-green-500 transition">
                  <User size={18} className="text-green-400 mr-3" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none"
                    disabled={loading || success}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">Min 3 characters, alphanumeric</p>
              </div>

              {/* Email */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Email</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-green-500 transition">
                  <Mail size={18} className="text-green-400 mr-3" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@example.com"
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none"
                    disabled={loading || success}
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Password</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-green-500 transition">
                  <Lock size={18} className="text-green-400 mr-3" />
                  <input
                    type="password"
                    value={password}
                    onChange={handlePasswordChange}
                    placeholder="Min 8 characters"
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none"
                    disabled={loading || success}
                  />
                </div>
                {password && (
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400">Password strength:</span>
                      <span className={`text-xs font-bold ${
                        passwordStrength === 'weak' ? 'text-red-400' :
                        passwordStrength === 'fair' ? 'text-yellow-400' :
                        passwordStrength === 'good' ? 'text-blue-400' :
                        'text-green-400'
                      }`}>
                        {strengthText[passwordStrength]}
                      </span>
                    </div>
                    <div className="w-full bg-slate-700/50 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full ${strengthColor[passwordStrength]} transition-all`}
                        style={{
                          width: passwordStrength === 'weak' ? '25%' : 
                                 passwordStrength === 'fair' ? '50%' :
                                 passwordStrength === 'good' ? '75%' : '100%'
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Confirm Password</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-green-500 transition">
                  <Lock size={18} className="text-green-400 mr-3" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm password"
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none"
                    disabled={loading || success}
                  />
                </div>
              </div>

              {/* Security Notice */}
              <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
                <p className="font-semibold mb-1">🔒 Security Reminder</p>
                <ul className="list-disc list-inside space-y-0.5 opacity-80">
                  <li>Use a strong password with mix of upper, lower, numbers</li>
                  <li>Don't share this password</li>
                  <li>This is your only admin account for now</li>
                </ul>
              </div>

              <button
                type="submit"
                disabled={loading || success || !username || !password || !confirmPassword || !email}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-500 text-white font-black py-3 rounded-xl transition-all duration-200 uppercase tracking-wider text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-green-500/30 active:scale-95"
              >
                {loading ? (
                  <div className="flex items-center justify-center gap-2">
                    <Loader size={18} className="animate-spin" />
                    Creating admin...
                  </div>
                ) : success ? (
                  <div className="flex items-center justify-center gap-2">
                    <Check size={18} />
                    Setup complete!
                  </div>
                ) : (
                  'Create Admin Account'
                )}
              </button>

              <p className="text-center text-xs text-slate-500 mt-4">
                This setup can only be run once. After completion, you can access the system with your credentials.
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
