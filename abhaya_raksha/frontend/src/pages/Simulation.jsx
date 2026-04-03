import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Zap, CloudRain, Wind, Thermometer, Shield, CheckCircle, ArrowLeft } from 'lucide-react'

const PRESETS = [
  {
    label: 'Heavy Rainfall – Mumbai',
    icon: CloudRain,
    color: 'blue',
    data: { city: 'Mumbai', zone: 'Andheri', event_type: 'rain', value: 28 },
    description: 'Monsoon downpour exceeds 15mm threshold'
  },
  {
    label: 'Severe AQI – Delhi',
    icon: Wind,
    color: 'purple',
    data: { city: 'Delhi', zone: 'Connaught Place', event_type: 'aqi', value: 320 },
    description: 'Air quality index exceeds 200 (Very Unhealthy)'
  },
  {
    label: 'Extreme Heat – Chennai',
    icon: Thermometer,
    color: 'orange',
    data: { city: 'Chennai', zone: 'T Nagar', event_type: 'heat', value: 45 },
    description: 'Temperature exceeds 42°C heat threshold'
  },
  {
    label: 'Curfew / Strike – Bangalore',
    icon: Shield,
    color: 'red',
    data: { city: 'Bangalore', zone: 'Koramangala', event_type: 'curfew', value: 1 },
    description: 'Zone closure triggers full income protection'
  },
]

function StepBadge({ step, label, done }) {
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg ${done ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${done ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'}`}>
        {done ? '✓' : step}
      </div>
      <span className={`text-sm font-medium ${done ? 'text-green-700' : 'text-gray-500'}`}>{label}</span>
    </div>
  )
}

export default function Simulation() {
  const [selected, setSelected] = useState(null)
  const [custom, setCustom] = useState({ city: 'Mumbai', zone: 'Central', event_type: 'rain', value: 20 })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)

  const runSimulation = async (data) => {
    setLoading(true)
    setResult(null)
    setStep(0)

    try {
      // Animate steps
      setStep(1)
      await new Promise(r => setTimeout(r, 600))
      setStep(2)
      await new Promise(r => setTimeout(r, 600))

      const res = await api.post('/admin/simulate', data)
      setStep(3)
      await new Promise(r => setTimeout(r, 400))
      setStep(4)
      await new Promise(r => setTimeout(r, 400))
      setStep(5)

      setResult(res.data)
      if (res.data.triggered) {
        toast.success(`${res.data.affected_workers} claims triggered! ₹${res.data.total_payout.toLocaleString()} payout`)
      } else {
        toast('Threshold not breached — no claims triggered', { icon: 'ℹ️' })
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <Link to="/admin" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft size={16} /> Admin
        </Link>
        <div className="flex items-center gap-3">
          <Zap className="text-orange-500" size={24} />
          <div>
            <h1 className="font-bold text-lg">Disruption Simulator</h1>
            <p className="text-xs text-gray-500">Trigger parametric claims in real-time</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Preset Events */}
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-3">Quick Presets</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {PRESETS.map((preset, i) => {
              const Icon = preset.icon
              const colorMap = {
                blue: 'border-blue-200 hover:border-blue-400 bg-blue-50',
                purple: 'border-purple-200 hover:border-purple-400 bg-purple-50',
                orange: 'border-orange-200 hover:border-orange-400 bg-orange-50',
                red: 'border-red-200 hover:border-red-400 bg-red-50',
              }
              const iconColor = {
                blue: 'text-blue-500', purple: 'text-purple-500',
                orange: 'text-orange-500', red: 'text-red-500'
              }
              return (
                <button
                  key={i}
                  onClick={() => { setSelected(i); runSimulation(preset.data) }}
                  disabled={loading}
                  className={`text-left p-4 rounded-xl border-2 transition ${colorMap[preset.color]} ${selected === i ? 'ring-2 ring-offset-1 ring-blue-400' : ''} disabled:opacity-50`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Icon size={20} className={iconColor[preset.color]} />
                    <span className="font-semibold text-gray-800">{preset.label}</span>
                  </div>
                  <p className="text-sm text-gray-500">{preset.description}</p>
                  <div className="mt-2 text-xs text-gray-400">
                    {preset.data.event_type.toUpperCase()} = {preset.data.value} | {preset.data.city}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Custom Event */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h2 className="font-semibold text-gray-900 mb-4">Custom Event</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">City</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={custom.city}
                onChange={e => setCustom({ ...custom, city: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Zone</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={custom.zone}
                onChange={e => setCustom({ ...custom, zone: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Event Type</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={custom.event_type}
                onChange={e => setCustom({ ...custom, event_type: e.target.value })}
              >
                <option value="rain">Rain (threshold: 15mm)</option>
                <option value="aqi">AQI (threshold: 200)</option>
                <option value="heat">Heat (threshold: 42°C)</option>
                <option value="curfew">Curfew (threshold: 1)</option>
                <option value="flood">Flood (threshold: 1)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Value</label>
              <input
                type="number"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={custom.value}
                onChange={e => setCustom({ ...custom, value: Number(e.target.value) })}
              />
            </div>
          </div>
          <button
            onClick={() => { setSelected(null); runSimulation(custom) }}
            disabled={loading}
            className="bg-orange-500 hover:bg-orange-600 text-white font-semibold px-6 py-2.5 rounded-lg transition disabled:opacity-50 flex items-center gap-2"
          >
            <Zap size={16} />
            {loading ? 'Running...' : 'Trigger Event'}
          </button>
        </div>

        {/* Step-by-step flow */}
        {step > 0 && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h2 className="font-semibold text-gray-900 mb-4">Parametric Claim Flow</h2>
            <div className="space-y-2">
              <StepBadge step={1} label="Disruption event detected" done={step >= 1} />
              <StepBadge step={2} label="Threshold check: value vs limit" done={step >= 2} />
              <StepBadge step={3} label="Fraud validation for each worker" done={step >= 3} />
              <StepBadge step={4} label="Claims auto-approved" done={step >= 4} />
              <StepBadge step={5} label="Payouts queued for disbursement" done={step >= 5} />
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className={`rounded-xl p-6 border-2 ${result.triggered ? 'bg-green-50 border-green-300' : 'bg-gray-50 border-gray-200'}`}>
            <div className="flex items-center gap-3 mb-4">
              {result.triggered
                ? <CheckCircle className="text-green-600" size={28} />
                : <Shield className="text-gray-400" size={28} />
              }
              <div>
                <h3 className="font-bold text-lg text-gray-900">
                  {result.triggered ? 'Claims Triggered!' : 'No Claims Triggered'}
                </h3>
                <p className="text-sm text-gray-500">
                  {result.event_type.toUpperCase()} = {result.value} (threshold: {result.threshold})
                </p>
              </div>
            </div>

            {result.triggered && (
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="bg-white rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-blue-600">{result.affected_workers}</p>
                  <p className="text-xs text-gray-500">Workers affected</p>
                </div>
                <div className="bg-white rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-600">₹{result.total_payout.toLocaleString()}</p>
                  <p className="text-xs text-gray-500">Total payout</p>
                </div>
                <div className="bg-white rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-orange-500">
                    {result.claims_created.filter(c => c.status === 'approved').length}
                  </p>
                  <p className="text-xs text-gray-500">Auto-approved</p>
                </div>
              </div>
            )}

            {result.claims_created.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Claims created:</p>
                {result.claims_created.map(c => (
                  <div key={c.id} className="bg-white rounded-lg px-4 py-3 flex items-center justify-between text-sm">
                    <span className="text-gray-600">Claim #{c.id} — Worker #{c.worker_id}</span>
                    <div className="flex items-center gap-3">
                      {c.fraud_score > 0.4 && (
                        <span className="text-xs text-red-500">⚠️ fraud: {c.fraud_score.toFixed(2)}</span>
                      )}
                      <span className="font-semibold">₹{c.payout_amount.toLocaleString()}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        c.status === 'approved' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {c.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
