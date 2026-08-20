import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import AgentSidebar from './components/AgentSidebar.jsx'
import AgentDetail from './components/AgentDetail.jsx'
import ApprovalCard from './components/ApprovalCard.jsx'
import SettingsModal from './components/SettingsModal.jsx'

const EXAMPLES = [
  'Plan groceries for this week, budget under ₹3,000',
  'Book me a taxi to the airport',
  'Find a flight to Mumbai under ₹15,000',
  'Add paneer and coffee to my grocery list',
]

function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('')
  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>Personal AI Ops</h1>
        <p className="tag">Ask once. Delegate permanently. Stay in control.</p>
        <div className="field">
          <label>Your email</label>
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && email && onLogin(email)}
          />
          <div className="hint">Demo sign-in — no password. This just identifies your agents.</div>
        </div>
        <button className="btn-primary" style={{ width: '100%', marginTop: 14 }} disabled={!email} onClick={() => onLogin(email)}>
          Continue
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('pia_email') || '')
  const [agents, setAgents] = useState([])
  const [selectedAgentId, setSelectedAgentId] = useState(null)
  const [messages, setMessages] = useState([]) // {role, content} | {role:'approval', approval}
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [needsSettings, setNeedsSettings] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  const login = (email) => {
    localStorage.setItem('pia_email', email)
    setUserEmail(email)
  }

  const refreshAgents = async () => {
    if (!userEmail) return
    const list = await api.listAgents(userEmail)
    setAgents(list)
  }

  const loadHistory = async () => {
    if (!userEmail) return
    const [convo, settings] = await Promise.all([api.getConversation(userEmail), api.getSettings(userEmail)])
    setMessages(convo.map((m) => ({ role: m.role, content: m.content })))
    setNeedsSettings(!settings.configured)
  }

  useEffect(() => {
    if (!userEmail) return
    refreshAgents()
    loadHistory()
  }, [userEmail])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || sending) return
    setInput('')
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setSending(true)
    try {
      const res = await api.sendChat(userEmail, message)
      setMessages((prev) => {
        const next = [...prev, { role: 'assistant', content: res.reply }]
        if (res.approval) next.push({ role: 'approval', approval: res.approval })
        return next
      })
      if (res.agent_action) refreshAgents()
    } catch (e) {
      if (e.status === 428) {
        setNeedsSettings(true)
        setShowSettings(true)
      } else {
        setError(e.message)
      }
    } finally {
      setSending(false)
    }
  }

  const selectedAgent = agents.find((a) => a.id === selectedAgentId)

  if (!userEmail) return <LoginScreen onLogin={login} />

  return (
    <div className="app-shell">
      <AgentSidebar
        agents={agents}
        selectedId={selectedAgentId}
        onSelect={(id) => setSelectedAgentId(id === selectedAgentId ? null : id)}
        onOpenSettings={() => setShowSettings(true)}
      />

      <div className="main">
        <div className="topbar">
          <strong style={{ fontSize: 14 }}>Chat with your Personal AI</strong>
          <span className="user-pill">{userEmail}</span>
        </div>

        {needsSettings && (
          <div className="banner">
            Add your AI model + API key to activate your agents. <button className="link" onClick={() => setShowSettings(true)}>Open Settings</button>
          </div>
        )}
        {error && <div className="banner" style={{ background: '#fbe7e9', borderColor: '#f3b3ba', color: '#8a2331' }}>{error}</div>}

        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="empty-hint">Say what you need in plain language — your AI will figure out which agent to create or update.</div>
          )}
          {messages.map((m, i) => {
            if (m.role === 'approval') {
              return (
                <div className="msg-row assistant" key={i}>
                  <ApprovalCard
                    approval={m.approval}
                    onDecided={(updated) => {
                      setMessages((prev) => prev.map((x) => (x.role === 'approval' && x.approval.id === updated.id ? { ...x, approval: updated } : x)))
                      refreshAgents()
                    }}
                  />
                </div>
              )
            }
            return (
              <div className={`msg-row ${m.role}`} key={i}>
                <div className="bubble">{m.content}</div>
              </div>
            )
          })}
          {sending && (
            <div className="msg-row assistant">
              <div className="bubble">Thinking…</div>
            </div>
          )}
        </div>

        {messages.length === 0 && (
          <div className="examples">
            {EXAMPLES.map((ex) => (
              <button className="example-chip" key={ex} onClick={() => send(ex)}>{ex}</button>
            ))}
          </div>
        )}

        <div className="composer">
          <input
            placeholder="Tell your AI what you need…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
          />
          <button className="send-btn" disabled={sending || !input.trim()} onClick={() => send()}>Send</button>
        </div>
      </div>

      {selectedAgent && (
        <AgentDetail agent={selectedAgent} onClose={() => setSelectedAgentId(null)} onChanged={refreshAgents} />
      )}

      {showSettings && (
        <SettingsModal
          userEmail={userEmail}
          onClose={() => setShowSettings(false)}
          onSaved={() => { setNeedsSettings(false); setShowSettings(false) }}
        />
      )}
    </div>
  )
}
