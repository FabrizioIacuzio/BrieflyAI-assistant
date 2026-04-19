/**
 * popup.js — Briefly AI Chrome extension popup logic.
 *
 * Flow:
 *   1. Check chrome.storage.local for a saved Briefly token.
 *   2. If none → show login screen.
 *   3. Login: chrome.identity.getAuthToken() → POST /api/auth/google-token → save token.
 *   4. Fetch emails from Gmail API using the Google access token.
 *   5. User selects emails + duration → POST /api/briefings/generate-raw.
 *   6. Stream SSE progress events.
 *   7. Play audio when done.
 */

import { fetchFinancialEmails, QUERY_PRESETS } from "./gmail.js";

/**
 * Backend URL — read from manifest so it's one place to change.
 * In development: set to http://localhost:8000/api in manifest.json > "backend_url".
 * In production:  set to https://your-domain.com/api
 */
const { backend_url: API = "http://localhost:8000/api" } =
  chrome.runtime.getManifest();

// ── DOM refs ───────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const loginScreen      = $("loginScreen");
const mainApp          = $("mainApp");
const btnSignIn        = $("btnSignIn");
const loginError       = $("loginError");

const userName         = $("userName");
const userEmail        = $("userEmail");
const avatarWrap       = $("avatarWrap");
const avatarInitial    = $("avatarInitial");
const btnSignOut       = $("btnSignOut");

const filterSelect     = $("filterSelect");
const btnFetch         = $("btnFetch");
const fetchError       = $("fetchError");

const emptyState       = $("emptyState");
const loadingState     = $("loadingState");
const emailItems       = $("emailItems");
const emailCount       = $("emailCount");
const noResultsState   = $("noResultsState");

const generateBar      = $("generateBar");
const selectedCount    = $("selectedCount");
const durationSelect   = $("durationSelect");
const btnGenerate      = $("btnGenerate");

const progressPanel    = $("progressPanel");
const progressSteps    = $("progressSteps");
const progressError    = $("progressError");

const audioPanel       = $("audioPanel");
const audioPlayer      = $("audioPlayer");

// ── App state ─────────────────────────────────────────────────────────────────
let googleAccessToken = null;   // Google OAuth token (for Gmail API)
let brieflyToken = null;        // Briefly session token
let userProfile = {};           // { username, email, picture }
let allEmails = [];             // fetched email objects
let selectedIds = new Set();    // currently checked email IDs

const PIPELINE_STEPS = [
  "Clustering & ranking emails",
  "Generating briefing script",
  "Synthesising audio",
  "Running AI analysis",
];

// ── Storage helpers ────────────────────────────────────────────────────────────
async function loadSaved() {
  return new Promise((resolve) =>
    chrome.storage.local.get(["brieflyToken", "userProfile"], resolve)
  );
}

async function saveSaved(data) {
  return new Promise((resolve) => chrome.storage.local.set(data, resolve));
}

async function clearSaved() {
  return new Promise((resolve) =>
    chrome.storage.local.remove(["brieflyToken", "userProfile"], resolve)
  );
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function showLogin() {
  loginScreen.style.display = "flex";
  mainApp.style.display = "none";
}

function showApp() {
  loginScreen.style.display = "none";
  mainApp.style.display = "flex";
}

function setUserUI(profile) {
  userName.textContent = profile.username || profile.email || "";
  userEmail.textContent = profile.email || "";
  if (profile.picture) {
    avatarWrap.innerHTML = `<img src="${profile.picture}" referrerpolicy="no-referrer" />`;
  } else {
    avatarInitial.textContent = (profile.username || profile.email || "?")[0].toUpperCase();
  }
}

function showFetchState(state) {
  // state: "empty" | "loading" | "results" | "none"
  emptyState.style.display      = state === "empty"   ? "flex" : "none";
  loadingState.style.display    = state === "loading" ? "flex" : "none";
  emailItems.style.display      = state === "results" ? "block" : "none";
  noResultsState.style.display  = state === "none"    ? "flex" : "none";
  generateBar.style.display     = state === "results" ? "flex" : "none";
}

function setError(el, msg) {
  if (msg) { el.textContent = msg; el.style.display = "block"; }
  else      { el.textContent = ""; el.style.display = "none"; }
}

// ── Auth ──────────────────────────────────────────────────────────────────────
/**
 * Get a Google OAuth access token via chrome.identity.getAuthToken.
 * This uses the oauth2 entry in manifest.json and handles the consent flow.
 */
async function getGoogleToken(interactive = true) {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive }, (token) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(token);
      }
    });
  });
}

/**
 * Exchange a Google access token for a Briefly session token.
 */
async function exchangeForBrieflyToken(googleToken) {
  const res = await fetch(`${API}/auth/google-token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ google_access_token: googleToken }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Backend error ${res.status}`);
  }
  return res.json(); // { token, username, email, picture }
}

async function signIn() {
  setError(loginError, "");
  btnSignIn.disabled = true;
  btnSignIn.textContent = "Signing in…";
  try {
    const gToken = await getGoogleToken(true);
    const data = await exchangeForBrieflyToken(gToken);

    // Keep Google token only in memory — never persist it to storage.
    // It's short-lived and Chrome will re-issue it silently when needed.
    googleAccessToken = gToken;
    brieflyToken = data.token;
    userProfile = { username: data.username, email: data.email, picture: data.picture };

    // Only persist the Briefly session token and profile (no Google token)
    await saveSaved({ brieflyToken, userProfile });
    setUserUI(userProfile);
    showApp();
  } catch (e) {
    setError(loginError, e.message);
  } finally {
    btnSignIn.disabled = false;
    btnSignIn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
        <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
        <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
        <path d="M3.964 10.707A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
        <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
      </svg>
      Sign in with Google`;
  }
}

async function signOut() {
  // Revoke cached Google token so next login shows consent screen
  if (googleAccessToken) {
    await new Promise((r) => chrome.identity.removeCachedAuthToken({ token: googleAccessToken }, r));
  }
  if (brieflyToken) {
    fetch(`${API}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${brieflyToken}` },
    }).catch(() => {});
  }
  await clearSaved();
  brieflyToken = null;
  googleAccessToken = null;
  userProfile = {};
  allEmails = [];
  selectedIds.clear();
  showFetchState("empty");
  setError(fetchError, "");
  audioPanel.style.display = "none";
  progressPanel.style.display = "none";
  showLogin();
}

// ── Email fetching ─────────────────────────────────────────────────────────────
async function fetchEmails() {
  setError(fetchError, "");
  showFetchState("loading");
  btnFetch.disabled = true;

  try {
    const preset = filterSelect.value;
    const query = QUERY_PRESETS[preset] ?? "";
    allEmails = await fetchFinancialEmails(googleAccessToken, query, 40);
    selectedIds.clear();
    renderEmailList();
  } catch (e) {
    // Google token may have expired — request a fresh one silently
    if (e.message.includes("401") || e.message.includes("invalid")) {
      try {
        googleAccessToken = await getGoogleToken(false);
        const preset = filterSelect.value;
        const query = QUERY_PRESETS[preset] ?? "";
        allEmails = await fetchFinancialEmails(googleAccessToken, query, 40);
        selectedIds.clear();
        renderEmailList();
        return;
      } catch (_) {}
    }
    showFetchState("empty");
    setError(fetchError, `Failed to fetch emails: ${e.message}`);
  } finally {
    btnFetch.disabled = false;
  }
}

function renderEmailList() {
  if (allEmails.length === 0) {
    showFetchState("none");
    return;
  }
  showFetchState("results");
  emailCount.textContent = `${allEmails.length} emails fetched`;

  // Clear old rows (keep the count div)
  const existing = emailItems.querySelectorAll(".email-item");
  existing.forEach((el) => el.remove());

  allEmails.forEach((email) => {
    const row = document.createElement("div");
    row.className = "email-item";
    row.dataset.id = email.ID;
    row.innerHTML = `
      <input type="checkbox" class="email-checkbox" data-id="${email.ID}" />
      <div class="email-body">
        <div class="email-subject">${escHtml(email.title)}</div>
        <div class="email-meta">${escHtml(email.source)} · ${formatDate(email.publishedAt)}</div>
        <div class="email-preview">${escHtml(email.description)}</div>
      </div>`;

    const cb = row.querySelector(".email-checkbox");
    cb.addEventListener("change", (e) => {
      e.stopPropagation();
      toggleSelect(email.ID, cb.checked, row);
    });
    row.addEventListener("click", (e) => {
      if (e.target === cb) return;
      cb.checked = !cb.checked;
      toggleSelect(email.ID, cb.checked, row);
    });
    emailItems.appendChild(row);
  });

  updateSelectedCount();
}

function toggleSelect(id, checked, row) {
  if (checked) {
    selectedIds.add(id);
    row.classList.add("selected");
  } else {
    selectedIds.delete(id);
    row.classList.remove("selected");
  }
  updateSelectedCount();
}

function updateSelectedCount() {
  const n = selectedIds.size;
  selectedCount.textContent = n === 0 ? "None selected" : `${n} selected`;
  btnGenerate.disabled = n === 0;
}

// ── Briefing generation ────────────────────────────────────────────────────────
async function generate() {
  const articles = allEmails.filter((e) => selectedIds.has(e.ID));
  if (articles.length === 0) return;

  const duration = parseInt(durationSelect.value, 10);

  // Switch to progress view
  generateBar.style.display = "none";
  progressPanel.style.display = "flex";
  audioPanel.style.display = "none";
  setError(progressError, "");
  renderSteps(PIPELINE_STEPS.map((t) => ({ title: t, status: "pending" })));

  try {
    // Start the job
    const res = await fetch(`${API}/briefings/generate-raw`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${brieflyToken}`,
      },
      body: JSON.stringify({ articles, duration_minutes: duration, voice_accent: "us" }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    const { job_id } = await res.json();

    // Stream SSE
    await streamProgress(job_id);
  } catch (e) {
    setError(progressError, e.message);
    generateBar.style.display = "flex";
    progressPanel.style.display = "none";
  }
}

function renderSteps(steps) {
  progressSteps.innerHTML = "";
  steps.forEach((s, i) => {
    const row = document.createElement("div");
    row.className = "step-row";
    row.id = `step-${i}`;
    row.innerHTML = `
      <div class="step-icon ${s.status}">${statusIcon(s.status)}</div>
      <div class="step-label ${s.status}">${escHtml(s.title)}</div>`;
    progressSteps.appendChild(row);
  });
}

function updateStep(index, status, title) {
  const row = $(`step-${index}`);
  if (!row) return;
  row.querySelector(".step-icon").className = `step-icon ${status}`;
  row.querySelector(".step-icon").textContent = statusIcon(status);
  row.querySelector(".step-label").className = `step-label ${status}`;
  if (title) row.querySelector(".step-label").textContent = title;
}

function statusIcon(s) {
  return { pending: "○", running: "◉", done: "✓", error: "✗" }[s] ?? "○";
}

async function streamProgress(jobId) {
  const url = `${API}/briefings/stream/${jobId}?token=${encodeURIComponent(brieflyToken)}`;
  const stepTitles = [...PIPELINE_STEPS];

  await new Promise((resolve, reject) => {
    const es = new EventSource(url);
    es.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }

      const { step, status, title, briefing_id, message } = data;

      if (step === "complete") {
        // Mark all pending as done
        stepTitles.forEach((_, i) => updateStep(i, "done"));
        es.close();
        showAudio(briefing_id);
        resolve();
        return;
      }

      if (step === "error") {
        es.close();
        reject(new Error(message || "Pipeline error"));
        return;
      }

      const idx = typeof step === "number" ? step : parseInt(step, 10);
      if (!isNaN(idx)) {
        updateStep(idx, status, title || stepTitles[idx]);
        if (status === "running") {
          // Mark previous steps done
          for (let i = 0; i < idx; i++) updateStep(i, "done");
        }
      }
    };
    es.onerror = () => {
      es.close();
      reject(new Error("Connection to backend lost"));
    };
  });
}

function showAudio(briefingId) {
  progressPanel.style.display = "none";
  audioPanel.style.display = "block";
  const audioBase = API.replace(/\/api$/, "");
  audioPlayer.src = `${audioBase}/audio/briefing_${briefingId}.mp3`;
  audioPlayer.play().catch(() => {});
  // Set "open full app" link from manifest so no localhost is hardcoded in HTML
  const appLink = document.getElementById("openAppLink");
  if (appLink) {
    const { frontend_url = "http://localhost:5173" } = chrome.runtime.getManifest();
    appLink.href = frontend_url;
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDate(str) {
  if (!str) return "";
  try {
    return new Date(str).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch { return str.slice(0, 10); }
}

// ── Init ───────────────────────────────────────────────────────────────────────
async function init() {
  const saved = await loadSaved();

  if (saved.brieflyToken) {
    brieflyToken = saved.brieflyToken;
    userProfile = saved.userProfile || {};
    // Re-request Google token silently (no UI shown, uses cached Chrome token)
    try {
      googleAccessToken = await getGoogleToken(false);
    } catch (_) {
      // If silent grant fails, user will need to re-authenticate on first fetch
    }
    setUserUI(userProfile);
    showApp();
  } else {
    showLogin();
  }
}

// ── Event listeners ────────────────────────────────────────────────────────────
btnSignIn.addEventListener("click", signIn);
btnSignOut.addEventListener("click", signOut);
btnFetch.addEventListener("click", fetchEmails);
btnGenerate.addEventListener("click", generate);

btnGenerate.disabled = true;

// Kick off
init();
