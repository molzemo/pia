import { useEffect, useState } from 'react'
import { api } from '../api.js'

function formatValue(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export default function AgentDetail({ agent, onClose, onChanged }) {
  const [memory, setMemory] = useState([])
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    const [mem, act] = await Promise.all([
      api.getAgentMemory(agent.id),
      api.getAgentActivity(agent.id),
    ])
    setMemory(mem)
    setActivity(act)
    setLoading(false)
  }

  useEffect(() => { load() }, [agent.id])

  const removeKey = async (key) => {
    await api.deleteMemory(agent.id, key)
    load()
  }

  const toggleStatus = async () => {
    const next = agent.status === 'active' ? 'paused' : 'active'
    await api.updateAgentStatus(agent.id, next)
    onChanged()
  }

  const remove = async () => {
    if (!confirm(`Delete ${agent.name}? This removes its memory and history.`)) return
    await api.deleteAgent(agent.id)
    onChanged()
    onClose()
  }

  return (
    <div className="detail-panel">
      <div className="header">
        <h2>{agent.name}</h2>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      <div className="section">
        <h3>What it can do</h3>
        <div style={{ fontSize: 12.5 }}>
          <div>Status: <strong>{agent.status}</strong></div>
          <div>Type: <strong>{agent.kind === 'recurring' ? 'Recurring' : 'On-demand'}</strong></div>
          {agent.permissions?.budget_cap && <div>Spending limit: <strong>₹{agent.permissions.budget_cap}</strong></div>}
          {agent.permissions?.approval_required !== undefined && (
            <div>Requires your approval: <strong>{String(agent.permissions.approval_required)}</strong></div>
          )}
          {agent.schedule?.recurrence && (
            <div>Schedule: <strong>{agent.schedule.recurrence}{agent.schedule.day ? ` (${agent.schedule.day})` : ''}</strong></div>
          )}
        </div>
      </div>

      <div className="section">
        <h3>Memory ({memory.length})</h3>
        {loading && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading…</div>}
        {!loading && memory.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Nothing remembered yet.</div>}
        {memory.map((m) => (
          <div className="memory-row" key={m.key}>
            <span className="k">{m.key}</span>
            <span className="v">{formatValue(m.value)}</span>
            <button className="del" title="Forget this" onClick={() => removeKey(m.key)}>🗑</button>
          </div>
        ))}
      </div>

      <div className="section" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <h3>Activity timeline</h3>
      </div>
      <div className="timeline">
        {activity.map((a) => (
          <div className="timeline-item" key={a.id}>
            <div className="t">{new Date(a.created_at).toLocaleString()}</div>
            <div className="m">{a.message}</div>
          </div>
        ))}
      </div>

      <div className="agent-controls">
        <button onClick={toggleStatus}>{agent.status === 'active' ? '⏸ Pause' : '▶ Resume'}</button>
        <button className="danger" onClick={remove}>🗑 Delete</button>
      </div>
    </div>
  )
}
