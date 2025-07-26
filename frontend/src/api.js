// src/api.js

export async function api(path, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send + receive session cookie
  };

  const token = window.localStorage.getItem("apiKey");
  if (token) {
    opts.headers["Authorization"] = `Bearer ${token}`;
  }

  if (body !== null) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, opts);
  let parsed = null;
  try {
    parsed = await res.json();
  } catch {
  }

  if (!res.ok) {
    const msg = parsed?.msg || res.statusText || "Request failed";
    throw new Error(msg);
  }
  return parsed;
}
export const fetchJobs = ()=> api("/jobs");
export const fetchJobRuns= jobId => api(`/jobs/${jobId}/runs`);
export const fetchRunData = runId => api(`/results/${runId}`);

export async function downloadRun(runId, fmt = "csv") {
  const token = window.localStorage.getItem("apiKey");
  const headers = {};

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`/api/results/${runId}/download?fmt=${fmt}`, {
    credentials: "include",
    headers,
  });

  if (!res.ok) {
    throw new Error("Download failed");
  }

  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
