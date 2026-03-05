import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Lock, Mail, User, Check, AlertCircle, Loader, Shield, ArrowRight } from 'lucide-react'

export const SetupPage: React.FC = () => {
  const navigate = useNavigate()
  const [step, setStep] = useState<'form' | 'otp' | 'done'>('form')

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [devOtp, setDevOtp] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    const checkSetup = async () => {
      try {
        const api = createApiClient(getApiBaseUrl())
        const response = await api.axiosInstance.get('auth/setup-status')
        if (response.data.setup_complete) {
          navigate('/login')
        }
      } catch {
        // ignore
      }
    }
    checkSetup()
  }, [navigate])

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setDevOtp('')

    if (!username.trim()) return setError('Username is required')
    if (username.trim().length < 3) return setError('Username must be at least 3 characters')
    if (!email.trim() || !email.includes('@')) return setError('Valid email is required')
    if (!password.trim()) return setError('Password is required')
    if (password.length < 8) return setError('Password must be at least 8 characters')
    if (password !== confirmPassword) return setError('Passwords do not match')

    setLoading(true)
    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/setup/send-email-otp', {
        username: username.trim(),
        password,
        email: email.trim(),
      })

      setStep('otp')
      setSuccess(`OTP has been sent to ${email.trim()}`)
      if (response.data?.dev_otp) {
        setDevOtp(response.data.dev_otp)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send OTP')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (otp.trim().length !== 6) return setError('OTP must be 6 digits')

    setLoading(true)
    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/setup/verify-email-otp', {
        email: email.trim(),
        otp: otp.trim(),
      })

      if (response.data?.success) {
        setStep('done')
        setSuccess('Email verified successfully!')
        localStorage.setItem('setupPrefillUsername', username.trim())
        
        // Redirect after 2 seconds using window.location for guaranteed redirect
        setTimeout(() => {
          window.location.href = '/login'
        }, 2000)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'OTP verification failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Decorations */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px] opacity-20"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px] opacity-20"></div>
      </div>

      <div className="w-full max-w-md">
        {/* Premium Card */}
        <div className="bg-gradient-to-b from-slate-900/60 to-slate-900/40 border border-blue-500/20 rounded-3xl backdrop-blur-xl overflow-hidden shadow-2xl">
          
          {/* Header Section */}
          <div className="bg-gradient-to-r from-blue-700 via-blue-600 to-blue-500 px-8 py-12">
            <div className="flex items-center justify-center mb-4">
              <div className="p-3 bg-white/20 rounded-2xl backdrop-blur">
                <Shield size={32} className="text-white" />
              </div>
            </div>
            <h1 className="text-4xl font-black text-white text-center">TiznDBot</h1>
            <p className="text-blue-100 text-xs text-center mt-3 tracking-widest font-bold uppercase">
              Secure Admin Setup
            </p>
          </div>

          {/* Content Section */}
          <div className="p-8 space-y-6">
            
            {/* Error Alert */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3 animate-fadeIn">
                <AlertCircle size={20} className="text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-red-300 text-sm font-medium">{error}</p>
              </div>
            )}

            {/* Success Alert */}
            {success && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3 animate-fadeIn">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <p className="text-emerald-300 text-sm font-medium">{success}</p>
              </div>
            )}

            {/* Form Step */}
            {step === 'form' && (
              <form onSubmit={handleSendOtp} className="space-y-5">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2.5 uppercase tracking-wider">Admin Username</label>
                  <div className="relative">
                    <User size={18} className="absolute left-4 top-3.5 text-blue-400" />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="admin"
                      className="w-full pl-12 pr-4 py-3 bg-slate-800/40 border border-slate-600/40 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2.5 uppercase tracking-wider">Email Address</label>
                  <div className="relative">
                    <Mail size={18} className="absolute left-4 top-3.5 text-blue-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="admin@example.com"
                      className="w-full pl-12 pr-4 py-3 bg-slate-800/40 border border-slate-600/40 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2.5 uppercase tracking-wider">Password</label>
                  <div className="relative">
                    <Lock size={18} className="absolute left-4 top-3.5 text-blue-400" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min 8 characters"
                      className="w-full pl-12 pr-4 py-3 bg-slate-800/40 border border-slate-600/40 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2.5 uppercase tracking-wider">Confirm Password</label>
                  <div className="relative">
                    <Lock size={18} className="absolute left-4 top-3.5 text-blue-400" />
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm password"
                      className="w-full pl-12 pr-4 py-3 bg-slate-800/40 border border-slate-600/40 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-black py-3.5 rounded-xl transition-all duration-300 uppercase tracking-wider text-sm disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl hover:shadow-blue-500/30 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader size={18} className="animate-spin" />
                      Sending OTP...
                    </>
                  ) : (
                    <>
                      Send Email OTP
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </form>
            )}

            {/* OTP Step */}
            {step === 'otp' && (
              <form onSubmit={handleVerifyOtp} className="space-y-6">
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-200">
                  <p className="font-semibold mb-1">Enter verification code</p>
                  <p>A 6-digit code has been sent to <span className="font-bold text-blue-100">{email}</span></p>
                </div>

                {devOtp && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200">
                    <p className="font-semibold mb-2">DEV MODE - OTP Code:</p>
                    <div className="font-mono text-lg font-bold tracking-[0.5em] text-amber-100 text-center bg-amber-900/20 py-3 rounded-lg">
                      {devOtp}
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2.5 uppercase tracking-wider">Verification Code</label>
                  <input
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    className="w-full text-center bg-slate-800/40 text-white text-3xl tracking-[0.3em] px-4 py-4 rounded-xl border border-slate-600/40 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 font-mono font-bold"
                    disabled={loading}
                    maxLength={6}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || otp.length !== 6}
                  className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-black py-3.5 rounded-xl transition-all duration-300 uppercase tracking-wider text-sm disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl hover:shadow-blue-500/30 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader size={18} className="animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      Verify & Continue
                      <Check size={18} />
                    </>
                  )}
                </button>
              </form>
            )}

            {/* Done Step */}
            {step === 'done' && (
              <div className="text-center space-y-4">
                <div className="flex justify-center mb-4">
                  <div className="p-4 bg-emerald-500/20 rounded-full">
                    <Check size={40} className="text-emerald-400" />
                  </div>
                </div>
                <div className="p-5 rounded-xl border border-emerald-500/30 bg-emerald-500/10">
                  <p className="text-emerald-200 font-bold text-lg mb-2">Setup Complete</p>
                  <p className="text-emerald-300 text-sm">Redirecting to login for Google Authenticator setup...</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Info */}
        <div className="text-center mt-6 text-slate-500 text-xs">
          <p>Trading Intelligence System • Version 4.2.0</p>
        </div>
      </div>
    </div>
  )
}
