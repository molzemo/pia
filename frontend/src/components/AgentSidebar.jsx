const ICONS = { grocery: '🛒', taxi: '🚕', flight: '✈️', shopping: '🛍️' }

function summarize(agent) {
  if (agent.domain === 'grocery') {
    const budget = agent.permissions?.budget_cap
    return budget ? `Weekly · budget ₹${budget}` : 'Weekly grocery planning'
  }
  if (agent.domain === 'shopping') {
    const budget = agent.permissions?.budget_cap
    return budget ? `On request · budget ₹${budget}` : 'On-request shopping'
  }
  if (agent.domain === 'taxi') return 'Remembers your ride preferences'
  if (agent.domain === 'flight') return 'Remembers your flight preferences'
  return agent.kind
}

export default function AgentSidebar({ agents, selectedId, onSelect, onOpenSettings }) {
  return (
    <div className="sidebar">
      <div className="brand">
        <div className="logo">🤖</div>
        <div>
          <h1>Personal AI Ops</h1>
          <p>Ask once. Delegate permanently.</p>
        </div>
      </div>
      <div className="agent-list">
        {agents.length === 0 && (
          <div className="empty-hint">
            No agents yet. Just tell the assistant what you need — e.g. <em>"Plan groceries for the week, budget under ₹3,000"</em> or <em>"Book me a taxi to the airport"</em>. It will set up the right agent automatically.
          </div>
        )}
        {agents.map((a) => (
          <div
            key={a.id}
            className={`agent-card ${selectedId === a.id ? 'selected' : ''}`}
            onClick={() => onSelect(a.id)}
          >
            <div className="row">
              <div className="title"><span>{ICONS[a.domain] || '🔧'}</span>{a.name}</div>
              <span className={`badge ${a.status}`}>{a.status}</span>
            </div>
            <div className="sub">{summarize(a)}</div>
          </div>
        ))}
      </div>
      <div className="sidebar-footer">
        <button className="icon-btn" onClick={onOpenSettings}>⚙️ Settings</button>
      </div>
    </div>
  )
}
