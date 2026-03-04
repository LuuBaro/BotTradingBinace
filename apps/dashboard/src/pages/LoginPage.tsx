import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../store'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Eye, EyeOff, Loader, Lock, User, Download, Copy, Check } from 'lucide-react'

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

  const { setToken, setUser } = useAuthStore()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      window.location.href = '/'
    }
  }, [])

  // Handle login
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

      if (response.data.totp_enabled === false) {
        // First time - need to setup 2FA
        setTempUsername(username.trim())
        await initializeTotp(username.trim(), password.trim())
      } else if (response.data.totp_enabled === true && !code2fa) {
        // Already has 2FA - need code
        setTempUsername(username.trim())
        setError('Hãy nhập mã 6 chữ số từ Google Authenticator')
      } else if (code2fa) {
        // Has 2FA code - verify it
        await verify2FA(username.trim())
      }
    } catch (err: any) {
      console.error('Login error:', err)
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
      // Auto login
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

  const copyBackupCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const downloadBackupCodes = () => {
    const content = `Backup Codes for Trading Bot\n================================\n\n${backupCodes
      .map((code, idx) => `${idx + 1}. ${code}`)
      .join('\n')}`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'backup-codes.txt'
    link.click()
    window.URL.revokeObjectURL(url)
  }

  // QR Setup UI
  if (showQRSetup && backupCodes.length === 0) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 font-sans">
        <div className="w-full max-w-md">
          <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-400 px-8 py-10">
              <h1 className="text-2xl font-black text-white text-center">2FA Setup</h1>
              <p className="text-blue-100 text-sm text-center mt-2">
                Quét mã QR với Google Authenticator
              </p>
            </div>

            {/* Content */}
            <div className="p-8">
              {error && (
                <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <p className="text-red-300 text-sm">{error}</p>
                </div>
              )}

              {/* QR Code */}
              <div className="flex justify-center mb-8">
                <div className="bg-white p-4 rounded-xl border border-white/10">
                  {qrCode && <img src={qrCode} alt="QR Code" className="w-56 h-56" />}
                </div>
              </div>

              {/* Manual Entry */}
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6 text-center backdrop-blur-sm">
                <p className="text-xs text-slate-300 mb-2">Nhập thủ công nếu không quét được:</p>
                <p className="text-sm font-mono text-blue-400 break-all font-bold">{secret}</p>
              </div>

              {/* Verify Form */}
              <form onSubmit={handleVerifyQRCode} className="space-y-4">
                <div>
                  <label className="block text-sm font-bold text-slate-200 mb-2">
                    Nhập mã 6 chữ số từ ứng dụng
                  </label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) =>
                      setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                    }
                    placeholder="000000"
                    maxLength={6}
                    className="w-full text-center text-3xl font-bold tracking-widest border border-white/20 bg-slate-900/50 text-white rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 focus:bg-slate-800 transition backdrop-blur-sm"
                    disabled={loading}
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || verificationCode.length !== 6}
                  className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 disabled:from-gray-700 disabled:to-gray-600 text-white font-bold py-3 rounded-lg transition flex items-center justify-center gap-2 shadow-lg shadow-blue-500/30"
                >
                  {loading ? (
                    <>
                      <Loader className="animate-spin" size={20} />
                      Đang xác thực...
                    </>
                  ) : (
                    'Xác thực'
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Backup Codes Display
  if (backupCodes.length > 0) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 font-sans">
        <div className="w-full max-w-md">
          <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
            <div className="bg-gradient-to-r from-amber-600 to-amber-500 px-8 py-10">
              <h1 className="text-2xl font-black text-white text-center">Lưu Mã Dự Phòng</h1>
              <p className="text-amber-100 text-sm text-center mt-2">
                Lưu 10 mã này ở nơi an toàn
              </p>
            </div>

            <div className="p-8">
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-6 backdrop-blur-sm">
                <p className="text-sm text-amber-100">
                  ⚠️ Mỗi mã dùng một lần. Nếu mất điện thoại, bạn có thể dùng các mã này để đăng nhập.
                </p>
              </div>

              <div className="bg-slate-900/30 border border-white/10 rounded-lg p-4 max-h-64 overflow-y-auto mb-6 space-y-2 backdrop-blur-sm">
                {backupCodes.map((code, idx) => (
                  <div
                    key={idx}
                    onClick={() => copyBackupCode(code)}
                    className="flex items-center gap-3 p-3 bg-slate-800/40 border border-white/10 rounded hover:border-blue-500/30 hover:bg-slate-800/60 cursor-pointer transition"
                  >
                    <span className="text-xs font-bold text-slate-400 min-w-6">{idx + 1}.</span>
                    <code className="text-sm font-mono text-blue-400 flex-1">{code}</code>
                    {copiedCode === code ? (
                      <Check size={16} className="text-green-400" />
                    ) : (
                      <Copy size={16} className="text-slate-500 hover:text-slate-300" />
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={downloadBackupCodes}
                className="w-full bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-700 hover:to-amber-600 text-white font-bold py-3 rounded-lg mb-4 flex items-center justify-center gap-2 transition shadow-lg shadow-amber-500/30"
              >
                <Download size={18} />
                Tải về (.txt)
              </button>

              <button
                onClick={() => window.location.href = '/'}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-bold py-3 rounded-lg transition shadow-lg shadow-blue-500/30"
              >
                ✅ Xong - Vào Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Main Login UI
  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md">
        <div className="bg-slate-800/40 border border-white/10 rounded-2xl backdrop-blur-xl overflow-hidden shadow-2xl">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-400 px-8 py-10">
            <h1 className="text-3xl font-black text-white text-center">TiznDBot</h1>
            <p className="text-blue-100 text-xs text-center mt-2 tracking-[0.15em] font-bold">Trading Intelligence Platform</p>
          </div>

          {/* Content */}
          <div className="p-8">
            {error && (
              <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4 backdrop-blur-sm">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              {/* Username */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Username</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                  <User size={18} className="text-blue-400 mr-3" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Password</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                  <Lock size={18} className="text-blue-400 mr-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none"
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-slate-500 hover:text-slate-300 transition"
                    disabled={loading}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* 2FA Code (optional) */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">2FA Code (Optional)</label>
                <div className="flex items-center border-b border-white/20 py-3 focus-within:border-blue-500 transition">
                  <Lock size={18} className="text-blue-400 mr-3" />
                  <input
                    type="text"
                    value={code2fa}
                    onChange={(e) => setCode2fa(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none text-center text-lg font-mono tracking-widest"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Login Button */}
              <button
                type="submit"
                disabled={loading || !username || !password}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 disabled:from-gray-700 disabled:to-gray-600 text-white font-black py-3 rounded-lg transition flex items-center justify-center gap-2 mt-8 shadow-lg shadow-blue-500/30 uppercase tracking-wider text-sm"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin" size={18} />
                    Processing...
                  </>
                ) : (
                  'Login'
                )}
              </button>
            </form>

            {/* Footer Info */}
            <div className="text-center mt-6">
              <p className="text-xs text-slate-500 uppercase tracking-widest">Trading Intelligence Platform</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

