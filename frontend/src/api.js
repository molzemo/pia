const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  let body = null
  try {
    body = await res.json()
  } catch {
    // no body
  }
  if (!res.ok) {
    const message = (body && body.detail) || res.statusText
    const err = new Error(message)
    err.status = res.status
    err.body = body
    throw err
  }
  return body
}

export const api = {
  health: () => request('/api/health'),

  sendChat: (userEmail, message) =>
    request('/api/chat', { method: 'POST', body: JSON.stringify({ user_email: userEmail, message }) }),

  getConversation: (userEmail) => request(`/api/conversation?user_email=${encodeURIComponent(userEmail)}`),

  listAgents: (userEmail) => request(`/api/agents?user_email=${encodeURIComponent(userEmail)}`),

  getAgentMemory: (agentId) => request(`/api/agents/${agentId}/memory`),

  getAgentActivity: (agentId) => request(`/api/agents/${agentId}/activity`),

  upsertMemory: (agentId, key, value) =>
    request(`/api/agents/${agentId}/memory/${encodeURIComponent(key)}`, { method: 'PUT', body: JSON.stringify({ value }) }),

  deleteMemory: (agentId, key) =>
    request(`/api/agents/${agentId}/memory/${encodeURIComponent(key)}`, { method: 'DELETE' }),

  updateAgentStatus: (agentId, status) =>
    request(`/api/agents/${agentId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  deleteAgent: (agentId) => request(`/api/agents/${agentId}`, { method: 'DELETE' }),

  listApprovals: (userEmail, status) =>
    request(`/api/approvals?user_email=${encodeURIComponent(userEmail)}${status ? `&status=${status}` : ''}`),

  decideApproval: (approvalId, decision, modifiedAmount) =>
    request(`/api/approvals/${approvalId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, modified_amount: modifiedAmount ?? null }),
    }),

  listActivity: (userEmail) => request(`/api/activity?user_email=${encodeURIComponent(userEmail)}`),

  getProviders: () => request('/api/settings/providers'),

  getSettings: (userEmail) => request(`/api/settings?user_email=${encodeURIComponent(userEmail)}`),

  saveSettings: (userEmail, payload) =>
    request('/api/settings', { method: 'POST', body: JSON.stringify({ user_email: userEmail, ...payload }) }),
}
