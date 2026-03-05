import React from 'react'

/**
 * Premium Button Component
 */
export const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline'
    size?: 'sm' | 'md' | 'lg'
    icon?: React.ReactNode
    loading?: boolean
  }
>(({ variant = 'primary', size = 'md', icon, loading, className, children, ...props }, ref) => {
  const baseClasses = 'font-bold transition-all duration-300 flex items-center justify-center gap-2 relative overflow-hidden active:scale-95'

  const variantClasses = {
    primary: 'bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:shadow-lg hover:shadow-blue-500/50 hover:from-blue-500 hover:to-blue-400',
    secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 border border-slate-700 hover:border-slate-500 hover:shadow-lg',
    danger: 'bg-gradient-to-r from-rose-600 to-red-500 text-white hover:shadow-lg hover:shadow-rose-500/50 hover:from-rose-500 hover:to-red-400',
    success: 'bg-gradient-to-r from-emerald-600 to-green-500 text-white hover:shadow-lg hover:shadow-emerald-500/50 hover:from-emerald-500 hover:to-green-400',
    outline: 'bg-transparent border-2 border-blue-500 text-blue-400 hover:bg-blue-500/10 hover:border-blue-400',
  }

  const sizeClasses = {
    sm: 'px-3 py-2 text-sm rounded-lg',
    md: 'px-6 py-3 text-base rounded-xl',
    lg: 'px-8 py-4 text-lg rounded-2xl',
  }

  return (
    <button
      ref={ref}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className || ''}`}
      disabled={loading}
      {...props}
    >
      {loading && <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />}
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </button>
  )
})
Button.displayName = 'Button'

/**
 * Premium Card Component
 */
export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    gradient?: boolean
    glow?: boolean
  }
>(({ gradient = false, glow = false, className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={`rounded-2xl overflow-hidden transition-all duration-300 ${
        gradient
          ? 'bg-gradient-to-br from-blue-600/20 to-purple-600/10 border border-blue-500/30'
          : 'bg-slate-900/40 border border-slate-700/50'
      } ${glow ? 'hover:shadow-xl hover:shadow-blue-500/30' : 'hover:shadow-xl'} backdrop-blur-md ${className || ''}`}
      {...props}
    >
      {children}
    </div>
  )
})
Card.displayName = 'Card'

/**
 * Premium Stat Card
 */
export const StatCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    label: string
    value: string | number
    icon?: React.ReactNode
    change?: number
    gradient?: string
  }
>(({ label, value, icon, change, gradient, className, ...props }, ref) => {
  return (
    <Card
      ref={ref}
      gradient={true}
      className={`p-6 relative overflow-hidden group ${className || ''}`}
      {...props}
    >
      <div className="absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" style={{backgroundImage: gradient}}></div>
      
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <span className="text-slate-400 text-sm font-semibold uppercase tracking-wide">{label}</span>
          {icon && <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400">{icon}</div>}
        </div>
        
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">{value}</span>
          {change !== undefined && (
            <span className={`text-sm font-bold ${change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {change >= 0 ? '+' : ''}{change}%
            </span>
          )}
        </div>
      </div>
    </Card>
  )
})
StatCard.displayName = 'StatCard'

/**
 * Premium Badge
 */
export const Badge = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    variant?: 'default' | 'success' | 'danger' | 'warning' | 'info'
    size?: 'sm' | 'md'
    icon?: React.ReactNode
  }
>(({ variant = 'default', size = 'sm', icon, className, children, ...props }, ref) => {
  const variantClasses = {
    default: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    success: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    danger: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    warning: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    info: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  }

  const sizeClasses = {
    sm: 'px-2.5 py-1 text-xs',
    md: 'px-3.5 py-1.5 text-sm',
  }

  return (
    <div
      ref={ref}
      className={`inline-flex items-center gap-1.5 rounded-full font-bold border ${variantClasses[variant]} ${sizeClasses[size]} ${className || ''}`}
      {...props}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </div>
  )
})
Badge.displayName = 'Badge'

/**
 * Premium Input
 */
export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & {
    icon?: React.ReactNode
    error?: string
  }
>(({ icon, error, className, ...props }, ref) => {
  return (
    <div className="relative">
      <input
        ref={ref}
        className={`w-full px-4 py-3 rounded-xl bg-slate-900/50 border transition-all duration-300 font-medium placeholder-slate-500 text-white backdrop-filter ${
          error
            ? 'border-rose-500/50 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20'
            : 'border-slate-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'
        } ${icon ? 'pl-12' : ''} ${className || ''}`}
        {...props}
      />
      {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">{icon}</div>}
      {error && <p className="text-rose-500 text-xs font-semibold mt-1">{error}</p>}
    </div>
  )
})
Input.displayName = 'Input'

/**
 * Premium Section Header
 */
export const SectionHeader = ({
  title,
  subtitle,
  icon,
  action,
}: {
  title: string
  subtitle?: string
  icon?: React.ReactNode
  action?: React.ReactNode
}) => {
  return (
    <div className="flex items-center justify-between mb-8 group">
      <div className="flex items-center gap-4">
        {icon && (
          <div className="p-3 bg-gradient-to-br from-blue-600/30 to-purple-600/20 rounded-xl group-hover:shadow-lg group-hover:shadow-blue-500/20 transition-all">
            {icon}
          </div>
        )}
        <div>
          <h2 className="text-3xl font-black tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">{title}</h2>
          {subtitle && <p className="text-slate-400 text-sm mt-1">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

/**
 * Premium Loading Skeleton
 */
export const Skeleton = ({ className }: { className?: string }) => {
  return <div className={`bg-slate-800/50 rounded-lg animate-shimmer ${className || 'h-8 w-24'}`} />
}

/**
 * Premium Alert Box
 */
export const Alert = ({
  type = 'info',
  title,
  message,
  action,
}: {
  type?: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  action?: React.ReactNode
}) => {
  const typeClasses = {
    success: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
    error: 'bg-rose-500/15 border-rose-500/30 text-rose-300',
    warning: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    info: 'bg-blue-500/15 border-blue-500/30 text-blue-300',
  }

  return (
    <div className={`p-4 rounded-xl border backdrop-blur-md ${typeClasses[type]}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-bold text-sm">{title}</p>
          <p className="text-sm opacity-90 mt-1">{message}</p>
        </div>
        {action && <div>{action}</div>}
      </div>
    </div>
  )
}

/**
 * Premium Progress Bar
 */
export const ProgressBar = ({
  value,
  max = 100,
  label,
  color = 'blue',
}: {
  value: number
  max?: number
  label?: string
  color?: 'blue' | 'green' | 'red' | 'yellow'
}) => {
  const percentage = (value / max) * 100

  const colorClasses = {
    blue: 'bg-gradient-to-r from-blue-600 to-blue-500 shadow-lg shadow-blue-500/50',
    green: 'bg-gradient-to-r from-emerald-600 to-emerald-500 shadow-lg shadow-emerald-500/50',
    red: 'bg-gradient-to-r from-rose-600 to-rose-500 shadow-lg shadow-rose-500/50',
    yellow: 'bg-gradient-to-r from-amber-600 to-amber-500 shadow-lg shadow-amber-500/50',
  }

  return (
    <div>
      {label && <p className="text-sm font-semibold text-slate-300 mb-2">{label}</p>}
      <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-500 rounded-full`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <p className="text-xs text-slate-500 mt-1">{percentage.toFixed(1)}%</p>
    </div>
  )
}

/**
 * Premium Data Grid Header
 */
export const GridHeader = ({ columns }: { columns: string[] }) => {
  return (
    <div className="grid gap-4 p-4 bg-gradient-to-r from-slate-800/50 to-slate-900/50 border-b border-slate-700 rounded-t-2xl">
      {columns.map((col, i) => (
        <div key={i} className="text-xs font-black uppercase tracking-widest text-slate-400">
          {col}
        </div>
      ))}
    </div>
  )
}

/**
 * Premium Glowing Badge
 */
export const GlowBadge = ({ children, color = 'blue' }: { children: React.ReactNode; color?: 'blue' | 'green' | 'red' | 'purple' }) => {
  const colorClasses = {
    blue: 'bg-blue-600 shadow-lg shadow-blue-500/50',
    green: 'bg-emerald-600 shadow-lg shadow-emerald-500/50',
    red: 'bg-rose-600 shadow-lg shadow-rose-500/50',
    purple: 'bg-purple-600 shadow-lg shadow-purple-500/50',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${colorClasses[color]}`}>
      {children}
    </span>
  )
}
