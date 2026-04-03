import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import {
  Users, Shield, TrendingUp,
  DollarSign, Activity, Zap, ShieldAlert
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend
} from 'recharts'

function StatCard({ icon: Icon, label, value, color, sub }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  }
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 rounded-lg ${colors[color] || colors.blue}`}>
          <Icon size={20} />
        </div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

// Format a UTC ISO timestamp to IST for display
function toIST(isoString) {
  return new Date(isoString).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [claims, setClaims] = useState([])
  const [fraudAlerts, setFraudAlerts] = useState([])
  const [weekly, setWeekly] = useState([])
  const [heatmap, setHeatmap] = useState([])
  const [insight, setInsight] = useState('')
  const [loading, setLoading] = useState(true)
  const [isPaused, setIsPaused] = useState(false)
  const [pauseToggling, setPauseToggling] = useState(false)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [sRes, cRes, fRes, wRes, hRes, pRes] = await Promise.all([
          api.get('/admin/stats'),
          api.get('/admin/claims'),
          api.get('/admin/fraud-alerts'),
          api.get('/admin/analytics/weekly'),
          api.get('/admin/risk-heatmap'),
          api.get('/system/status'),   // public endpoint — same source of truth as worker dashboard
        ])
        setStats(sRes.data)
        setClaims(cRes.data.slice(0, 10))
        setFraudAlerts(fRes.data.slice(0, 5))
        setWeekly(wRes.data.reverse())
        setHeatmap(hRes.data)
        setIsPaused(pRes.data.is_systemic_pause)
        api.get('/admin/stats/insight').then(r => setInsight(r.data.insight)).catch(() => {})
        api.get('/admin/system-health').then(r => setHealth(r.data)).catch(() => {})
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>
  )

  const lossRatioPct = stats ? (stats.loss_ratio * 100).toFixed(1) : 0
  const lossColor = stats?.loss_ratio > 0.8 ? 'text-red-600' : stats?.loss_ratio > 0.5 ? 'text-orange-500' : 'text-green-600'

  const handleTogglePause = async () => {
    setPauseToggling(true)
    try {
      const res = await api.post('/admin/toggle-pause')
      setIsPaused(res.data.is_systemic_pause)
    } catch (err) {
      console.error('Failed to toggle systemic pause', err)
    } finally {
      setPauseToggling(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="text-blue-600" size={28} />
          <div>
            <h1 className="font-bold text-lg">AbhayaRaksha Admin</h1>
            <p className="text-xs text-gray-500">Platform Operations Dashboard</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link to="/simulate" className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
            <Zap size={16} /> Run Simulation
          </Link>
          <Link to="/login" className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2">
            Worker Login →
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Users} label="Total Workers" value={stats.total_workers} color="blue" />
            <StatCard icon={Shield} label="Active Policies" value={stats.active_policies} color="green" sub={`${stats.total_policies} total`} />
            <StatCard icon={Activity} label="Total Claims" value={stats.total_claims} color="orange" sub={`${stats.approved_claims} approved`} />
            <StatCard icon={DollarSign} label="Total Payout" value={`₹${stats.total_payout.toLocaleString()}`} color="purple" />
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-4">
          {/* Loss Ratio */}
          {stats && (
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h3 className="text-sm text-gray-500 mb-2">Loss Ratio</h3>
              <p className={`text-4xl font-bold ${lossColor}`}>{lossRatioPct}%</p>
              <p className="text-xs text-gray-400 mt-1">
                {stats.loss_ratio < 0.5 ? '✅ Healthy' : stats.loss_ratio < 0.8 ? '⚠️ Monitor' : '🚨 Critical'}
              </p>
              <div className="mt-3 bg-gray-100 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${stats.loss_ratio < 0.5 ? 'bg-green-500' : stats.loss_ratio < 0.8 ? 'bg-orange-400' : 'bg-red-500'}`}
                  style={{ width: `${Math.min(lossRatioPct, 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* Fraud Alerts */}
          {stats && (
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h3 className="text-sm text-gray-500 mb-2">Fraud Alerts</h3>
              <p className="text-4xl font-bold text-red-500">{stats.fraud_alerts}</p>
              <p className="text-xs text-gray-400 mt-1">Claims with fraud score ≥ 0.6</p>
              {fraudAlerts.length > 0 && (
                <div className="mt-3 space-y-1">
                  {fraudAlerts.slice(0, 3).map(f => (
                    <div key={f.id} className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">
                      Claim #{f.id} — score: {f.fraud_score?.toFixed(2)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* AI Insight */}
          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <span>🤖</span>
              <span className="text-sm font-semibold text-indigo-700">AI Insight</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">
              {insight || 'Loading AI analysis...'}
            </p>
          </div>
        </div>

        {/* Weekly Analytics Chart */}
        {weekly.length > 0 && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h3 className="font-semibold text-gray-900 mb-4">Weekly Claims & Payouts</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weekly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="claims" fill="#3b82f6" name="Claims" radius={[4,4,0,0]} />
                <Bar yAxisId="right" dataKey="payout" fill="#10b981" name="Payout (₹)" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Risk Heatmap */}
        {heatmap.length > 0 && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h3 className="font-semibold text-gray-900 mb-4">Risk Heatmap by City</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {heatmap.map(h => {
                const pct = Math.round(h.avg_risk * 100)
                const bg = pct < 30 ? 'bg-green-100 border-green-300' : pct < 60 ? 'bg-yellow-100 border-yellow-300' : 'bg-red-100 border-red-300'
                const text = pct < 30 ? 'text-green-700' : pct < 60 ? 'text-yellow-700' : 'text-red-700'
                return (
                  <div key={h.city} className={`border rounded-lg p-3 ${bg}`}>
                    <p className="text-sm font-medium text-gray-700">{h.city}</p>
                    <p className={`text-2xl font-bold ${text}`}>{pct}%</p>
                    <p className="text-xs text-gray-500">{h.data_points} readings</p>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Systemic Risk Management */}
        <div className={`rounded-xl border-2 p-5 ${isPaused ? 'bg-red-50 border-red-400' : 'bg-white border-gray-200'}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg ${isPaused ? 'bg-red-100' : 'bg-gray-100'}`}>
                <ShieldAlert size={22} className={isPaused ? 'text-red-600' : 'text-gray-500'} />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Systemic Risk Management</h3>
                <p className="text-xs text-gray-500 mt-0.5 max-w-lg">
                  Enable this <strong>ONLY</strong> during national emergencies (War / Pandemic / Nuclear Hazard)
                  to prevent fund insolvency. This will immediately pause <strong>all</strong> automated
                  parametric payouts platform-wide until manually deactivated.
                </p>
                {isPaused && (
                  <p className="text-xs font-semibold text-red-600 mt-2">
                    🚨 ACTIVE — All parametric payouts are currently suspended.
                  </p>
                )}
              </div>
            </div>
            {/* Toggle switch */}
            <button
              onClick={handleTogglePause}
              disabled={pauseToggling}
              aria-pressed={isPaused}
              className={`relative flex-shrink-0 w-14 h-7 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                isPaused ? 'bg-red-500 focus:ring-red-400' : 'bg-gray-300 focus:ring-gray-400'
              } disabled:opacity-60`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform duration-200 ${
                  isPaused ? 'translate-x-7' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              isPaused ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {isPaused ? 'PAUSED — Force Majeure Active' : 'ACTIVE — Normal Operations'}
            </span>
          </div>
        </div>

        {/* Recent Claims Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Recent Claims</h3>
            <span className="text-xs text-gray-400">Last 10</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {['ID', 'Worker', 'Trigger', 'Value', 'Payout', 'Fraud Score', 'Status', 'Time (IST)'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {claims.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">#{c.id}</td>
                    <td className="px-4 py-3">Worker #{c.worker_id}</td>
                    <td className="px-4 py-3 capitalize">{c.trigger_type}</td>
                    <td className="px-4 py-3">{c.trigger_value}</td>
                    <td className="px-4 py-3 font-medium">₹{c.payout_amount?.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        c.fraud_score >= 0.6 ? 'bg-red-100 text-red-700' :
                        c.fraud_score >= 0.3 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {c.fraud_score?.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        c.status === 'paid' ? 'bg-green-100 text-green-700' :
                        c.status === 'approved' ? 'bg-blue-100 text-blue-700' :
                        c.status === 'rejected' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{toIST(c.created_at)}</td>
                  </tr>
                ))}
                {claims.length === 0 && (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No claims yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        {/* System Health */}
        {health && (
          <div className={`rounded-xl border-2 p-5 ${health.enrollment_suspended ? 'bg-red-50 border-red-400' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-900">System Health — Actuarial Metrics</h3>
              {health.enrollment_suspended && (
                <span className="text-xs font-bold bg-red-600 text-white px-3 py-1 rounded-full animate-pulse">
                  🚨 Enrollment Suspended: High Risk
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-1">Premiums Collected</p>
                <p className="text-xl font-bold text-gray-900">₹{Math.round(health.total_premiums_collected).toLocaleString()}</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-1">Claims Paid</p>
                <p className="text-xl font-bold text-gray-900">₹{Math.round(health.total_claims_paid).toLocaleString()}</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-1">BCR (Burning Cost Rate)</p>
                <p className={`text-xl font-bold ${health.bcr > 0.85 ? 'text-red-600' : health.bcr > 0.5 ? 'text-orange-500' : 'text-green-600'}`}>
                  {(health.bcr * 100).toFixed(1)}%
                </p>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-1">Loss Ratio</p>
                <p className={`text-xl font-bold ${health.loss_ratio_pct > 85 ? 'text-red-600' : health.loss_ratio_pct > 50 ? 'text-orange-500' : 'text-green-600'}`}>
                  {health.loss_ratio_pct.toFixed(1)}%
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {health.loss_ratio_pct <= 50 ? '✅ Healthy' : health.loss_ratio_pct <= 85 ? '⚠️ Monitor' : '🚨 Critical'}
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
