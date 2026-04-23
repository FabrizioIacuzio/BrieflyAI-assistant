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

const emailListWrap    = $("emailList");
const controlsSection  = $("controlsSection");
const searchRow        = $("searchRow");
const searchInput      = $("searchInput");
const btnSelectAll     = $("btnSelectAll");
const btnClearAll      = $("btnClearAll");

const progressPanel    = $("progressPanel");
const progressSteps    = $("progressSteps");
const progressError    = $("progressError");
const btnBackToEmails  = $("btnBackToEmails");

const resultsPanel     = $("resultsPanel");
const audioPlayer      = $("audioPlayer");

// ── App state ─────────────────────────────────────────────────────────────────
let googleAccessToken = null;   // Google OAuth token (for Gmail API)
let brieflyToken = null;        // Briefly session token
let userProfile = {};           // { username, email, picture }
let allEmails = [];             // fetched email objects
let selectedIds = new Set();    // currently checked email IDs
let searchQuery = "";           // current search filter

// ── Avatar helpers ────────────────────────────────────────────────────────────
const AVATAR_COLORS = [
  "#3B82F6","#8B5CF6","#EC4899","#EF4444","#F59E0B",
  "#10B981","#06B6D4","#6366F1","#F97316","#84CC16",
];
function avatarColor(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}
function senderInitials(str) {
  const clean = str.replace(/<[^>]+>/g, "").replace(/["]/g, "").trim();
  const parts = clean.split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return clean.slice(0, 2).toUpperCase();
}

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

/**
 * Silently refresh the Briefly token using the cached Google token.
 * Returns true if successful, false if the user needs to re-login interactively.
 */
async function refreshBrieflyToken() {
  try {
    const gToken = await getGoogleToken(false);
    const data = await exchangeForBrieflyToken(gToken);
    googleAccessToken = gToken;
    brieflyToken = data.token;
    userProfile = { username: data.username, email: data.email, picture: data.picture };
    await saveSaved({ brieflyToken, userProfile });
    return true;
  } catch {
    return false;
  }
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
    fetchEmails();   // auto-load emails after sign-in
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
  searchQuery = "";
  searchInput.value = "";
  searchRow.style.display = "none";
  resultsPanel.style.display = "none";
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

function visibleEmails() {
  if (!searchQuery) return allEmails;
  const q = searchQuery.toLowerCase();
  return allEmails.filter(
    (e) =>
      (e.title || "").toLowerCase().includes(q) ||
      (e.source || "").toLowerCase().includes(q) ||
      (e.description || "").toLowerCase().includes(q)
  );
}

function renderEmailList() {
  if (allEmails.length === 0) {
    showFetchState("none");
    searchRow.style.display = "none";
    return;
  }
  showFetchState("results");
  searchRow.style.display = "block";

  const emails = visibleEmails();
  emailCount.textContent = searchQuery
    ? `${emails.length} of ${allEmails.length} emails`
    : `${allEmails.length} emails`;

  // Clear old rows (keep the count row)
  emailItems.querySelectorAll(".email-item").forEach((el) => el.remove());

  emails.forEach((email) => {
    const color = avatarColor(email.source || email.title || "?");
    const initials = senderInitials(email.source || "?");
    const row = document.createElement("div");
    row.className = "email-item" + (selectedIds.has(email.ID) ? " selected" : "");
    row.dataset.id = email.ID;
    row.innerHTML = `
      <div class="sender-avatar" style="--av-bg:${color}">
        <span class="av-initials">${escHtml(initials)}</span>
        <span class="av-check">✓</span>
      </div>
      <div class="email-body">
        <div class="email-subject-row">
          <span class="email-subject">${escHtml(email.title)}</span>
          <span class="email-date">${formatDate(email.publishedAt)}</span>
        </div>
        <div class="email-meta">${escHtml(email.source)}</div>
        <div class="email-preview">${escHtml(email.description)}</div>
      </div>`;

    row.addEventListener("click", () => {
      const checked = !selectedIds.has(email.ID);
      toggleSelect(email.ID, checked, row);
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
  selectedCount.textContent = n === 0 ? "0" : String(n);
  btnGenerate.disabled = n === 0;
  btnClearAll.style.display = n > 0 ? "inline" : "none";
  btnSelectAll.style.display = n === allEmails.length ? "none" : "inline";
}

function showGenerationView() {
  controlsSection.style.display = "none";
  emailListWrap.style.display = "none";
  generateBar.style.display = "none";
  progressPanel.style.display = "flex";
  resultsPanel.style.display = "none";
}

function showEmailView() {
  controlsSection.style.display = "block";
  emailListWrap.style.display = "flex";
  generateBar.style.display = "flex";
  progressPanel.style.display = "none";
  resultsPanel.style.display = "none";
}

// ── Briefing generation ────────────────────────────────────────────────────────
async function generate() {
  const articles = allEmails.filter((e) => selectedIds.has(e.ID));
  if (articles.length === 0) return;

  const duration = parseInt(durationSelect.value, 10);

  showGenerationView();
  setError(progressError, "");
  renderSteps(PIPELINE_STEPS.map((t) => ({ title: t, status: "pending" })));

  try {
    let res = await fetch(`${API}/briefings/generate-raw`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${brieflyToken}`,
      },
      body: JSON.stringify({ articles, duration_minutes: duration, voice_accent: "us" }),
    });

    // Token expired — try a silent refresh once
    if (res.status === 401) {
      const refreshed = await refreshBrieflyToken();
      if (!refreshed) throw new Error("Session expired. Please sign out and sign in again.");
      res = await fetch(`${API}/briefings/generate-raw`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${brieflyToken}`,
        },
        body: JSON.stringify({ articles, duration_minutes: duration, voice_accent: "us" }),
      });
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    const { job_id } = await res.json();

    await streamProgress(job_id);
  } catch (e) {
    setError(progressError, e.message);
    btnBackToEmails.style.display = "block";
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
        showBriefingResult(briefing_id);
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

async function showBriefingResult(briefingId) {
  progressPanel.style.display = "none";
  resultsPanel.style.display = "flex";

  const audioBase = API.replace(/\/api$/, "");
  audioPlayer.src = `${audioBase}/audio/briefing_${briefingId}.mp3?token=${encodeURIComponent(brieflyToken)}`;
  audioPlayer.play().catch(() => {});

  // Speed buttons
  resultsPanel.querySelectorAll(".speed-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      resultsPanel.querySelectorAll(".speed-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      audioPlayer.playbackRate = parseFloat(btn.dataset.rate);
    });
  });

  // Open app link — pass token + briefing ID so the web app logs in
  // automatically and opens the just-generated briefing directly.
  const appLink = $("openAppLink");
  const { frontend_url = "http://localhost:5173" } = chrome.runtime.getManifest();
  if (appLink) {
    const params = new URLSearchParams({
      token:       brieflyToken,
      username:    userProfile.username || userProfile.email || "User",
      email:       userProfile.email    || "",
      picture:     userProfile.picture  || "",
      briefing_id: String(briefingId),
    });
    appLink.href = `${frontend_url}/oauth-callback?${params.toString()}`;
  }

  // Fetch full briefing data
  try {
    const res = await fetch(`${API}/briefings/${briefingId}`, {
      headers: { Authorization: `Bearer ${brieflyToken}` },
    });
    if (!res.ok) return;
    const b = await res.json();
    renderBriefingData(b);
  } catch (_) {}
}

function renderBriefingData(b) {
  // Topics
  const clusters = b.clusters?.clusters || [];
  if (clusters.length) {
    const topicsSection = $("topicsSection");
    const topicsList = $("topicsList");
    topicsList.innerHTML = clusters
      .sort((a, z) => (a.priority || 99) - (z.priority || 99))
      .map((c) => `<span class="topic-chip">${escHtml(c.cluster_name)}</span>`)
      .join("");
    topicsSection.style.display = "block";
  }

  // Risk alerts
  const alerts = (b.analytics || []).filter((r) => r.urgency >= 8 || r.market_impact >= 8);
  if (alerts.length) {
    const riskAlert = $("riskAlert");
    const riskList = $("riskList");
    riskList.innerHTML = alerts
      .map((r) => `<div class="risk-item">· ${escHtml(r.one_line_summary)} <span style="opacity:.7">[U${r.urgency}/I${r.market_impact}]</span></div>`)
      .join("");
    riskAlert.style.display = "block";
  }

  // Analytics scores
  const analytics = b.analytics || [];
  if (analytics.length) {
    const analyticsSection = $("analyticsSection");
    const analyticsList = $("analyticsList");
    analyticsList.innerHTML = analytics.map((r) => {
      const cls = { Positive: "sent-positive", Neutral: "sent-neutral", Negative: "sent-negative" }[r.sentiment] || "sent-neutral";
      return `<div class="score-row">
        <span class="sentiment-badge ${cls}">${escHtml(r.sentiment)}</span>
        <span class="score-summary">${escHtml(r.one_line_summary || r.subject || "")}</span>
        <span class="score-meta">U${r.urgency}·I${r.market_impact}</span>
      </div>`;
    }).join("");
    analyticsSection.style.display = "block";
  }

  // Script
  if (b.script) {
    const scriptSection = $("scriptSection");
    const scriptText = $("scriptText");
    scriptText.textContent = b.script;
    scriptSection.style.display = "block";
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
    fetchEmails();   // auto-load emails on open
  } else {
    showLogin();
  }
}

// ── Event listeners ────────────────────────────────────────────────────────────
btnSignIn.addEventListener("click", signIn);
btnSignOut.addEventListener("click", signOut);
btnFetch.addEventListener("click", fetchEmails);
btnGenerate.addEventListener("click", generate);
btnBackToEmails.addEventListener("click", () => {
  btnBackToEmails.style.display = "none";
  setError(progressError, "");
  showEmailView();
});

$("btnNewBriefing").addEventListener("click", () => {
  audioPlayer.pause();
  audioPlayer.src = "";
  // Reset results sections
  ["topicsSection","analyticsSection","scriptSection","riskAlert"].forEach((id) => {
    $(id).style.display = "none";
  });
  showEmailView();
});

searchInput.addEventListener("input", () => {
  searchQuery = searchInput.value.trim();
  renderEmailList();
});

btnSelectAll.addEventListener("click", () => {
  visibleEmails().forEach((e) => selectedIds.add(e.ID));
  renderEmailList();
});

btnClearAll.addEventListener("click", () => {
  selectedIds.clear();
  renderEmailList();
});

btnGenerate.disabled = true;

// Kick off
init();
