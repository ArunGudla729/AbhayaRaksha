import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Shield } from 'lucide-react'

const CITIES = [
  { name: 'Mumbai', lat: 19.076, lng: 72.877 },
  { name: 'Delhi', lat: 28.613, lng: 77.209 },
  { name: 'Bangalore', lat: 12.972, lng: 77.594 },
  { name: 'Chennai', lat: 13.083, lng: 80.270 },
  { name: 'Hyderabad', lat: 17.385, lng: 78.487 },
  { name: 'Pune', lat: 18.520, lng: 73.856 },
]

export default function Register() {
  const [form, setForm] = useState({
    name: '', email: '', phone: '', password: '',
    worker_type: 'food_delivery', city: 'Mumbai',
    zone: 'Central', lat: 19.076, lng: 72.877,
    avg_daily_income: 800
  })
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleCityChange = e => {
    const city = CITIES.find(c => c.name === e.target.value)
    setForm({ ...form, city: city.name, lat: city.lat, lng: city.lng })
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/auth/register', { ...form, avg_daily_income: Number(form.avg_daily_income) })
      toast.success('Registered! Please login.')
      navigate('/login')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const field = (label, key, type = 'text', extra = {}) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        required
        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={form[key]}
        onChange={e => setForm({ ...form, [key]: e.target.value })}
        {...extra}
      />
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 to-indigo-800 py-8">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-lg">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="text-blue-600" size={32} />
          <div>
            <h1 className="text-2xl font-bold">Join AbhayaRaksha</h1>
            <p className="text-sm text-gray-500">Protect your weekly income</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {field('Full Name', 'name')}
            {field('Phone', 'phone', 'tel')}
          </div>
          {field('Email', 'email', 'email')}
          {field('Password', 'password', 'password')}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Worker Type</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={form.worker_type}
                onChange={e => setForm({ ...form, worker_type: e.target.value })}
              >
                <option value="food_delivery">Food Delivery (Zomato/Swiggy)</option>
                <option value="ecommerce">E-commerce (Amazon/Flipkart)</option>
                <option value="grocery">Grocery (Zepto/Blinkit)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={form.city}
                onChange={handleCityChange}
              >
                {CITIES.map(c => <option key={c.name}>{c.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {field('Delivery Zone', 'zone', 'text', { placeholder: 'e.g. Andheri West' })}
            {field('Avg Daily Income (₹)', 'avg_daily_income', 'number', { min: 200, max: 5000 })}
          </div>

          {/* Force Majeure terms — mandatory before account creation */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={termsAccepted}
              onChange={e => setTermsAccepted(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
            />
            <span className="text-xs text-gray-600 leading-relaxed group-hover:text-gray-800 transition">
              I agree to the AbhayaRaksha Policy Terms, including standard actuarial exclusions
              for <strong>War, Pandemics, and Nuclear Hazards</strong> as defined under Force Majeure.
            </span>
          </label>

          <button
            type="submit"
            disabled={loading || !termsAccepted}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already registered?{' '}
          <Link to="/login" className="text-blue-600 font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
