import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Eye, EyeOff, Loader, Lock, User, Download, Copy, Check, Mail, KeyRound } from 'lucide-react'

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code2fa, setCode2fa] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // For first-time 2FA setup
  const [showQRSetup, setShowQRSetup] = useState(false)
  const [qrCode, setQrCode] = useState('')
  const [secret, setSecret] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
  const [tempUsername, setTempUsername] = useState('')

  // Forgot password flow
  const [showForgot, setShowForgot] = useState(false)
  const [resetEmail, setResetEmail] = useState('')
  const [resetOtp, setResetOtp] = useState('')
  const [resetPassword, setResetPassword] = useState('')
  const [resetStep, setResetStep] = useState<'request' | 'verify'>('request')
  const [devResetOtp, setDevResetOtp] = useState('')

  const { setToken, setUser } = useAuthStore()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      window.location.href = '/'
      return
    }

    const prefill = localStorage.getItem('setupPrefillUsername')
    if (prefill) {
      setUsername(prefill)
      localStorage.removeItem('setupPrefillUsername')
    }
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const api = createApiClient(getApiBaseUrl())

      const response = await api.axiosInstance.post('auth/login', {
        username: username.trim(),
        password: password.trim(),
      })

      if (response.data.requires_2fa_setup === true) {
        setTempUsername(username.trim())
        await initializeTotp(username.trim(), password.trim())
      } else if (response.data.totp_enabled === true && !code2fa) {
        setTempUsername(username.trim())
        setError('Nhập mã 6 số từ Google Authenticator để hoàn tất đăng nhập')
      } else if (response.data.totp_enabled === true && code2fa) {
        await verify2FA(username.trim())
      } else {
        setError('Unexpected authentication state. Please try again.')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Đăng nhập thất bại')
    } finally {
      setLoading(false)
    }
  }

  const initializeTotp = async (user: string, pass: string) => {
    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/setup-totp', {
        username: user,
        password: pass,
      })
      setSecret(response.data.secret)
      setQrCode(response.data.qr_code)
      setShowQRSetup(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi setup 2FA')
    }
  }

  const handleVerifyQRCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/verify-totp-setup', {
        username: tempUsername,
        secret: secret,
        code: verificationCode.trim(),
      })
      setBackupCodes(response.data.backup_codes)
      await verify2FA(tempUsername, verificationCode.trim())
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Mã xác thực sai')
      setLoading(false)
    }
  }

  const verify2FA = async (user: string, code?: string) => {
    const codeToUse = code || code2fa.trim()
    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/verify-2fa', {
        username: user,
        code: codeToUse,
      })

      if (response.data.access_token) {
        setToken(response.data.access_token)
        setUser({
          id: response.data.user.id,
          username: response.data.user.username,
          email: response.data.user.email,
          role: response.data.user.role,
        })
        window.location.href = '/'
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Mã 2FA sai. Thử lại')
      setLoading(false)
    }
  }

  const handleRequestResetOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    setDevResetOtp('')
    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/request-password-reset-otp', {
        email: resetEmail.trim(),
      })
      setResetStep('verify')
      if (response.data?.dev_otp) {
        setDevResetOtp(response.data.dev_otp)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Không thể gửi OTP reset')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const api = createApiClient(getApiBaseUrl())
      const response = await api.axiosInstance.post('auth/confirm-password-reset-otp', {
        email: resetEmail.trim(),
        otp: resetOtp.trim(),
        new_password: resetPassword,
      })
      if (response.data?.username) {
        setUsername(response.data.username)
      }
      setShowForgot(false)
      setResetStep('request')
      setResetOtp('')
      setResetPassword('')
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Không thể reset mật khẩu')
    } finally {
      setLoading(false)
    }
  }

  const copyBackupCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const downloadBackupCodes = () => {
    const content = `Backup Codes for TiznDBot\n================================\n\n${backupCodes
      .map((code, idx) => `${idx + 1}. ${code}`)
      .join('\n')}`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'tizndbot-backup-codes.txt'
    link.click()
    window.URL.revokeObjectURL(url)
  }

  if (showQRSetup && backupCodes.length === 0) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 font-sans">
        <div className="w-full max-w-md">
          <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
            <div className="bg-gradient-to-r from-blue-700 to-blue-500 px-8 py-10">
              <h1 className="text-2xl font-black text-white text-center">Enable Google Authenticator</h1>
              <p className="text-blue-100 text-sm text-center mt-2">Quét QR để kích hoạt 2FA bắt buộc</p>
            </div>

            <div className="p-8">
              {error && <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4"><p className="text-red-300 text-sm">{error}</p></div>}

              <div className="flex justify-center mb-8">
                <div className="bg-white p-4 rounded-xl border border-white/10">
                  {qrCode && <img src={qrCode} alt="QR Code" className="w-56 h-56" />}
                </div>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6 text-center backdrop-blur-sm">
                <p className="text-xs text-slate-300 mb-2">Manual key:</p>
                <p className="text-sm font-mono text-blue-400 break-all font-bold">{secret}</p>
              </div>

              <form onSubmit={handleVerifyQRCode} className="space-y-4">
                <div>
                  <label className="block text-sm font-bold text-slate-200 mb-2">Nhập mã 6 số từ app</label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    className="w-full text-center text-3xl font-bold tracking-widest border border-white/20 bg-slate-900/50 text-white rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                    disabled={loading}
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || verificationCode.length !== 6}
                  className="w-full bg-gradient-to-r from-blue-600 to-blue-500 text-white font-bold py-3 rounded-lg transition flex items-center justify-center gap-2 shadow-lg shadow-blue-500/30"
                >
                  {loading ? <><Loader className="animate-spin" size={20} />Đang xác thực...</> : 'Xác thực'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (backupCodes.length > 0) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 font-sans">
        <div className="w-full max-w-md">
          <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
            <div className="bg-gradient-to-r from-amber-600 to-amber-500 px-8 py-10">
              <h1 className="text-2xl font-black text-white text-center">Backup Codes</h1>
              <p className="text-amber-100 text-sm text-center mt-2">Lưu ở nơi an toàn</p>
            </div>

            <div className="p-8">
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-6">
                <p className="text-sm text-amber-100">⚠️ Mỗi mã dùng một lần khi mất Google Authenticator.</p>
              </div>

              <div className="bg-slate-900/30 border border-white/10 rounded-lg p-4 max-h-64 overflow-y-auto mb-6 space-y-2">
                {backupCodes.map((code, idx) => (
                  <div key={idx} onClick={() => copyBackupCode(code)} className="flex items-center gap-3 p-3 bg-slate-800/40 border border-white/10 rounded hover:border-blue-500/30 cursor-pointer transition">
                    <span className="text-xs font-bold text-slate-400 min-w-6">{idx + 1}.</span>
                    <code className="text-sm font-mono text-blue-400 flex-1">{code}</code>
                    {copiedCode === code ? <Check size={16} className="text-green-400" /> : <Copy size={16} className="text-slate-500" />}
                  </div>
                ))}
              </div>

              <button onClick={downloadBackupCodes} className="w-full bg-gradient-to-r from-amber-600 to-amber-500 text-white font-bold py-3 rounded-lg mb-4 flex items-center justify-center gap-2 transition">
                <Download size={18} />Tải về (.txt)
              </button>

              <button onClick={() => (window.location.href = '/')} className="w-full bg-gradient-to-r from-blue-600 to-blue-500 text-white font-bold py-3 rounded-lg transition">
                ✅ Vào Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md">
        <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
          <div className="bg-gradient-to-r from-blue-700 to-blue-500 px-8 py-10">
            <h1 className="text-3xl font-black text-white text-center">TiznDBot</h1>
            <p className="text-blue-100 text-xs text-center mt-2 tracking-[0.15em] font-bold uppercase">Secure Access Gateway</p>
          </div>

          <div className="p-8">
            {error && (
              <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            {!showForgot ? (
              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Username</label>
                  <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                    <User size={18} className="text-blue-400 mr-3" />
                    <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none" disabled={loading} />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Password</label>
                  <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                    <Lock size={18} className="text-blue-400 mr-3" />
                    <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none" disabled={loading} />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-slate-500 hover:text-slate-300 transition" disabled={loading}>
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Google Authenticator Code</label>
                  <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                    <KeyRound size={18} className="text-blue-400 mr-3" />
                    <input type="text" value={code2fa} onChange={(e) => setCode2fa(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" maxLength={6} className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none text-center text-lg font-mono tracking-widest" disabled={loading} />
                  </div>
                </div>

                <button type="submit" disabled={loading || !username || !password} className="w-full bg-gradient-to-r from-blue-600 to-blue-500 text-white font-black py-3 rounded-lg transition flex items-center justify-center gap-2 mt-8 shadow-lg shadow-blue-500/30 uppercase tracking-wider text-sm">
                  {loading ? <><Loader className="animate-spin" size={18} />Processing...</> : 'Login Securely'}
                </button>

                <button type="button" onClick={() => setShowForgot(true)} className="w-full text-sm text-blue-300 hover:text-blue-200 transition mt-1">
                  Quên mật khẩu? Khôi phục qua email
                </button>
              </form>
            ) : (
              <div className="space-y-4">
                <h3 className="text-white font-bold">Khôi phục mật khẩu qua email</h3>
                {resetStep === 'request' ? (
                  <form onSubmit={handleRequestResetOtp} className="space-y-4">
                    <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                      <Mail size={18} className="text-blue-400 mr-3" />
                      <input type="email" value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} placeholder="your@email.com" className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none" disabled={loading} />
                    </div>
                    <button type="submit" disabled={loading || !resetEmail} className="w-full bg-gradient-to-r from-indigo-600 to-blue-500 text-white font-bold py-3 rounded-lg transition">
                      {loading ? 'Đang gửi OTP...' : 'Gửi OTP khôi phục'}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleConfirmReset} className="space-y-4">
                    {devResetOtp && <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200">DEV OTP: <span className="font-bold">{devResetOtp}</span></div>}
                    <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                      <KeyRound size={18} className="text-blue-400 mr-3" />
                      <input type="text" value={resetOtp} onChange={(e) => setResetOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="OTP 6 digits" className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none" disabled={loading} maxLength={6} />
                    </div>
                    <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                      <Lock size={18} className="text-blue-400 mr-3" />
                      <input type="password" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} placeholder="New password (min 8)" className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none" disabled={loading} />
                    </div>
                    <button type="submit" disabled={loading || resetOtp.length !== 6 || resetPassword.length < 8} className="w-full bg-gradient-to-r from-indigo-600 to-blue-500 text-white font-bold py-3 rounded-lg transition">
                      {loading ? 'Đang đổi mật khẩu...' : 'Xác nhận đổi mật khẩu'}
                    </button>
                  </form>
                )}

                <button
                  type="button"
                  onClick={() => {
                    setShowForgot(false)
                    setResetStep('request')
                    setDevResetOtp('')
                    setError('')
                  }}
                  className="w-full text-sm text-slate-400 hover:text-slate-200 transition"
                >
                  ← Quay lại đăng nhập
                </button>
              </div>
            )}

            <div className="text-center mt-6">
              <p className="text-xs text-slate-500 uppercase tracking-widest">TiznDBot • Multi-Factor Protected</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
