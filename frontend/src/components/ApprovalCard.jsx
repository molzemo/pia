import { useState } from 'react'
import { api } from '../api.js'

const CURRENCY = { INR: '₹' }

export default function ApprovalCard({ approval, onDecided }) {
  const [busy, setBusy] = useState(false)
  const [modifyOpen, setModifyOpen] = useState(false)
  const [modifyValue, setModifyValue] = useState(approval.amount)
  const symbol = CURRENCY[approval.cart?.currency] || '₹'

  const decide = async (decision, modifiedAmount) => {
    setBusy(true)
    try {
      const res = await api.decideApproval(approval.id, decision, modifiedAmount)
      onDecided(res.approval)
    } finally {
      setBusy(false)
    }
  }

  const items = approval.cart?.items || []
  const notes = approval.cart?.notes
  const isFinal = ['completed', 'rejected'].includes(approval.status)

  return (
    <div className="approval-card">
      <div className="head">
        <div>
          <div className="title">{approval.description}</div>
        </div>
        <div className="total">{symbol}{Number(approval.amount).toFixed(0)}</div>
      </div>
      <div className="body">
        {items.map((it, i) => (
          <div className="line" key={i}>
            <span>{it.item}{it.brand ? ` · ${it.brand}` : ''}{it.route ? ` · ${it.route}` : ''}</span>
            <span>{symbol}{Number(it.price).toFixed(0)}</span>
          </div>
        ))}
        {notes && <div className="notes">{notes}</div>}
      </div>
      {!isFinal && approval.status === 'pending' && (
        <div className="actions">
          <button className="reject" disabled={busy} onClick={() => decide('reject')}>Reject</button>
          <button disabled={busy} onClick={() => setModifyOpen((v) => !v)}>Modify</button>
          <button className="approve" disabled={busy} onClick={() => decide('approve')}>
            Approve &amp; Pay
          </button>
        </div>
      )}
      {modifyOpen && (
        <div className="actions" style={{ borderTop: 'none' }}>
          <input
            type="number"
            value={modifyValue}
            onChange={(e) => setModifyValue(e.target.value)}
            style={{ flex: 1, border: '1px solid var(--border)', borderRadius: 8, padding: '8px' }}
          />
          <button className="approve" disabled={busy} onClick={() => decide('modify', Number(modifyValue))}>
            Confirm amount &amp; Pay
          </button>
        </div>
      )}
      {isFinal && (
        <div className="actions" style={{ justifyContent: 'flex-start' }}>
          <span className={`status-pill ${approval.status}`}>{approval.status}</span>
        </div>
      )}
    </div>
  )
}
