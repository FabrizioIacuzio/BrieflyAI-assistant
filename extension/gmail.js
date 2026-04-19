/**
 * gmail.js — Gmail API helpers for the Briefly extension.
 *
 * All functions accept a Google OAuth access token and return plain JS objects.
 */

const GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me";

/** Low-level authenticated fetch. */
async function gfetch(token, path, params = {}) {
  const url = new URL(`${GMAIL_BASE}${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Gmail API error ${res.status}: ${await res.text()}`);
  return res.json();
}

/**
 * Fetch recent message IDs matching the given Gmail query.
 * Returns an array of { id, threadId }.
 */
export async function listMessages(token, query = "", maxResults = 50) {
  const data = await gfetch(token, "/messages", { q: query, maxResults });
  return data.messages || [];
}

/** Decode base64url to a UTF-8 string. */
function decodeBase64Url(str) {
  const base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  try {
    return decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
  } catch {
    return atob(base64);
  }
}

/** Recursively extract plain-text body from a MIME part tree. */
function extractBody(part) {
  if (!part) return "";
  if (part.mimeType === "text/plain" && part.body?.data) {
    return decodeBase64Url(part.body.data);
  }
  if (part.parts) {
    for (const p of part.parts) {
      const text = extractBody(p);
      if (text) return text;
    }
  }
  return "";
}

/** Get header value by name (case-insensitive). */
function header(headers, name) {
  return (
    headers.find((h) => h.name.toLowerCase() === name.toLowerCase())?.value ||
    ""
  );
}

/**
 * Fetch a single message and parse it into a Briefly article-shaped dict.
 * Returns null if the message can't be parsed.
 */
export async function fetchMessage(token, id) {
  try {
    const msg = await gfetch(token, `/messages/${id}`, { format: "full" });
    const hdrs = msg.payload?.headers || [];
    const subject = header(hdrs, "subject") || "(no subject)";
    const from = header(hdrs, "from") || "Unknown sender";
    const date = header(hdrs, "date") || "";
    const body = extractBody(msg.payload);

    return {
      ID: id,
      title: subject,
      description: body.slice(0, 400).replace(/\s+/g, " ").trim(),
      content: body.slice(0, 3000),
      source: from,
      publishedAt: date,
      url: `https://mail.google.com/mail/u/0/#inbox/${id}`,
    };
  } catch (e) {
    console.warn("fetchMessage failed for", id, e);
    return null;
  }
}

/**
 * High-level: list and fetch messages matching the query.
 * Returns an array of article-shaped objects.
 */
export async function fetchFinancialEmails(token, query, maxResults = 40) {
  const ids = await listMessages(token, query, maxResults);
  const results = await Promise.all(ids.map((m) => fetchMessage(token, m.id)));
  return results.filter(Boolean);
}

/**
 * Built-in query presets matching the web app's filter presets.
 */
export const QUERY_PRESETS = {
  All: "",
  "Bloomberg / Reuters": "from:(bloomberg.com OR reuters.com)",
  "Market Data": "subject:(market OR stocks OR equities OR bonds OR yield)",
  "Central Banks": "subject:(fed OR ecb OR boe OR monetary OR rate decision)",
  "Crypto": "subject:(bitcoin OR ethereum OR crypto OR defi OR blockchain)",
  "Macro": "subject:(gdp OR inflation OR cpi OR ppi OR unemployment OR macro)",
};
