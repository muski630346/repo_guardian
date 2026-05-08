const API = "http://localhost:8000"

export async function getDashboardData() {
  const res = await fetch(`${API}/dashboard`)
  return res.json()
}

export async function getActivities() {
  const res = await fetch(`${API}/activities`)
  return res.json()
}

export async function getFindings() {
  const res = await fetch(`${API}/findings`)
  return res.json()
}

export async function getAgentStatus() {
  const res = await fetch(`${API}/agent-status`)
  return res.json()
}

export async function getPRs() {
  const res = await fetch(`${API}/prs`)
  return res.json()
}