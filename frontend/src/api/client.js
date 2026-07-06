const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  let body = null;
  try {
    body = await res.json();
  } catch {
    // no body
  }
  if (!res.ok) {
    const err = new Error(body?.detail || `Request failed (${res.status})`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

export const api = {
  latestScan: () => request("/scans/latest/"),
  listScans: () => request("/scans/"),
  getScan: (id) => request(`/scans/${id}/`),
  getAccount: (id) => request(`/accounts/${id}/`),
  getDossier: (id) => request(`/accounts/${id}/dossier/`),
  runSampleScan: () => request("/scans/run_sample/", { method: "POST" }),
  uploadScan: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/scans/upload/", { method: "POST", body: form });
  },

  telegramHealth: () => request("/telegram/health/"),
  startTelegramScan: (targets) =>
    request("/telegram/scan/", { method: "POST", body: JSON.stringify({ targets }) }),
  getJob: (id) => request(`/jobs/${id}/`),

  listWatchlist: () => request("/watchlist/"),
  addWatch: (username) =>
    request("/watchlist/", { method: "POST", body: JSON.stringify({ username }) }),
  removeWatch: (id) => request(`/watchlist/${id}/`, { method: "DELETE" }),

  modelMetrics: () => request("/model/metrics/"),

  // Alerts
  listAlerts: (status) => request(`/alerts/${status ? `?status=${status}` : ''}`),
  acknowledgeAlert: (id) => request(`/alerts/${id}/acknowledge/`, { method: 'POST' }),
  dismissAlert: (id) => request(`/alerts/${id}/dismiss/`, { method: 'POST' }),
};
