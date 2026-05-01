const API_BASE = "http://127.0.0.1:5000";
const STORAGE_KEY = "medtrack_user";

function getCurrentUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setCurrentUser(user) {
  if (user) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

async function apiRequest(path, options = {}) {
  const user = getCurrentUser();
  const headers = options.headers || {};
  if (user && user.id) {
    headers["X-User-Id"] = String(user.id);
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(API_BASE + path, { ...options, headers });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    const msg = data && data.error ? data.error : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function requireAuth(role) {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
    return null;
  }
  if (role && user.role !== role) {
    window.location.href = user.role === "caregiver" ? "caregiver.html" : "dashboard.html";
    return null;
  }
  return user;
}

function requirePatient() {
  return requireAuth("patient");
}

function requireCaregiver() {
  return requireAuth("caregiver");
}
