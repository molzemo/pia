import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function SettingsModal({ userEmail, onClose, onSaved }) {
  const [providers, setProviders] = useState({})
  const [provider, setProvider] = useState('anthropic')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [existingMasked, setExistingMasked] = useState(null)
  const [paymentRail, setPaymentRail] = useState('simulated_upi')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    (async () => {
      const [p, s] = await Promise.all([api.getProviders(), api.getSettings(userEmail)])
      setProviders(p)
      setProvider(s.llm_provider)
      setModel(s.llm_model)
      setExistingMasked(s.api_key_masked)
      setPaymentRail(s.payment_rail)
    })()
  }, [userEmail])

  const models = providers[provider]?.models || []

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await api.saveSettings(userEmail, {
        llm_provider: provider,
        llm_model: model,
        api_key: apiKey || undefined,
        payment_rail: paymentRail,
      })
      setExistingMasked(res.api_key_masked)
      setApiKey('')
      onSaved()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="m-head">
          <h2>Settings</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="m-body">
          <div className="field">
            <label>AI model provider</label>
            <select value={provider} onChange={(e) => { setProvider(e.target.value); setModel('') }}>
              {Object.entries(providers).map(([key, p]) => (
                <option key={key} value={key}>{p.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="">Select a model…</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>API key {existingMasked ? `(currently ${existingMasked})` : ''}</label>
            <input
              type="password"
              placeholder={existingMasked ? 'Enter a new key to replace it' : 'sk-...'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <div className="hint">
              Your key is encrypted at rest and never shown again after saving. It's used only to call
              your chosen model on your behalf — get one from
              {provider === 'anthropic' ? ' console.anthropic.com' : ' platform.openai.com'}.
            </div>
          </div>
          <div className="field">
            <label>Payment rail</label>
            <select value={paymentRail} onChange={(e) => setPaymentRail(e.target.value)}>
              <option value="simulated_upi">Simulated UPI (demo)</option>
            </select>
            <div className="hint">
              The platform never stores or sees your UPI PIN, card number or bank OTP. Payment
              authentication always happens inside the payment rail's own regulated flow — this demo
              rail simulates that handshake so you can see the full approve → pay → confirm loop.
            </div>
          </div>
          {error && <div className="hint" style={{ color: 'var(--red)' }}>{error}</div>}
        </div>
        <div className="m-actions">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={saving || !model} onClick={save}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
