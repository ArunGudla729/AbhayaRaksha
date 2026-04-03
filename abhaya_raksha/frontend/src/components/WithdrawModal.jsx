import { useState, useEffect } from 'react'
import { CheckCircle, X, Loader2, Banknote } from 'lucide-react'
import api from '../api'

/**
 * WithdrawModal — simulates the UPI instant payout gateway flow.
 *
 * Props:
 *   claim    — the claim object (must have id, payout_amount, trigger_type)
 *   onClose  — called when the modal is dismissed; receives `true` if a
 *              successful withdrawal happened (so Dashboard can refresh)
 */
export default function WithdrawModal({ claim, onClose }) {
  // phase: 'confirm' | 'connecting' | 'verifying' | 'success' | 'error'
  const [phase, setPhase] = useState('confirm')
  const [txnId, setTxnId] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  // Lock body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const handleConfirm = async () => {
    setPhase('connecting')

    // Step 1 — "Connecting to UPI Gateway..." (2 s)
    await new Promise(r => setTimeout(r, 2000))
    setPhase('verifying')

    // Step 2 — "Verifying with Bank..." (1 s) then hit the real endpoint
    await new Promise(r => setTimeout(r, 1000))

    try {
      const res = await api.post(`/claims/${claim.id}/withdraw`)
      setTxnId(res.data.transaction_id)
      setPhase('success')
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Transfer failed. Please try again.')
      setPhase('error')
    }
  }

  const handleClose = () => {
    onClose(phase === 'success')
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) handleClose() }}
    >
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">

        {/* Close button — hidden during processing */}
        {(phase === 'confirm' || phase === 'success' || phase === 'error') && (
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        )}

        {/* ── Confirm phase ─────────────────────────────────────────── */}
        {phase === 'confirm' && (
          <div className="p-6 space-y-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 rounded-xl">
                <Banknote className="text-green-600" size={24} />
              </div>
              <div>
                <h2 className="font-bold text-gray-900 text-lg">Withdraw to UPI</h2>
                <p className="text-xs text-gray-500 capitalize">{claim.trigger_type} disruption payout</p>
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Payout amount</span>
                <span className="font-bold text-gray-900">₹{claim.payout_amount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Method</span>
                <span className="text-gray-700">UPI / Bank Transfer</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Processing time</span>
                <span className="text-green-600 font-medium">Instant</span>
              </div>
            </div>

            <p className="text-xs text-gray-400 text-center">
              The parametric payout has already been approved. This transfers it from
              your AbhayaRaksha wallet to your linked UPI account.
            </p>

            <div className="flex gap-3">
              <button
                onClick={handleClose}
                className="flex-1 border border-gray-200 text-gray-600 text-sm font-medium py-2.5 rounded-xl hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold py-2.5 rounded-xl transition"
              >
                Confirm Transfer
              </button>
            </div>
          </div>
        )}

        {/* ── Processing phases ──────────────────────────────────────── */}
        {(phase === 'connecting' || phase === 'verifying') && (
          <div className="p-10 flex flex-col items-center gap-5">
            <div className="relative">
              <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center">
                <Loader2 className="text-green-600 animate-spin" size={32} />
              </div>
            </div>
            <div className="text-center space-y-1">
              <p className="font-semibold text-gray-900">
                {phase === 'connecting' ? 'Connecting to UPI Gateway...' : 'Verifying with Bank...'}
              </p>
              <p className="text-xs text-gray-400">Please do not close this window</p>
            </div>
            {/* Step indicators */}
            <div className="flex items-center gap-2 text-xs">
              <span className={`px-2 py-0.5 rounded-full font-medium ${
                phase === 'connecting' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'
              }`}>
                1 Gateway
              </span>
              <span className="text-gray-300">→</span>
              <span className={`px-2 py-0.5 rounded-full font-medium ${
                phase === 'verifying' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'
              }`}>
                2 Bank
              </span>
              <span className="text-gray-300">→</span>
              <span className="px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-400">
                3 Transfer
              </span>
            </div>
          </div>
        )}

        {/* ── Success phase ──────────────────────────────────────────── */}
        {phase === 'success' && (
          <div className="p-8 flex flex-col items-center gap-4 text-center">
            {/* Animated green checkmark */}
            <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center animate-bounce-once">
              <CheckCircle className="text-green-500" size={44} strokeWidth={1.5} />
            </div>

            <div className="space-y-1">
              <h2 className="text-xl font-bold text-gray-900">Transfer Successful!</h2>
              <p className="text-sm text-gray-500">
                ₹{claim.payout_amount.toLocaleString()} sent to your UPI account
              </p>
            </div>

            <div className="w-full bg-green-50 border border-green-200 rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Transaction ID</span>
                <span className="font-mono font-semibold text-green-700">{txnId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Amount</span>
                <span className="font-bold text-gray-900">₹{claim.payout_amount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <span className="text-green-600 font-medium">Paid</span>
              </div>
            </div>

            <button
              onClick={handleClose}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-xl transition"
            >
              Done
            </button>
          </div>
        )}

        {/* ── Error phase ────────────────────────────────────────────── */}
        {phase === 'error' && (
          <div className="p-8 flex flex-col items-center gap-4 text-center">
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
              <X className="text-red-500" size={32} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Transfer Failed</h2>
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
