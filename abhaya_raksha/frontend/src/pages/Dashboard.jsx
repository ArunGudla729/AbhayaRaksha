import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import {
  Shield, TrendingUp, CheckCircle,
  CloudRain, Wind, Thermometer, LogOut, RefreshCw, Info, X
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import WithdrawModal from '../components/WithdrawModal'
import ActivationModal from '../components/ActivationModal'

function StatCard({ icon: Icon, label, value, color = 'blue', sub }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    red: 'bg-red-50 text-red-600',
  }
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 rounded-lg ${colors[color]}`}>
          <Icon size={20} />
        </div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function RiskMeter({ score }) {
  const pct = Math.round(score * 100)
  const color = pct < 30 ? '#22c55e' : pct < 60 ? '#f59e0b' : '#ef4444'
  const label = pct < 30 ? 'Low Risk' : pct < 60 ? 'Moderate Risk' : 'High Risk'
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Current Risk Level</h3>
      <div className="flex items-center gap-4">
        <div className="relative w-20 h-20">
          <svg viewBox="0 0 36 36" className="w-20 h-20 -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3" />
            <circle
              cx="18" cy="18" r="15.9" fill="none"
              stroke={color} strokeWidth="3"
              strokeDasharray={`${pct} ${100 - pct}`}
              strokeLinecap="round"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-lg font-bold" style={{ color }}>
            {pct}%
          </span>
        </div>
        <div>
          <p className="font-semibold text-lg" style={{ color }}>{label}</p>
          <p className="text-xs text-gray-400">Updated live</p>
        </div>
      </div>
    </div>
  )
}

// City-specific rain thresholds — mirrors CITY_RAIN_THRESHOLDS in claim_engine.py.
// Keeps warning colours in sync with what actually triggers a backend claim.
const CITY_RAIN_THRESHOLDS = {
  mumbai:    35,
  delhi:     12,
  chennai:   25,
  bangalore: 20,
  hyderabad: 15,
}

function getRainThreshold(city = '') {
  return CITY_RAIN_THRESHOLDS[city.toLowerCase()] ?? 15
}

// Format a UTC ISO timestamp to IST for display
function toIST(isoString) {
  return new Date(isoString).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
}

export default function Dashboard() {
  const [worker, setWorker] = useState(null)
  const [risk, setRisk] = useState(null)
  const [policy, setPolicy] = useState(null)
  const [claims, setClaims] = useState([])
  const [summary, setSummary] = useState('')
  const [shiftAdvice, setShiftAdvice] = useState('')
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [withdrawClaim, setWithdrawClaim] = useState(null)
  const [showExclusions, setShowExclusions] = useState(false)
  const [showActivationModal, setShowActivationModal] = useState(false)
  const [isSystemicPause, setIsSystemicPause] = useState(false)
  const navigate = useNavigate()

  const loadData = async (isRefresh = false) => {
    try {
      if (isRefresh) setIsRefreshing(true)
      else setLoading(true)

      const [wRes, rRes] = await Promise.all([
        api.get('/workers/me'),
        api.get('/workers/risk')
      ])
      setWorker(wRes.data)
      setRisk(rRes.data)

      try {
        const pRes = await api.get('/policies/active')
        setPolicy(pRes.data)
      } catch { setPolicy(null) }

      const cRes = await api.get('/claims/my')
      setClaims(cRes.data)

      // Systemic pause state — uses the worker-accessible public endpoint
      api.get('/system/status')
        .then(r => setIsSystemicPause(r.data.is_systemic_pause ?? false))
        .catch(() => setIsSystemicPause(false))

      // Load AI summary in background
      api.get('/workers/risk/summary').then(r => setSummary(r.data.summary)).catch(() => {})
      // Smart-Shift advice in background
      api.get('/workers/shift-advice').then(r => setShiftAdvice(r.data.shift_advice)).catch(() => {})
    } catch (err) {
      toast.error('Failed to load data')
    } finally {
      if (isRefresh) setIsRefreshing(false)
      else setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleActivationClose = (didActivate) => {
    setShowActivationModal(false)
    if (didActivate) loadData()
  }

  const handleWithdrawClose = (didSucceed) => {
    setWithdrawClaim(null)
    if (didSucceed) {
      toast.success('Transfer complete! Your balance has been updated.')
      loadData()
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('is_admin')
    navigate('/login')
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>
  )

  const weeklyIncome = worker ? worker.avg_daily_income * 5 : 0
  const approvedClaims = claims.filter(c => c.status === 'approved' || c.status === 'paid')
  const totalPaid = claims.filter(c => c.status === 'paid').reduce((s, c) => s + c.payout_amount, 0)
  const hasActivePolicy = !!policy

  const claimChartData = ['rain', 'aqi', 'heat', 'curfew'].map(type => ({
    name: type.toUpperCase(),
    count: claims.filter(c => c.trigger_type === type).length
  }))

  return (
    <>
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="text-blue-600" size={28} />
          <div>
            <h1 className="font-bold text-lg text-gray-900">AbhayaRaksha</h1>
            <p className="text-xs text-gray-500">Income Protection Dashboard</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">Welcome Back {worker?.name}</span>
          <button onClick={() => loadData(true)} disabled={isRefreshing} className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50" title={isRefreshing ? "Refreshing..." : "Refresh"}>
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
          <button onClick={logout} className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-500">
            <LogOut size={16} /> Logout
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Systemic Emergency Banner */}
        {isSystemicPause && (
          <div className="bg-red-600 text-white rounded-xl px-5 py-4 flex items-start gap-3 shadow-lg">
            <span className="text-xl flex-shrink-0">🚨</span>
            <div>
              <p className="font-bold text-sm">SYSTEMIC EMERGENCY: Payouts Temporarily Paused</p>
              <p className="text-xs text-red-100 mt-0.5">
                Automated parametric payouts are suspended for fund sustainability during a
                War / Pandemic / Force Majeure event. Your policy remains active and coverage
                will resume once the emergency is lifted by the platform administrator.
              </p>
            </div>
          </div>
        )}

        {/* ── No active policy — show Activation Card only ─────────── */}
        {!hasActivePolicy && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 w-full max-w-md p-8 space-y-6">
              <div className="text-center space-y-2">
                <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto">
                  <Shield className="text-blue-600" size={32} />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Protect Your Income</h2>
                <p className="text-sm text-gray-500">
                  You don't have an active policy. Activate now to get automatic payouts
                  when rain, AQI, or heat disrupts your deliveries.
                </p>
              </div>

              {risk && (
                <div className="bg-blue-50 rounded-xl p-4 space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Weekly premium</span>
                    <span className="font-bold text-blue-700">₹{risk.weekly_premium?.toLocaleString()}/week <span className="text-xs font-normal text-green-600">inclusive</span></span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Income protected</span>
                    <span className="font-semibold text-green-700">₹{risk.coverage_amount?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Your risk score</span>
                    <span className="text-gray-700">{Math.round(risk.risk_score * 100)}% — {risk.risk_score < 0.3 ? 'Low' : risk.risk_score < 0.6 ? 'Moderate' : 'High'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Coverage window</span>
                    <span className="text-gray-700">7 days</span>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <button
                  onClick={() => setShowActivationModal(true)}
                  disabled={isSystemicPause}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  {isSystemicPause ? '🚨 Paused — Emergency Active' : 'Activate Weekly Policy'}
                </button>
                <button
                  onClick={() => setShowExclusions(true)}
                  className="w-full flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 transition"
                >
                  <Info size={13} /> View policy exclusions & Force Majeure terms
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Active policy — full dashboard ────────────────────────── */}
        {hasActivePolicy && (<>
        {/* Smart-Shift Planner */}
        {shiftAdvice && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🛡️</span>
              <span className="text-sm font-semibold text-gray-800">Abhaya Smart-Shift</span>
              <span className="ml-auto text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Tomorrow's forecast</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{shiftAdvice}</p>
          </div>
        )}
        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={TrendingUp} label="Weekly Income" value={`₹${weeklyIncome.toLocaleString()}`} color="blue" sub="6 working days" />
          <StatCard icon={Shield} label="Protected Weekly Income" value={risk ? `₹${risk.coverage_amount.toLocaleString()}` : '—'} color="green" sub="Max weekly payout" />
          <StatCard icon={CheckCircle} label="Claims Approved" value={approvedClaims.length} color="orange" sub="This account" />
          <StatCard icon={TrendingUp} label="Total Received" value={`₹${totalPaid.toLocaleString()}`} color="green" sub="Lifetime payouts" />
        </div>

        {/* Risk + Policy Row */}
        <div className="grid md:grid-cols-3 gap-4">
          {risk && <RiskMeter score={risk.risk_score} />}

          {/* Weather Conditions */}
          {risk && (
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h3 className="text-sm font-medium text-gray-500 mb-3">Live Conditions – {risk.city}</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-blue-500">
                    <CloudRain size={16} /> <span className="text-sm">Rainfall</span>
                  </div>
                  {(() => {
                    const threshold = getRainThreshold(risk.city)
                    const warn = risk.rain_mm >= threshold
                    return (
                      <span className={`text-sm font-semibold ${warn ? 'text-red-500' : 'text-gray-700'}`}>
                        {risk.rain_mm} mm {warn ? `⚠️ ≥${threshold}mm` : '✓'}
                      </span>
                    )
                  })()}
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-purple-500">
                    <Wind size={16} /> <span className="text-sm">AQI</span>
                  </div>
                  <span className={`text-sm font-semibold ${risk.aqi >= 200 ? 'text-red-500' : 'text-gray-700'}`}>
                    {risk.aqi} {risk.aqi >= 200 ? '⚠️' : '✓'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-orange-500">
                    <Thermometer size={16} /> <span className="text-sm">Temperature</span>
                  </div>
                  <span className={`text-sm font-semibold ${risk.temp_c >= 42 ? 'text-red-500' : 'text-gray-700'}`}>
                    {Math.round(risk.temp_c)}°C {risk.temp_c >= 42 ? '⚠️' : '✓'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Policy Card */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-500">Your Policy</h3>
              <button
                onClick={() => setShowExclusions(true)}
                className="text-gray-400 hover:text-blue-500 transition"
                title="View policy exclusions & Force Majeure terms"
                aria-label="View policy exclusions"
              >
                <Info size={15} />
              </button>
            </div>
            <div className="space-y-2">
              {(() => {
                const now = new Date()
                const coverStart = policy.underwriting_start_date
                  ? new Date(policy.underwriting_start_date)
                  : null
                const isPending = coverStart && now < coverStart
                const daysLeft = coverStart
                  ? Math.ceil((coverStart - now) / (1000 * 60 * 60 * 24))
                  : 0
                return isPending ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                      <span className="text-sm font-semibold text-yellow-600">Pending</span>
                    </div>
                    <p className="text-sm text-yellow-700 font-medium">
                      🛡️ Underwriting: Starts in {daysLeft} day{daysLeft !== 1 ? 's' : ''}.
                    </p>
                  </>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm font-semibold text-green-600">Active</span>
                  </div>
                )
              })()}
              <p className="text-2xl font-bold text-gray-900">₹{Math.round(policy.weekly_premium)}/week</p>
              <p className="text-xs text-gray-500">Protected weekly income: ₹{Math.round(policy.coverage_amount).toLocaleString()}</p>
              <p className="text-xs text-green-600 font-medium">✓ Inclusive micro-insurance pricing</p>
              <p className="text-xs text-gray-400">
                Expires: {new Date(policy.end_date).toLocaleDateString('en-IN')}
              </p>
            </div>
          </div>
        </div>

        {/* AI Summary */}
        {summary && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🤖</span>
              <span className="text-sm font-semibold text-blue-700">AI Risk Summary</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{summary}</p>
          </div>
        )}

        {/* Claims History */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Claims History</h3>
          </div>
          {claims.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              <Shield size={40} className="mx-auto mb-2 opacity-30" />
              <p>No claims yet. Claims trigger automatically when disruptions occur.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {claims.map(claim => (
                <div key={claim.id} className="px-5 py-4 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium capitalize">{claim.trigger_type} disruption</span>
                      {claim.fraud_score > 0.4 && (
                        <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                          ⚠️ Fraud flag
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {toIST(claim.created_at)} IST •
                      Value: {claim.trigger_value} (threshold: {claim.trigger_threshold})
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">₹{claim.payout_amount.toLocaleString()}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        claim.status === 'paid' ? 'bg-green-100 text-green-700' :
                        claim.status === 'approved' ? 'bg-blue-100 text-blue-700' :
                        claim.status === 'rejected' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {claim.status}
                      </span>
                    </div>
                    {claim.status === 'approved' && (
                      <button
                        onClick={() => !isSystemicPause && setWithdrawClaim(claim)}
                        disabled={isSystemicPause}
                        className={`text-xs px-3 py-1.5 rounded-lg transition font-medium ${
                          isSystemicPause
                            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        }`}
                        title={isSystemicPause ? 'Withdrawals paused during Force Majeure event' : undefined}
                      >
                        {isSystemicPause ? 'Paused' : 'Withdraw to UPI'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Claims Chart */}
        {claims.length > 0 && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h3 className="font-semibold text-gray-900 mb-4">Claims by Trigger Type</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={claimChartData}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {claimChartData.map((_, i) => (
                    <Cell key={i} fill={['#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'][i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        </>)}
      </main>
    </div>

    {/* Withdraw modal */}
    {withdrawClaim && (
      <WithdrawModal claim={withdrawClaim} onClose={handleWithdrawClose} />
    )}

    {/* Activation modal */}
    {showActivationModal && (
      <ActivationModal
        risk={risk}
        onClose={handleActivationClose}
        onShowTerms={() => { setShowActivationModal(false); setShowExclusions(true) }}
      />
    )}

    {/* Policy Exclusions & Force Majeure modal */}
    {showExclusions && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        onClick={e => { if (e.target === e.currentTarget) setShowExclusions(false) }}
      >
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <Shield className="text-blue-600" size={20} />
              <h2 className="font-bold text-gray-900">Policy Exclusions & Force Majeure</h2>
            </div>
            <button onClick={() => setShowExclusions(false)} className="text-gray-400 hover:text-gray-600 transition">
              <X size={20} />
            </button>
          </div>
          <div className="px-6 py-5 space-y-4">
            <p className="text-sm text-gray-600 leading-relaxed">
              To ensure long-term fund sustainability for all workers, coverage is explicitly
              excluded for losses resulting from:
            </p>
            <ol className="space-y-3">
              {[
                { n: '1', title: 'Acts of War or Terrorism', desc: 'Any loss directly or indirectly caused by declared or undeclared war, invasion, civil war, or acts of terrorism.' },
                { n: '2', title: 'Global Pandemics', desc: 'Disruptions arising from events classified as a Public Health Emergency of International Concern (PHEIC) or pandemic by the World Health Organization (WHO).' },
                { n: '3', title: 'Radioactive / Nuclear Contamination', desc: 'Any loss attributable to ionising radiation, radioactive contamination, or nuclear reaction from any source.' },
              ].map(item => (
                <li key={item.n} className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 text-red-600 text-xs font-bold flex items-center justify-center">
                    {item.n}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{item.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-700 leading-relaxed">
              These exclusions are standard actuarial practice in parametric insurance and protect
              the fund from systemic, uninsurable risks that would otherwise cause insolvency.
            </div>
          </div>
          <div className="px-6 pb-5">
            <button
              onClick={() => setShowExclusions(false)}
              className="w-full bg-gray-900 hover:bg-gray-800 text-white font-semibold py-2.5 rounded-xl transition text-sm"
            >
              Understood
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  )
}
