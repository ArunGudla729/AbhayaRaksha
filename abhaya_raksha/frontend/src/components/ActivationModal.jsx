import { useState, useEffect } from 'react'
import { CheckCircle, X, Loader2, Shield, Info } from 'lucide-react'
import api from '../api'

/**
 * ActivationModal — simulates the weekly premium payment flow.
 *
 * Props:
 *   risk        — risk data object (weekly_premium, coverage_amount, risk_score, city)
 *   onClose     — called when dismissed; receives `true` if activation succeeded
 *   onShowTerms — called when worker clicks the exclusions (ⓘ) link
 */
export default function ActivationModal({ risk, onClose, onShowTerms }) {
  // phase: 'confirm' | 'processing' | 'success' | 'error'
  const [phase, setPhase] = useState('confirm')
  const [policy, setPolicy] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const handleActivate = async () => {
    setPhase('processing')
    // Simulate payment gateway delay before hitting the real endpoint
    await new Promise(r => setTimeout(r, 2200))
    try {
      const res = await api.post('/policies/activate')
      setPolicy(res.data)
      setPhase('success')
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Activation failed. Please try again.')
      setPhase('error')
    }
  }

  const handleClose = () => onClose(phase === 'success')

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget && phase !== 'processing') handleClose() }}
    >
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">

        {/* Close — hidden during processing */}
        {phase !== 'processing' && (
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        )}

        {/* ── Confirm ───────────────────────────────────────────────── */}
        {phase === 'confirm' && (
          <div className="p-6 space-y-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-xl">
                <Shield className="text-blue-600" size={24} />
              </div>
              <div>
                <h2 className="font-bold text-gray-900 text-lg">Activate Weekly Policy</h2>
                <p className="text-xs text-gray-500">{risk?.city} — risk-adjusted premium</p>
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Weekly premium</span>
                <span className="font-bold text-gray-900">₹{risk?.weekly_premium?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Income protected</span>
                <span className="font-semibold text-green-700">₹{risk?.coverage_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Risk score</span>
                <span className="text-gray-700">{Math.round((risk?.risk_score ?? 0) * 100)}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Coverage window</span>
                <span className="text-gray-700">7 days from now</span>
              </div>
            </div>

            {/* Terms summary */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-1">
              <p className="text-xs font-semibold text-amber-800">Standard exclusions apply:</p>
              <ul className="text-xs text-amber-700 space-y-0.5">
                {['War / Terrorism', 'WHO-declared Pandemics', 'Nuclear / Radioactive events'].map(e => (
                  <li key={e} className="flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-amber-500 flex-shrink-0" />
                    {e}
                  </li>
                ))}
              </ul>
              <button
                onClick={onShowTerms}
                className="text-xs text-blue-600 hover:underline mt-1 flex items-center gap-1"
              >
                <Info size={11} /> Read full policy exclusions
              </button>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleClose}
                className="flex-1 border border-gray-200 text-gray-600 text-sm font-medium py-2.5 rounded-xl hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleActivate}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2.5 rounded-xl transition"
              >
                Pay & Activate
              </button>
            </div>
          </div>
        )}

        {/* ── Processing ────────────────────────────────────────────── */}
        {phase === 'processing' && (
          <div className="p-10 flex flex-col items-center gap-5">
            <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center">
              <Loader2 className="text-blue-600 animate-spin" size={32} />
            </div>
            <div className="text-center space-y-1">
              <p className="font-semibold text-gray-900">Processing Payment...</p>
              <p className="text-xs text-gray-400">Calculating your risk-adjusted premium</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">Risk Engine</span>
              <span>→</span>
              <span className="px-2 py-0.5 rounded-full bg-gray-100">Payment</span>
              <span>→</span>
              <span className="px-2 py-0.5 rounded-full bg-gray-100">Activate</span>
            </div>
          </div>
        )}

        {/* ── Success ───────────────────────────────────────────────── */}
        {phase === 'success' && policy && (
          <div className="p-8 flex flex-col items-center gap-4 text-center">
            <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle className="text-green-500" size={44} strokeWidth={1.5} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Policy Activated!</h2>
              <p className="text-sm text-gray-500 mt-1">You are now protected for 7 days</p>
            </div>
            <div className="w-full bg-green-50 border border-green-200 rounded-xl p-4 space-y-2 text-sm text-left">
              <div className="flex justify-between">
                <span className="text-gray-500">Weekly premium</span>
                <span className="font-bold text-gray-900">₹{policy.weekly_premium?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Income protected</span>
                <span className="font-semibold text-green-700">₹{policy.coverage_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Expires</span>
                <span className="text-gray-700">
                  {new Date(policy.end_date).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata' })}
                </span>
              </div>
            </div>
            <button
              onClick={handleClose}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-xl transition"
            >
              Go to Dashboard
            </button>
          </div>
        )}

        {/* ── Error ─────────────────────────────────────────────────── */}
        {phase === 'error' && (
          <div className="p-8 flex flex-col items-center gap-4 text-center">
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
              <X className="text-red-500" size={32} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Activation Failed</h2>
              <p className="text-sm text-gray-500 mt-1">{errorMsg}</p>
            </div>
            <button
              onClick={handleClose}
              className="w-full border border-gray-200 text-gray-600 font-medium py-2.5 rounded-xl hover:bg-gray-50 transition"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
