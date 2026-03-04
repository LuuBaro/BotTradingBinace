import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../store'
import { useNavigate } from 'react-router-dom'
import { createApiClient, getApiBaseUrl } from '../api/client'
import { Copy, Check, ShieldAlert, Loader } from 'lucide-react'

export const SetupTOTPPage: React.FC = () => {
  const [step, setStep] = useState<'intro' | 'qr-code' | 'verify' | 'backup-codes'>('intro')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [secret, setSecret] = useState('')
  const [qrCode, setQrCode] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const navigate = useNavigate()

  useEffect(() => {
    // Initialize from localStorage if coming from login
    const savedUsername = localStorage.getItem('setupTotpUsername')
    if (savedUsername) {
      setUsername(savedUsername)
      // Auto-skip intro and go directly to password verification
      // (User is already authenticated, so we still need to verify password)
    } else {
      // If not coming from login, redirect back to login
      navigate('/login')
    }
  }, [])

  // Bước 1: Khởi động setup
  const handleStartSetup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const api = createApiClient(getApiBaseUrl())
      
      const response = await api.axiosInstance.post('auth/setup-totp', {
        username: username.trim(),
        password: password.trim(),
      })

      setSecret(response.data.secret)
      setQrCode(response.data.qr_code)
      setStep('qr-code')
      
      console.log('✅ Setup initiated. QR code generated.')
    } catch (err: any) {
      console.error('Setup error:', err)
      setError(err.response?.data?.detail || 'Failed to setup TOTP. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  // Bước 2: Xác thực QR code (nhập mã từ app)
  const handleVerifyQRCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const api = createApiClient(getApiBaseUrl())
      
      const response = await api.axiosInstance.post('auth/verify-totp-setup', {
        username: username.trim(),
        secret: secret,
        code: verificationCode.trim(),
      })

      setBackupCodes(response.data.backup_codes)
      setStep('backup-codes')
      
      console.log('✅ 2FA setup verified. Backup codes generated.')
    } catch (err: any) {
      console.error('Verification error:', err)
      setError(err.response?.data?.detail || 'Invalid verification code. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Copy backup code to clipboard
  const copyBackupCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  // Finish setup
  const handleFinishSetup = () => {
    localStorage.removeItem('setupTotpUsername')
    window.location.href = '/'
  }

  // Render: Intro step
  if (step === 'intro') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-gradient-to-b from-slate-800 to-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-green-600 to-green-500 px-8 py-12">
              <h1 className="text-3xl font-black text-white mb-2">Setup 2FA</h1>
              <p className="text-green-100 text-sm font-medium">Bảo vệ tài khoản bằng Google Authenticator</p>
            </div>

            {/* Content */}
            <div className="p-8">
              {error && (
                <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                  <p className="text-red-400 text-sm font-medium">{error}</p>
                </div>
              )}

              <form onSubmit={handleStartSetup} className="space-y-4">
                {/* Username */}
                <div>
                  <label htmlFor="username" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Tên đăng nhập
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    className="w-full bg-slate-700/30 border border-slate-600/50 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-green-500/50 transition"
                    disabled={loading}
                  />
                </div>

                {/* Password */}
                <div>
                  <label htmlFor="password" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Mật khẩu (xác nhận)
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••"
                      className="w-full bg-slate-700/30 border border-slate-600/50 rounded-lg px-4 py-2.5 pr-10 text-white placeholder-slate-500 focus:outline-none focus:border-green-500/50 transition"
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-300"
                      disabled={loading}
                    >
                      {showPassword ? '🙈' : '👁'}
                    </button>
                  </div>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading || !username || !password}
                  className="w-full bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 disabled:from-slate-700 disabled:to-slate-600 text-white font-bold py-3 rounded-lg transition flex items-center justify-center gap-2 mt-6"
                >
                  {loading ? (
                    <>
                      <Loader className="animate-spin" size={20} />
                      Đang khởi động...
                    </>
                  ) : (
                    'Tiếp tục'
                  )}
                </button>
              </form>

              {/* Info */}
              <div className="mt-6 bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                <p className="text-xs text-blue-200 leading-relaxed">
                  📱 Chuẩn bị ứng dụng Google Authenticator sẵn sàng để quét mã QR trong bước tiếp theo.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Render: QR Code step
  if (step === 'qr-code') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-gradient-to-b from-slate-800 to-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-purple-500 px-8 py-12">
              <h1 className="text-3xl font-black text-white mb-2">Quét mã QR</h1>
              <p className="text-purple-100 text-sm font-medium">Sử dụng Google Authenticator để quét</p>
            </div>

            {/* Content */}
            <div className="p-8">
              {/* QR Code */}
              <div className="flex justify-center mb-6">
                <div className="bg-white rounded-lg p-4">
                  {qrCode && <img src={qrCode} alt="QR Code" className="w-64 h-64" />}
                </div>
              </div>

              {/* Manual entry option */}
              <div className="bg-slate-700/30 border border-slate-600/50 rounded-xl p-4 mb-6">
                <p className="text-xs text-slate-300 font-bold uppercase tracking-wider mb-2">
                  🔑 Không thể quét QR?
                </p>
                <p className="text-xs text-slate-400 mb-2">Nhập manually vào ứng dụng:</p>
                <p className="text-sm font-mono text-blue-400 break-all bg-slate-900/50 p-2 rounded border border-slate-600/50">
                  {secret}
                </p>
              </div>

              {/* Verification Form */}
              <form onSubmit={handleVerifyQRCode} className="space-y-4">
                <div>
                  <label htmlFor="verCode" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Nhập mã 6 chữ số từ ứng dụng
                  </label>
                  <input
                    id="verCode"
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    className="w-full text-center text-2xl font-bold tracking-widest bg-slate-700/30 border border-slate-600/50 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50 transition"
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || verificationCode.length !== 6}
                  className="w-full bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-700 hover:to-purple-600 disabled:from-slate-700 disabled:to-slate-600 text-white font-bold py-3 rounded-lg transition flex items-center justify-center gap-2"
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

              {error && (
                <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                  <p className="text-red-400 text-xs">{error}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Render: Backup Codes step
  if (step === 'backup-codes') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-gradient-to-b from-slate-800 to-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-amber-600 to-amber-500 px-8 py-12">
              <h1 className="text-3xl font-black text-white mb-2">Lưu mã khôi phục</h1>
              <p className="text-amber-100 text-sm font-medium">10 mã dự phòng khi mất điện thoại</p>
            </div>

            {/* Content */}
            <div className="p-8">
              {/* Warning */}
              <div className="mb-6 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                <div className="flex gap-2">
                  <ShieldAlert className="text-amber-400 flex-shrink-0 mt-0.5" size={16} />
                  <div>
                    <p className="text-xs font-bold text-amber-300 uppercase tracking-wider mb-1">
                      ⚠️ LƯU QUAN TRỌNG
                    </p>
                    <p className="text-xs text-amber-200 leading-relaxed">
                      Lưu lại 10 mã này ở nơi an toàn. Mỗi mã dùng 1 lần. Nếu mất điện thoại, bạn có thể dùng các mã này để đăng nhập.
                    </p>
                  </div>
                </div>
              </div>

              {/* Backup Codes List */}
              <div className="bg-slate-900/50 border border-slate-600/50 rounded-xl p-4 mb-6 max-h-80 overflow-y-auto">
                <div className="space-y-2">
                  {backupCodes.map((code, idx) => (
                    <div 
                      key={idx}
                      onClick={() => copyBackupCode(code)}
                      className="flex items-center gap-2 p-3 bg-slate-700/30 hover:bg-slate-700/50 rounded border border-slate-600/30 cursor-pointer transition group"
                    >
                      <span className="text-xs font-bold text-slate-400 min-w-5">{idx + 1}.</span>
                      <code className="text-sm font-mono text-blue-400 flex-1 group-hover:text-blue-300 transition">
                        {code}
                      </code>
                      {copiedCode === code ? (
                        <Check size={16} className="text-green-400" />
                      ) : (
                        <Copy size={16} className="text-slate-500 group-hover:text-slate-400 transition" />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Finish Button */}
              <button
                onClick={handleFinishSetup}
                className="w-full bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 text-white font-bold py-3 rounded-lg transition"
              >
                ✅ Xong! Vào Dashboard
              </button>

              {/* Info */}
              <div className="mt-6 bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                <p className="text-xs text-blue-200">
                  💾 Bạn có thể in hoặc chụp ảnh những mã này. Lần sau đăng nhập sẽ cần mã 6 chữ số từ app hoặc mã khôi phục này.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return null
}
