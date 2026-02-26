import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { AlertTriangle, TrendingUp, TrendingDown, Zap, RefreshCw } from 'lucide-react';
import { createApiClient, getApiBaseUrl } from '../api/client';

const apiClient = createApiClient(getApiBaseUrl(), localStorage.getItem('token') || '');

interface PatternData {
  name: string;
  description: string;
  occurrences: number;
  avg_loss: number;
  recommendation: string;
}

interface TradeStats {
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  total_trades: number;
  total_pnl: number;
  consecutive_losses: number;
  consecutive_wins: number;
}

interface PerformanceByRegime {
  regime: string;
  win_rate: number;
  trades: number;
  total_pnl: number;
}

interface PerformanceByMetric {
  category: string;
  win_rate: number;
  trades: number;
  total_pnl: number;
}

interface AutoAdaptSuggestion {
  size_multiplier: number;
  size_multiplier_reason: string;
  confidence_scaling: number;
  confidence_scaling_reason: string;
  cooldown_after_loss_minutes: number;
}

export const LearningPage: React.FC = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [patterns, setPatterns] = useState<PatternData[]>([]);
  const [regimePerformance, setRegimePerformance] = useState<PerformanceByRegime[]>([]);
  const [volatilityPerformance, setVolatilityPerformance] = useState<PerformanceByMetric[]>([]);
  const [spreadPerformance, setSpreadPerformance] = useState<PerformanceByMetric[]>([]);
  const [leveragePerformance, setLeveragePerformance] = useState<PerformanceByMetric[]>([]);
  const [timeOfDayPerformance, setTimeOfDayPerformance] = useState<PerformanceByMetric[]>([]);
  const [adaptations, setAdaptations] = useState<AutoAdaptSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoAdaptApplied, setAutoAdaptApplied] = useState(false);

  useEffect(() => {
    loadLearningMetrics();
  }, []);

  const loadLearningMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get('/learning/dashboard-metrics');

      if (response.data.status === 'insufficient_data') {
        setError(
          `Insufficient data: ${response.data.trades_recorded}/5 trades recorded. ` +
          'Learning analysis requires at least 5 trades.'
        );
        setLoading(false);
        return;
      }

      setMetrics(response.data);

      // Parse stats
      if (response.data.stats) {
        setStats(response.data.stats);

        // Build performance charts from stats
        if (response.data.stats.performance_by_regime) {
          setRegimePerformance(
            Object.entries(response.data.stats.performance_by_regime).map(
              ([regime, data]: [string, any]) => ({
                regime,
                win_rate: data.win_rate,
                trades: data.total_trades,
                total_pnl: data.total_pnl
              })
            )
          );
        }

        if (response.data.stats.performance_by_volatility) {
          setVolatilityPerformance(
            Object.entries(response.data.stats.performance_by_volatility).map(
              ([vol, data]: [string, any]) => ({
                category: vol,
                win_rate: data.win_rate,
                trades: data.total_trades,
                total_pnl: data.total_pnl
              })
            )
          );
        }

        if (response.data.stats.performance_by_spread) {
          setSpreadPerformance(
            Object.entries(response.data.stats.performance_by_spread).map(
              ([spread, data]: [string, any]) => ({
                category: spread,
                win_rate: data.win_rate,
                trades: data.total_trades,
                total_pnl: data.total_pnl
              })
            )
          );
        }

        if (response.data.stats.performance_by_leverage) {
          setLeveragePerformance(
            Object.entries(response.data.stats.performance_by_leverage).map(
              ([lev, data]: [string, any]) => ({
                category: `${lev}x`,
                win_rate: data.win_rate,
                trades: data.total_trades,
                total_pnl: data.total_pnl
              })
            )
          );
        }

        if (response.data.stats.performance_by_time_of_day) {
          setTimeOfDayPerformance(
            Object.entries(response.data.stats.performance_by_time_of_day).map(
              ([hour, data]: [string, any]) => ({
                category: `${hour}:00 UTC`,
                win_rate: data.win_rate,
                trades: data.total_trades,
                total_pnl: data.total_pnl
              })
            )
          );
        }
      }

      // Parse patterns
      if (response.data.top_patterns) {
        setPatterns(response.data.top_patterns);
      }

      // Parse auto-adapt suggestions
      if (response.data.suggested_adaptations) {
        setAdaptations(response.data.suggested_adaptations);
      }

      setLoading(false);
    } catch (err) {
      setError(`Failed to load learning metrics: ${err}`);
      setLoading(false);
    }
  };

  const handleApplyAutoAdapt = async () => {
    try {
      const response = await apiClient.post('/learning/auto-adapt/apply');
      if (response.data.success) {
        setAutoAdaptApplied(true);
        setTimeout(() => loadLearningMetrics(), 1000);
      }
    } catch (err) {
      setError(`Failed to apply auto-adapt: ${err}`);
    }
  };

  const handleManualAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post('/learning/analyze');

      setTimeout(() => loadLearningMetrics(), 1000);
    } catch (err) {
      setError(`Failed to trigger analysis: ${err}`);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="inline-block">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
          <p className="mt-4 text-slate-400">Loading learning metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Learning & Adaptation</h1>
          <p className="text-slate-400 mt-2">
            AI analysis of trading history, pattern detection, and automated optimization
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleManualAnalysis}
            disabled={loading}
            className="btn btn-primary flex items-center gap-2"
          >
            <RefreshCw size={18} />
            Analyze Now
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-danger flex items-start gap-3">
          <AlertTriangle size={20} className="flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold">Error</h3>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {!error && metrics && (
        <>
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="card">
              <div className="card-body flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Win Rate</p>
                  <p className="text-2xl font-bold">
                    {typeof metrics.key_metrics.win_rate === 'string'
                      ? metrics.key_metrics.win_rate
                      : `${(metrics.key_metrics.win_rate * 100).toFixed(1)}%`}
                  </p>
                </div>
                <TrendingUp className="text-green-600" size={24} />
              </div>
            </div>

            <div className="card">
              <div className="card-body flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Profit Factor</p>
                  <p className="text-2xl font-bold">
                    {metrics.key_metrics.profit_factor}
                  </p>
                </div>
                <TrendingUp className="text-blue-600" size={24} />
              </div>
            </div>

            <div className="card">
              <div className="card-body flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Max Drawdown</p>
                  <p className="text-2xl font-bold">
                    {metrics.key_metrics.max_drawdown}
                  </p>
                </div>
                <TrendingDown className="text-orange-600" size={24} />
              </div>
            </div>

            <div className="card">
              <div className="card-body flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Trades Analyzed</p>
                  <p className="text-2xl font-bold">
                    {metrics.trades_analyzed}
                  </p>
                </div>
                <Zap className="text-purple-600" size={24} />
              </div>
            </div>
          </div>

          {/* Patterns Section */}
          {patterns.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <AlertTriangle size={22} className="text-red-600" />
                Discovered Losing Patterns
              </h2>

              <div className="space-y-3">
                {patterns.map((pattern, idx) => (
                  <div
                    key={idx}
                    className="border border-red-100 bg-red-50 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-red-900 mb-1">
                          {pattern.name.replace(/_/g, ' ').toUpperCase()}
                        </h3>
                        <p className="text-sm text-red-800 mb-2">{pattern.description}</p>
                        <p className="text-xs text-red-700">
                          <strong>Recommendation:</strong> {pattern.recommendation}
                        </p>
                      </div>
                      <div className="ml-4 text-right">
                        <p className="text-lg font-bold text-red-600">
                          {pattern.occurrences}x
                        </p>
                        <p className="text-xs text-red-600">
                          {pattern.avg_loss && `Avg loss: ${pattern.avg_loss.toFixed(2)}`}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Auto-Adapt Suggestions */}
          {adaptations && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Suggested Auto-Adapt Changes
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="bg-white rounded border border-blue-100 p-3">
                  <p className="text-sm text-gray-600">Position Size Multiplier</p>
                  <p className="text-lg font-bold text-blue-600">
                    {adaptations.size_multiplier.toFixed(2)}x
                  </p>
                  <p className="text-xs text-gray-700 mt-1">
                    {adaptations.size_multiplier_reason}
                  </p>
                </div>

                <div className="bg-white rounded border border-blue-100 p-3">
                  <p className="text-sm text-gray-600">Confidence Scaling</p>
                  <p className="text-lg font-bold text-blue-600">
                    {adaptations.confidence_scaling.toFixed(2)}x
                  </p>
                  <p className="text-xs text-gray-700 mt-1">
                    {adaptations.confidence_scaling_reason}
                  </p>
                </div>

                <div className="bg-white rounded border border-blue-100 p-3">
                  <p className="text-sm text-gray-600">Cooldown After Loss</p>
                  <p className="text-lg font-bold text-blue-600">
                    {adaptations.cooldown_after_loss_minutes}m
                  </p>
                  <p className="text-xs text-gray-700 mt-1">
                    Prevent revenge trading
                  </p>
                </div>
              </div>

              <div className="bg-white rounded p-3 mb-4">
                <p className="text-sm text-gray-700">
                  <strong>⚠️ Safety Constraints:</strong> Only position size, confidence threshold, 
                  and cooldown can change. Leverage, stop-loss logic, and symbols remain unchanged.
                </p>
              </div>

              <button
                onClick={handleApplyAutoAdapt}
                disabled={autoAdaptApplied}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg 
                           hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {autoAdaptApplied ? '✓ Applied' : 'Apply Suggestions'}
              </button>
            </div>
          )}

          {/* Performance by Market Regime */}
          {regimePerformance.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Performance by Market Regime
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={regimePerformance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="regime" />
                  <YAxis />
                  <Tooltip formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value} />
                  <Legend />
                  <Bar dataKey="win_rate" name="Win Rate" fill="#8b5cf6" />
                  <Bar dataKey="total_pnl" name="Total PnL" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Performance by Volatility */}
          {volatilityPerformance.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Performance by Volatility
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={volatilityPerformance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <Tooltip formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value} />
                  <Legend />
                  <Bar dataKey="win_rate" name="Win Rate" fill="#0ea5e9" />
                  <Bar dataKey="trades" name="Trade Count" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Performance by Spread */}
          {spreadPerformance.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Performance by Spread
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={spreadPerformance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <Tooltip formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value} />
                  <Legend />
                  <Bar dataKey="win_rate" name="Win Rate" fill="#ec4899" />
                  <Bar dataKey="total_pnl" name="Total PnL" fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Performance by Leverage */}
          {leveragePerformance.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Performance by Leverage
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={leveragePerformance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <Tooltip formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value} />
                  <Legend />
                  <Line type="monotone" dataKey="win_rate" name="Win Rate" stroke="#10b981" />
                  <Line type="monotone" dataKey="trades" name="Trade Count" stroke="#f59e0b" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Performance by Time of Day */}
          {timeOfDayPerformance.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Performance by Time of Day (UTC)
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={timeOfDayPerformance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" angle={-45} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value} />
                  <Legend />
                  <Line type="monotone" dataKey="win_rate" name="Win Rate" stroke="#06b6d4" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LearningPage;
