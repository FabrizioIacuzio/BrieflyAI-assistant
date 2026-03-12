import re
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from analytics import (
    analyze_emails_with_llm,
    create_market_impact_chart,
    create_sentiment_chart,
    create_urgency_market_chart,
    sentiment_badge_html,
)
from logic import process_reports_and_generate_audio
from rss_fetcher import fetch_live_emails

# ── Constants ──────────────────────────────────────────────────────────────────
FINANCIAL_SENDERS = {
    "Bloomberg", "Reuters", "FactSet", "Goldman Sachs",
    "CNBC", "BBC Business", "Yahoo Finance", "MarketWatch", "The Guardian",
}
FINANCIAL_KEYWORDS = [
    "Fed", "Market", "Earnings", "NVIDIA", "Crude", "Oil", "OPEC", "Inflation",
    "Rate", "ECB", "Rally", "Volatility", "Bond", "Yield", "Stock", "Revenue",
    "Analyst", "Investor", "Treasury", "Central Bank", "Shares", "Trading",
    "Energy", "Refinery", "Growth", "Economy", "Investment", "Equity", "GDP",
    "Recession", "S&P", "Nasdaq", "Dow", "Bitcoin", "Crypto", "Dollar",
    "Commodity", "Futures", "Hedge", "Interest", "Deficit", "Tariff",
]
FILTER_OPTIONS = [
    "Manual Selection",
    "Market Volatility",
    "Tech & AI Sector",
    "Bullish Sentiment",
    "Central Banks & Rates",
    "Global Energy",
    "Last 24 Hours",
    "Bloomberg / Reuters Only",
]
SENDER_COLORS = {
    "Bloomberg":    "#2563EB",
    "Reuters":      "#EA580C",
    "FactSet":      "#7C3AED",
    "CNBC":         "#059669",
    "BBC Business": "#DC2626",
    "Yahoo Finance":"#B45309",
    "MarketWatch":  "#0891B2",
    "The Guardian": "#1D4ED8",
    "Goldman Sachs":"#374151",
}

# Topic classification — ordered from most specific to most general
TOPIC_RULES = [
    ("AI & Tech",      r"NVIDIA|artificial intelligence|\bAI\b|Microsoft|chip|semiconductor|Apple|Google|Meta|OpenAI|cloud|software|tech"),
    ("Energy",         r"oil|OPEC|crude|gas|energy|refin|Brent|WTI|LNG|petroleum|barrel|OPEC\+"),
    ("Gold",           r"\bgold\b|precious metal|bullion"),
    ("Crypto",         r"bitcoin|ethereum|crypto|blockchain|DeFi|NFT|token"),
    ("Central Banks",  r"Fed|Federal Reserve|\brate\b|inflation|ECB|central bank|monetary|yield|treasury|hawkish|dovish|interest rate"),
    ("Equities",       r"stock|earnings|rally|S&P|Nasdaq|Dow|shares|IPO|dividend|equity|market cap"),
    ("Commodities",    r"commodity|commodities|copper|wheat|corn|silver|metal|grain"),
    ("Retail",         r"retail|consumer|e-commerce|foot traffic|store|shopper"),
    ("Macro",          r"GDP|recession|economy|employment|jobs|unemployment|debt|trade|tariff|deficit"),
    # Non-financial
    ("Shopping",       r"order|shipped|delivery|purchase|amazon|ebay|checkout|invoice|payment"),
    ("Social",         r"LinkedIn|Twitter|Facebook|Instagram|connection|follower|notification"),
    ("HR",             r"performance review|HR|human resources|feedback|self-assessment|360"),
    ("IT",             r"maintenance|VPN|password|software update|IT support|system|downtime"),
    ("Entertainment",  r"Spotify|Netflix|playlist|music|movie|series|podcast"),
    ("Utilities",      r"storage|bill|account|subscription|quota|alert"),
    ("Facilities",     r"building|HVAC|floor|meeting room|facilities|access"),
]

TOPIC_COLORS = {
    "AI & Tech":     ("#7C3AED", "#F5F3FF", "#DDD6FE"),
    "Energy":        ("#D97706", "#FFFBEB", "#FDE68A"),
    "Gold":          ("#B45309", "#FFFBEB", "#FDE68A"),
    "Crypto":        ("#F59E0B", "#FFFBEB", "#FDE68A"),
    "Central Banks": ("#0891B2", "#ECFEFF", "#A5F3FC"),
    "Equities":      ("#059669", "#ECFDF5", "#A7F3D0"),
    "Commodities":   ("#78716C", "#F5F5F4", "#D6D3D1"),
    "Retail":        ("#10B981", "#ECFDF5", "#A7F3D0"),
    "Macro":         ("#2563EB", "#EFF6FF", "#BFDBFE"),
    # noise — all neutral gray
    "Shopping":      ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "Social":        ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "HR":            ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "IT":            ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "Entertainment": ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "Utilities":     ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "Facilities":    ("#94A3B8", "#F8FAFC", "#E2E8F0"),
    "General":       ("#94A3B8", "#F8FAFC", "#E2E8F0"),
}


def get_email_type(row) -> str:
    """Return the most specific topic that matches this email's content."""
    combined = f"{row['Subject']} {row.get('Content', '')}"
    for topic, pattern in TOPIC_RULES:
        if re.search(pattern, combined, re.I):
            return topic
    return "General"


def type_pill(topic: str) -> str:
    color, bg, border = TOPIC_COLORS.get(topic, ("#94A3B8", "#F8FAFC", "#E2E8F0"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'border:1px solid {border};padding:2px 9px;border-radius:20px;'
        f'font-size:10.5px;font-weight:600;white-space:nowrap;">{topic}</span>'
    )

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Briefly AI",
    layout="wide",
    page_icon="B",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ─── Base ─────────────────────────────────── */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
.stApp { background: #F1F5F9; }
#stDecoration, [data-testid="stSidebarNav"], #MainMenu, footer { display: none !important; visibility: hidden !important; }
[data-testid="stHeader"] { background: transparent; border-bottom: none; }

/* ─── Sidebar ───────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0C1220 !important;
    border-right: 1px solid #1E293B !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] .stMarkdown p {
    color: #64748B !important;
    font-size: 12px !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: #475569 !important;
    font-size: 10.5px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    margin-bottom: 6px;
}
[data-testid="stSidebar"] .stRadio label {
    color: #94A3B8 !important;
    font-size: 13px !important;
    padding: 3px 0;
}
[data-testid="stSidebar"] hr { border-color: #1E293B !important; margin: 16px 0; }
[data-testid="stSidebar"] div.stButton > button {
    background: #1E293B !important;
    color: #94A3B8 !important;
    border: 1px solid #334155 !important;
    box-shadow: none !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 7px 14px !important;
    letter-spacing: 0;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background: #334155 !important;
    color: #E2E8F0 !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ─── Main content buttons ──────────────────── */
div.stButton > button {
    background: #2563EB !important;
    color: white !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 9px 20px !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.2) !important;
    transition: background 0.15s, box-shadow 0.15s, transform 0.1s !important;
}
div.stButton > button:hover {
    background: #1D4ED8 !important;
    box-shadow: 0 3px 10px rgba(37,99,235,0.3) !important;
    transform: translateY(-1px) !important;
}
div.stButton > button:disabled {
    background: #CBD5E1 !important;
    color: #94A3B8 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ─── Tabs ──────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: white;
    border-bottom: 1px solid #E2E8F0;
    border-radius: 12px 12px 0 0;
    padding: 0 !important;
    display: flex;
    justify-content: center;
    gap: 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stTabs [data-baseweb="tab"] {
    flex: 0 1 200px;
    justify-content: center;
    text-align: center !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: #64748B !important;
    padding: 15px 30px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
    border-radius: 0 !important;
    background: transparent !important;
    letter-spacing: 0.01em;
}
.stTabs [aria-selected="true"] {
    color: #2563EB !important;
    border-bottom-color: #2563EB !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: white;
    border-radius: 0 0 12px 12px;
    padding: 28px 28px 32px !important;
    border: 1px solid #E2E8F0;
    border-top: none;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ─── Expanders ─────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 9px !important;
    background: #FAFBFC !important;
    margin-bottom: 8px;
}
[data-testid="stExpander"] summary {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #1E293B !important;
    padding: 11px 16px !important;
}
[data-testid="stExpander"] summary:hover { background: #F1F5F9 !important; border-radius: 9px; }

/* ─── Misc ──────────────────────────────────── */
hr { border-color: #E2E8F0 !important; margin: 12px 0; }
input[type="checkbox"] { accent-color: #2563EB; }

/* ─── Pipeline pulse animation ──────────────── */
@keyframes pipPulse {
    0%, 100% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(37,99,235,0.4); }
    50%       { transform: scale(1.25); opacity: 0.8; box-shadow: 0 0 0 6px rgba(37,99,235,0); }
}
.pip-pulse {
    width: 11px; height: 11px;
    background: #2563EB; border-radius: 50%;
    animation: pipPulse 1.2s ease-in-out infinite;
}

/* ─── Archive cards ─────────────────────────── */
.arc-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 4px;
    transition: box-shadow 0.15s, border-color 0.15s;
}
.arc-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-color: #BFDBFE; }
.arc-card-featured { border-color: #BFDBFE; background: #F0F7FF; }
.arc-ts { font-size: 13px; font-weight: 600; color: #0F172A; }
.arc-sub { font-size: 12px; color: #94A3B8; margin-top: 2px; }
.arc-tags { margin: 10px 0 8px; }
.arc-tag {
    display: inline-block;
    background: #EFF6FF; color: #1D4ED8;
    border: 1px solid #BFDBFE;
    border-radius: 5px; padding: 2px 9px;
    font-size: 11px; font-weight: 500; margin: 2px 2px 0 0;
}

/* ─── Inbox rows ────────────────────────────── */
.inbox-divider { border: none; border-top: 1px solid #F1F5F9; margin: 0; }

/* ─── Ghost expand buttons (secondary type) ─── */
[data-testid="baseButton-secondary"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #CBD5E1 !important;
    box-shadow: none !important;
    padding: 3px 7px !important;
    font-size: 15px !important;
    font-weight: 300 !important;
    line-height: 1.2 !important;
    transform: none !important;
    min-height: 0 !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: #F1F5F9 !important;
    border-color: #E2E8F0 !important;
    color: #2563EB !important;
    transform: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "archive": [],
    "analytics_df": None,
    "latest_clusters": None,
    "latest_emails": None,
    "latest_script": None,
    "latest_audio_path": None,
    "_last_suggestion": None,
    "open_archive_idx": None,
    "open_email_id": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ────────────────────────────────────────────────────────────────────
def is_financial(row) -> bool:
    if row["Sender"] in FINANCIAL_SENDERS:
        return True
    combined = f"{row['Subject']} {row.get('Content', '')}".lower()
    return any(kw.lower() in combined for kw in FINANCIAL_KEYWORDS)


def filter_auto_select(row, suggestion: str, max_date: str) -> bool:
    def m(text, pat):
        return bool(re.search(pat, str(text), re.I))
    if suggestion == "Manual Selection":          return False
    if suggestion == "Market Volatility":         return m(row["Subject"], r"Surge|Rally|Crash|Volatility|Shock|Plunge|Soar")
    if suggestion == "Tech & AI Sector":          return m(row["Subject"], r"NVIDIA|AI|Microsoft|Chips|Tech|Semiconductor|Apple|Google|Meta|OpenAI")
    if suggestion == "Bullish Sentiment":         return m(row.get("Content", ""), r"Growth|Higher|Positive|Upward|Gain|Bull|Rise|Record")
    if suggestion == "Central Banks & Rates":     return m(row["Subject"], r"Fed|Rate|Inflation|ECB|Central Bank|Monetary|Yield|Treasury|Hawkish|Dovish")
    if suggestion == "Global Energy":             return m(row["Subject"], r"Oil|OPEC|Energy|Crude|Gas|Refin|Brent|WTI|LNG")
    if suggestion == "Last 24 Hours":             return str(row["Date"]) == max_date
    if suggestion == "Bloomberg / Reuters Only":  return row["Sender"] in ("Bloomberg", "Reuters")
    return False


def sender_pill(sender: str) -> str:
    c = SENDER_COLORS.get(sender, "#64748B")
    return (f'<span style="display:inline-block;background:{c}14;color:{c};'
            f'border:1px solid {c}28;padding:1px 8px;border-radius:20px;'
            f'font-size:11px;font-weight:600;white-space:nowrap;">{sender}</span>')


def topic_pill(t: str) -> str:
    """Blue pill for cluster/topic tags (used in briefing metadata and archive)."""
    return (f'<span style="display:inline-block;background:#EFF6FF;color:#1D4ED8;'
            f'border:1px solid #BFDBFE;border-radius:5px;padding:2px 9px;'
            f'font-size:11px;font-weight:500;margin:2px 2px 0 0;">{t}</span>')


def email_detail_html(row) -> str:
    """Render a full email reading pane as HTML."""
    email_tp  = get_email_type(row)
    is_fin    = bool(row.get("Is_Financial", False))
    content   = str(row.get("Content", "")).strip() or "No content available."
    url       = str(row.get("URL", "")).strip()

    accent = "#2563EB" if is_fin else "#94A3B8"
    paragraphs = "".join(
        f'<p style="margin:0 0 14px 0;">{p.strip()}</p>'
        for p in content.split("  ") if p.strip()
    ) or f'<p style="margin:0;">{content}</p>'

    url_html = (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block;margin-top:18px;font-size:12.5px;color:#2563EB;'
        f'text-decoration:none;font-weight:500;border-bottom:1px solid #BFDBFE;padding-bottom:1px;">'
        f'Read original article →</a>'
    ) if url else ""

    return (
        f'<div style="background:white;border:1px solid #E2E8F0;border-radius:11px;'
        f'padding:22px 26px;margin:2px 0 10px;box-shadow:0 2px 10px rgba(0,0,0,0.06);'
        f'border-left:3px solid {accent};">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">'
        f'<div style="display:flex;gap:7px;align-items:center;flex-wrap:wrap;">'
        f'{sender_pill(str(row["Sender"]))}&nbsp;{type_pill(email_tp)}'
        f'</div>'
        f'<span style="font-size:12px;color:#94A3B8;white-space:nowrap;padding-top:2px;">{row["Date"]}</span>'
        f'</div>'
        f'<div style="font-size:17px;font-weight:700;color:#0F172A;line-height:1.35;margin-bottom:16px;">'
        f'{row["Subject"]}'
        f'</div>'
        f'<div style="border-top:1px solid #F1F5F9;padding-top:16px;'
        f'font-size:14px;color:#334155;line-height:1.8;">'
        f'{paragraphs}'
        f'</div>'
        f'{url_html}'
        f'</div>'
    )


def kpi_card(value, label: str, color: str = "#2563EB") -> str:
    return (
        f'<div style="background:white;border-radius:11px;padding:18px 20px;'
        f'border:1px solid #E2E8F0;box-shadow:0 1px 3px rgba(0,0,0,0.05);'
        f'min-height:88px;display:flex;flex-direction:column;justify-content:center;">'
        f'<div style="font-size:26px;font-weight:700;color:{color};line-height:1;">{value}</div>'
        f'<div style="font-size:11px;font-weight:600;color:#94A3B8;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-top:6px;">{label}</div></div>'
    )


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _load_rss():
    return fetch_live_emails(max_per_feed=4)


@st.cache_data(show_spinner=False)
def _load_csv():
    try:
        return pd.read_csv("data.csv")
    except FileNotFoundError:
        return None


def get_data():
    rss_df = _load_rss()
    csv_df = _load_csv()
    if rss_df is not None and len(rss_df) > 0:
        if csv_df is not None and len(csv_df) > 0:
            combined = pd.concat([rss_df, csv_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["Subject"]).reset_index(drop=True)
            combined = combined.sort_values(["Date", "ID"], ascending=[False, True]).reset_index(drop=True)
            return combined
        return rss_df
    return csv_df


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:6px 0 20px;">
        <div style="font-size:20px;font-weight:700;color:#F8FAFC;letter-spacing:-0.3px;">
            Briefly <span style="color:#60A5FA;">AI</span>
        </div>
        <div style="font-size:11px;color:#475569;margin-top:3px;">Financial Briefing Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Smart Filters**")
    suggestion = st.radio("filter", FILTER_OPTIONS, label_visibility="collapsed")

    st.divider()
    st.markdown("**Briefing Length**")
    duration_minutes = st.radio(
        "duration",
        [1, 3, 5],
        format_func=lambda x: f"{x} minute{'s' if x > 1 else ''}",
        index=1,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Refresh Feed", use_container_width=True):
        st.cache_data.clear()
        for k in list(st.session_state.keys()):
            if k.startswith("sel_"):
                del st.session_state[k]
        st.session_state["_last_suggestion"] = None
        st.rerun()

    st.markdown(
        '<div style="font-size:10px;color:#334155;text-align:center;margin-top:24px;">Powered by Groq · gTTS</div>',
        unsafe_allow_html=True,
    )


# ── Load & prepare data ────────────────────────────────────────────────────────
with st.spinner("Loading feed…"):
    df = get_data()

if df is None:
    st.error("No data available. Run `python setup_data.py` to generate sample data.")
    st.stop()

df["Is_Financial"] = df.apply(is_financial, axis=1)
max_date = str(df["Date"].max())

if st.session_state["_last_suggestion"] != suggestion:
    for k in list(st.session_state.keys()):
        if k.startswith("sel_"):
            del st.session_state[k]
    st.session_state["_last_suggestion"] = suggestion

fin_count     = int(df["Is_Financial"].sum())
noise_count   = int((~df["Is_Financial"]).sum())
archive_count = len(st.session_state.archive)


# ── Page header ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:14px 0 6px;">
    <h1 style="margin:0;font-size:28px;font-weight:700;color:#0F172A;letter-spacing:-0.5px;">
        Briefly <span style="color:#2563EB;">AI</span>
    </h1>
    <p style="margin:5px 0 0;color:#64748B;font-size:13.5px;">
        AI-powered financial briefings — synthesised in seconds
    </p>
</div>
""", unsafe_allow_html=True)

# KPI row — 3 cards rendered in one HTML block so heights always match
st.markdown(
    f'<div style="display:flex;gap:16px;justify-content:center;margin:10px 0 4px;">'
    f'<div style="flex:1;max-width:210px;">{kpi_card(fin_count,     "Financial Reports", "#2563EB")}</div>'
    f'<div style="flex:1;max-width:210px;">{kpi_card(noise_count,   "Other Emails",      "#64748B")}</div>'
    f'<div style="flex:1;max-width:210px;">{kpi_card(archive_count, "Saved Briefings",   "#2563EB")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_inbox, tab_analytics, tab_archive = st.tabs(["Inbox", "Analytics", "Archive"])


# ══════════════════════════════════════════════════════════════════════════════
# INBOX
# ══════════════════════════════════════════════════════════════════════════════
with tab_inbox:

    # Sub-header
    top_l, top_r = st.columns([4, 1])
    top_l.markdown(
        f'<p style="font-size:13px;color:#64748B;margin:0 0 14px;">'
        f'<strong style="color:#0F172A;">{len(df)}</strong> emails &nbsp;·&nbsp; '
        f'<strong style="color:#2563EB;">{fin_count}</strong> financial reports</p>',
        unsafe_allow_html=True,
    )
    sel_slot = top_r.empty()

    # Column headers
    _ind, h0, h1, h2, h3, h4, h5 = st.columns([0.008, 0.04, 0.17, 0.49, 0.10, 0.13, 0.055])
    for col, lbl in zip([h1, h2, h3, h4], ["Source", "Subject", "Date", "Type"]):
        col.markdown(
            f'<div style="font-size:10.5px;font-weight:700;color:#94A3B8;'
            f'text-transform:uppercase;letter-spacing:0.08em;padding-bottom:6px;">{lbl}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('<hr style="margin:0 0 4px;border-color:#E2E8F0;">', unsafe_allow_html=True)

    # Email rows
    selected_rows = []
    for _, row in df.iterrows():
        rid      = row["ID"]
        is_fin   = bool(row["Is_Financial"])
        email_tp = get_email_type(row)
        is_open  = st.session_state["open_email_id"] == rid

        c_ind, c0, c1, c2, c3, c4, c5 = st.columns([0.008, 0.04, 0.17, 0.49, 0.10, 0.13, 0.055])

        # Left accent strip — thicker + brighter when the email is open
        with c_ind:
            bar_color = "#2563EB" if is_fin else "transparent"
            bar_width = "4px" if is_open else "3px"
            st.markdown(
                f'<div style="width:{bar_width};background:{bar_color};min-height:34px;'
                f'border-radius:0 2px 2px 0;margin-top:3px;opacity:{"1" if is_open else "0.6"};"></div>',
                unsafe_allow_html=True,
            )

        with c0:
            if is_fin:
                key = f"sel_{rid}"
                if key not in st.session_state:
                    st.session_state[key] = filter_auto_select(row, suggestion, max_date)
                if st.checkbox("", key=key, label_visibility="collapsed"):
                    selected_rows.append(row)
            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)

        with c1:
            st.markdown(sender_pill(str(row["Sender"])), unsafe_allow_html=True)

        with c2:
            weight = "600" if is_fin else "400"
            color  = "#0F172A" if is_fin else "#94A3B8"
            st.markdown(
                f'<span style="font-size:13.5px;font-weight:{weight};color:{color};">'
                f'{row["Subject"]}</span>',
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                f'<span style="font-size:12px;color:#94A3B8;">{row["Date"]}</span>',
                unsafe_allow_html=True,
            )

        with c4:
            st.markdown(type_pill(email_tp), unsafe_allow_html=True)

        with c5:
            icon = "▼" if is_open else "›"
            if st.button(icon, key=f"open_{rid}", type="secondary"):
                st.session_state["open_email_id"] = None if is_open else rid
                st.rerun()

        st.markdown('<hr class="inbox-divider">', unsafe_allow_html=True)

        # ── Inline reading pane ──────────────────────────────────────────────
        if is_open:
            st.markdown(email_detail_html(row), unsafe_allow_html=True)

    # Selection counter
    n_sel = len(selected_rows)
    sel_slot.markdown(
        f'<div style="text-align:right;font-size:13px;color:#2563EB;font-weight:600;">'
        f'{n_sel} selected</div>',
        unsafe_allow_html=True,
    )

    selected_df = pd.DataFrame(selected_rows) if selected_rows else pd.DataFrame()
    has_sel     = len(selected_df) > 0

    st.markdown("<br>", unsafe_allow_html=True)
    btn_col, hint_col = st.columns([2, 4])
    with btn_col:
        gen_clicked = st.button("Generate Audio Brief", disabled=not has_sel, use_container_width=True)
    with hint_col:
        if not has_sel:
            st.markdown(
                '<p style="color:#94A3B8;font-size:13px;padding-top:10px;">Select at least one financial email above.</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p style="color:#64748B;font-size:13px;padding-top:10px;">'
                f'{n_sel} report{"s" if n_sel > 1 else ""} selected &nbsp;·&nbsp; {duration_minutes}-minute briefing</p>',
                unsafe_allow_html=True,
            )

    # ── Pipeline ───────────────────────────────────────────────────────────────
    if gen_clicked and has_sel:

        PIPELINE_STEPS = [
            ("Clustering & ranking emails",  "Grouping your reports into thematic clusters by importance"),
            ("Generating briefing script",   f"Writing a {duration_minutes}-minute broadcast narrative"),
            ("Synthesising audio",           "Converting the script to speech via gTTS"),
            ("Running AI analysis",          "Scoring sentiment, urgency and market impact per article"),
        ]

        def _pipeline_html(active: int, done: set, error: bool = False) -> str:
            steps_html = ""
            for i, (title, desc) in enumerate(PIPELINE_STEPS):
                is_done   = i in done
                is_active = i == active and not error
                is_error  = i == active and error

                if is_error:
                    icon = ('<div style="width:32px;height:32px;min-width:32px;background:#FEF2F2;'
                            'border-radius:50%;display:flex;align-items:center;justify-content:center;'
                            'font-size:14px;color:#DC2626;">✕</div>')
                    t_col, d_col = "#DC2626", "#FCA5A5"
                    badge = ('<span style="background:#FEF2F2;color:#DC2626;padding:2px 10px;'
                             'border-radius:20px;font-size:11px;font-weight:600;">Error</span>')
                    opacity = "1"
                elif is_done:
                    icon = ('<div style="width:32px;height:32px;min-width:32px;background:#ECFDF5;'
                            'border-radius:50%;display:flex;align-items:center;justify-content:center;'
                            'font-size:15px;color:#059669;">✓</div>')
                    t_col, d_col = "#0F172A", "#64748B"
                    badge = ('<span style="background:#ECFDF5;color:#059669;padding:2px 10px;'
                             'border-radius:20px;font-size:11px;font-weight:600;">Done</span>')
                    opacity = "1"
                elif is_active:
                    icon = ('<div style="width:32px;height:32px;min-width:32px;background:#EFF6FF;'
                            'border-radius:50%;display:flex;align-items:center;justify-content:center;">'
                            '<div class="pip-pulse"></div></div>')
                    t_col, d_col = "#0F172A", "#64748B"
                    badge = ('<span style="background:#EFF6FF;color:#2563EB;padding:2px 10px;'
                             'border-radius:20px;font-size:11px;font-weight:600;">Running…</span>')
                    opacity = "1"
                else:
                    icon = ('<div style="width:32px;height:32px;min-width:32px;background:#F8FAFC;'
                            'border-radius:50%;display:flex;align-items:center;justify-content:center;">'
                            '<div style="width:8px;height:8px;background:#CBD5E1;border-radius:50%;"></div></div>')
                    t_col, d_col = "#94A3B8", "#CBD5E1"
                    badge = ""
                    opacity = "0.5"

                connector = ""
                if i < len(PIPELINE_STEPS) - 1:
                    line_col = "#A7F3D0" if i in done else "#E2E8F0"
                    connector = (f'<div style="width:2px;height:18px;background:{line_col};'
                                 f'margin:3px 0 3px 15px;border-radius:1px;"></div>')

                # Build each step as a compact single-line string (no newlines → no markdown interference)
                steps_html += (
                    f'<div style="opacity:{opacity};">'
                    f'<div style="display:flex;align-items:center;gap:14px;">'
                    f'<div style="display:flex;flex-direction:column;align-items:center;">{icon}</div>'
                    f'<div style="flex:1;">'
                    f'<div style="font-size:14px;font-weight:600;color:{t_col};line-height:1.3;">{title}</div>'
                    f'<div style="font-size:12px;color:{d_col};margin-top:2px;">{desc}</div>'
                    f'</div>'
                    f'<div style="white-space:nowrap;">{badge}</div>'
                    f'</div>'
                    f'{connector}'
                    f'</div>'
                )

            title_label = "Pipeline error" if error else ("Briefing ready ✓" if done == {0,1,2,3} else "AI Pipeline running…")
            title_color = "#DC2626" if error else ("#059669" if done == {0,1,2,3} else "#2563EB")
            return (
                f'<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;'
                f'padding:20px 24px;margin:8px 0 20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
                f'<div style="font-size:11px;font-weight:700;color:{title_color};'
                f'text-transform:uppercase;letter-spacing:0.09em;margin-bottom:16px;">{title_label}</div>'
                f'{steps_html}'
                f'</div>'
            )

        pipeline_ph = st.empty()
        pipeline_ph.markdown(_pipeline_html(0, set()), unsafe_allow_html=True)

        try:
            script, audio_path, clusters_data = process_reports_and_generate_audio(
                selected_df, duration_minutes
            )
            # Animate steps 1 and 2 completing after the main LLM call
            pipeline_ph.markdown(_pipeline_html(1, {0}), unsafe_allow_html=True)
            time.sleep(0.35)
            pipeline_ph.markdown(_pipeline_html(2, {0, 1}), unsafe_allow_html=True)
            time.sleep(0.35)
            pipeline_ph.markdown(_pipeline_html(3, {0, 1, 2}), unsafe_allow_html=True)

            analytics_df = analyze_emails_with_llm(selected_df)
            pipeline_ph.markdown(_pipeline_html(-1, {0, 1, 2, 3}), unsafe_allow_html=True)

            st.session_state.analytics_df      = analytics_df
            st.session_state.latest_clusters   = clusters_data
            st.session_state.latest_emails     = selected_df.copy()
            st.session_state.latest_script     = script
            st.session_state.latest_audio_path = audio_path

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            st.session_state.archive.insert(0, {
                "timestamp":        datetime.now(),
                "script":           script,
                "audio_bytes":      audio_bytes,
                "sources_count":    len(selected_df),
                "filter_used":      suggestion,
                "duration_minutes": duration_minutes,
                "clusters":         clusters_data,
                "analytics_df":     analytics_df,
                "emails_df":        selected_df.copy(),
            })

        except Exception as exc:
            pipeline_ph.markdown(_pipeline_html(0, set(), error=True), unsafe_allow_html=True)
            st.error(f"Error: {exc}")
            st.stop()

    # ── Latest result (persists via session state) ─────────────────────────────
    if st.session_state.latest_script:
        st.markdown(
            '<hr style="margin:24px 0 20px;border-color:#E2E8F0;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="font-size:12px;font-weight:700;color:#94A3B8;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:14px;">Latest Briefing</p>',
            unsafe_allow_html=True,
        )

        st.audio(st.session_state.latest_audio_path)
        st.markdown("<br>", unsafe_allow_html=True)

        sc_col, meta_col = st.columns([3, 1])
        with sc_col:
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#94A3B8;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Script</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;'
                f'padding:18px 20px;font-size:14px;color:#1E293B;line-height:1.75;">'
                f'{st.session_state.latest_script}</div>',
                unsafe_allow_html=True,
            )
        with meta_col:
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#94A3B8;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Topics</p>',
                unsafe_allow_html=True,
            )
            clusters = st.session_state.latest_clusters or {}
            for c in sorted(clusters.get("clusters", []), key=lambda x: x.get("priority", 99)):
                st.markdown(topic_pill(c["cluster_name"]), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:12px;color:#64748B;line-height:2;">'
                f'<strong style="color:#0F172A;">Filter:</strong>&nbsp; {suggestion}<br>'
                f'<strong style="color:#0F172A;">Duration:</strong>&nbsp; {duration_minutes} min<br>'
                f'<strong style="color:#0F172A;">Generated:</strong>&nbsp; {datetime.now().strftime("%H:%M")}'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="margin-top:16px;padding:11px 16px;background:#EFF6FF;'
            'border-radius:7px;border-left:3px solid #2563EB;font-size:13px;color:#1D4ED8;">'
            'Switch to the <strong>Analytics</strong> tab to explore sentiment scores and market impact charts.'
            '</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    adf = st.session_state.analytics_df
    edf = st.session_state.latest_emails

    if adf is None or (isinstance(adf, pd.DataFrame) and adf.empty):
        st.markdown("""
        <div style="text-align:center;padding:72px 20px;">
            <div style="font-size:40px;font-weight:700;color:#E2E8F0;margin-bottom:16px;">—</div>
            <h3 style="color:#1E293B;font-weight:600;margin-bottom:10px;font-size:18px;">No analysis yet</h3>
            <p style="color:#64748B;max-width:380px;margin:0 auto;font-size:14px;line-height:1.6;">
                Select financial emails in the <strong>Inbox</strong> tab and click
                <strong>Generate Audio Brief</strong> to unlock AI-powered sentiment
                scores, urgency ratings, and market impact charts.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # KPI strip
        pos = int((adf["sentiment"] == "Positive").sum())
        neu = int((adf["sentiment"] == "Neutral").sum())
        neg = int((adf["sentiment"] == "Negative").sum())
        avg_impact  = float(adf["market_impact"].mean())
        avg_urgency = float(adf["urgency"].mean())

        a1, a2, a3, a4, a5 = st.columns(5)
        a1.markdown(kpi_card(pos,                     "Positive",     "#059669"), unsafe_allow_html=True)
        a2.markdown(kpi_card(neu,                     "Neutral",      "#D97706"), unsafe_allow_html=True)
        a3.markdown(kpi_card(neg,                     "Negative",     "#DC2626"), unsafe_allow_html=True)
        a4.markdown(kpi_card(f"{avg_impact:.1f}/10",  "Avg Impact",   "#2563EB"), unsafe_allow_html=True)
        a5.markdown(kpi_card(f"{avg_urgency:.1f}/10", "Avg Urgency",  "#7C3AED"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Score legend ───────────────────────────────────────────────────────
        with st.expander("How are these scores calculated?", expanded=False):
            st.markdown("""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 24px;padding:4px 0 8px;">

<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;padding:14px 16px;">
<div style="font-size:12px;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Sentiment &nbsp;·&nbsp; Positive / Neutral / Negative</div>
<div style="font-size:13px;color:#374151;line-height:1.6;">The overall tone of the article towards financial markets. The model reads the subject and body and classifies the article as <strong>Positive</strong> (market-constructive), <strong>Negative</strong> (risk-off / bearish), or <strong>Neutral</strong>.</div>
</div>

<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;padding:14px 16px;">
<div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Sentiment Score &nbsp;·&nbsp; −1.0 to +1.0</div>
<div style="font-size:13px;color:#374151;line-height:1.6;">A continuous score for how bullish or bearish the article is. <strong>−1.0</strong> = extremely bearish / risk-off. <strong>0.0</strong> = neutral / balanced. <strong>+1.0</strong> = extremely bullish / risk-on.</div>
</div>

<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;padding:14px 16px;">
<div style="font-size:12px;font-weight:700;color:#7C3AED;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Avg Urgency &nbsp;·&nbsp; 1 – 10</div>
<div style="font-size:13px;color:#374151;line-height:1.6;">How time-sensitive the information is. <strong>1–3</strong> = background analysis or long-term trends. <strong>4–6</strong> = notable but not breaking. <strong>7–10</strong> = breaking news or immediate market-moving event requiring prompt attention.</div>
</div>

<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;padding:14px 16px;">
<div style="font-size:12px;font-weight:700;color:#2563EB;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Avg Impact &nbsp;·&nbsp; 1 – 10</div>
<div style="font-size:13px;color:#374151;line-height:1.6;">Expected effect on financial markets. <strong>1–3</strong> = minimal or niche impact. <strong>4–6</strong> = moderate, likely to move a specific sector. <strong>7–10</strong> = broad multi-asset market move expected (e.g. Fed decision, major geopolitical shock).</div>
</div>

</div>
<div style="font-size:12px;color:#94A3B8;margin-top:4px;line-height:1.6;">
All scores are assigned by <strong>Llama 3.3-70B</strong> (via Groq) using a structured prompt that enforces strict JSON output with validated ranges. The model acts as a quantitative financial analyst, inferring scores from the article's tone, entities, and market context — not from real-time market data.
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Split: charts left | breakdown right
        chart_col, list_col = st.columns([6, 4])

        with chart_col:
            try:
                st.plotly_chart(create_sentiment_chart(adf, edf), use_container_width=True)
            except Exception as e:
                st.error(f"Sentiment chart: {e}")
            try:
                st.plotly_chart(create_market_impact_chart(adf, edf), use_container_width=True)
            except Exception as e:
                st.error(f"Market impact chart: {e}")

        with list_col:
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#94A3B8;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">Article Breakdown</p>',
                unsafe_allow_html=True,
            )
            try:
                from analytics import _safe_merge
                merged = _safe_merge(adf, edf, extra_cols=["Sender"])
            except Exception:
                merged = pd.DataFrame()

            if merged.empty:
                st.warning("Could not load article details.")
            else:
                for _, row in merged.iterrows():
                    title = str(row.get("Subject", ""))
                    label = title[:55] + ("…" if len(title) > 55 else "")
                    with st.expander(label):
                        d1, d2 = st.columns(2)
                        with d1:
                            st.markdown(
                                f'**Sentiment:** {sentiment_badge_html(row["sentiment"])}',
                                unsafe_allow_html=True,
                            )
                            st.markdown(f'**Score:** `{row["sentiment_score"]:+.2f}`')
                        with d2:
                            st.markdown(f'**Urgency:** `{row["urgency"]} / 10`')
                            st.markdown(f'**Impact:** `{row["market_impact"]} / 10`')

                        topics  = row.get("topics") or []
                        entities = ", ".join(row.get("key_entities") or []) or "—"
                        if topics:
                            pills = " ".join(topic_pill(t) for t in topics)
                            st.markdown(f"**Topics:** {pills}", unsafe_allow_html=True)
                        st.markdown(f"**Entities:** {entities}")
                        summary = row.get("one_line_summary", "")
                        if summary:
                            st.caption(f"*{summary}*")

        # Full-width scatter
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            st.plotly_chart(create_urgency_market_chart(adf, edf), use_container_width=True)
        except Exception as e:
            st.error(f"Urgency chart: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════
with tab_archive:
    archive = st.session_state.archive

    if not archive:
        st.markdown("""
        <div style="text-align:center;padding:72px 20px;">
            <div style="font-size:40px;font-weight:700;color:#E2E8F0;margin-bottom:16px;">—</div>
            <h3 style="color:#1E293B;font-weight:600;margin-bottom:10px;font-size:18px;">No briefings yet</h3>
            <p style="color:#64748B;font-size:14px;">Generate your first briefing from the Inbox tab.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Card grid — 3 columns
        grid_cols = st.columns(3)
        for i, entry in enumerate(archive):
            with grid_cols[i % 3]:
                ts       = entry["timestamp"].strftime("%d %b %Y")
                t_time   = entry["timestamp"].strftime("%H:%M")
                duration = entry.get("duration_minutes", "—")
                sources  = entry.get("sources_count", "—")
                clusters = entry.get("clusters") or {}
                topic_names = [
                    c["cluster_name"]
                    for c in sorted(clusters.get("clusters", []), key=lambda x: x.get("priority", 99))[:3]
                ]
                tags_html = "".join(f'<span class="arc-tag">{t}</span>' for t in topic_names)
                featured  = "arc-card-featured" if i == 0 else ""

                st.markdown(
                    f'<div class="arc-card {featured}">'
                    f'  <div class="arc-ts">{ts} &nbsp; <span style="font-weight:400;color:#94A3B8;">{t_time}</span></div>'
                    f'  <div class="arc-sub">{sources} sources &nbsp;·&nbsp; {duration} min</div>'
                    f'  <div class="arc-tags">{tags_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("View briefing", key=f"view_{i}", use_container_width=True):
                    if st.session_state.open_archive_idx == i:
                        st.session_state.open_archive_idx = None  # toggle off
                    else:
                        st.session_state.open_archive_idx = i

        # Detail panel for selected card
        idx = st.session_state.open_archive_idx
        if idx is not None and idx < len(archive):
            entry = archive[idx]
            st.markdown(
                '<hr style="margin:24px 0 20px;border-color:#E2E8F0;">',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<p style="font-size:12px;font-weight:700;color:#94A3B8;'
                f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:16px;">'
                f'Briefing &nbsp;·&nbsp; {entry["timestamp"].strftime("%d %b %Y, %H:%M")}</p>',
                unsafe_allow_html=True,
            )

            st.audio(entry["audio_bytes"], format="audio/mp3")
            st.markdown("<br>", unsafe_allow_html=True)

            sc_col, meta_col = st.columns([3, 1])
            with sc_col:
                st.markdown(
                    '<p style="font-size:11px;font-weight:700;color:#94A3B8;'
                    'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Script</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;'
                    f'padding:18px 20px;font-size:14px;color:#1E293B;line-height:1.75;">'
                    f'{entry["script"]}</div>',
                    unsafe_allow_html=True,
                )
            with meta_col:
                st.markdown(
                    '<p style="font-size:11px;font-weight:700;color:#94A3B8;'
                    'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Details</p>',
                    unsafe_allow_html=True,
                )
                clusters = entry.get("clusters") or {}
                for c in sorted(clusters.get("clusters", []), key=lambda x: x.get("priority", 99)):
                    st.markdown(topic_pill(c["cluster_name"]), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(
                    f'<div style="font-size:12px;color:#64748B;line-height:2;">'
                    f'<strong style="color:#0F172A;">Filter:</strong>&nbsp; {entry.get("filter_used", "—")}<br>'
                    f'<strong style="color:#0F172A;">Sources:</strong>&nbsp; {entry.get("sources_count", "—")}<br>'
                    f'<strong style="color:#0F172A;">Duration:</strong>&nbsp; {entry.get("duration_minutes", "—")} min'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Sentiment chart if available
            a_df = entry.get("analytics_df")
            e_df = entry.get("emails_df")
            if (
                a_df is not None
                and isinstance(a_df, pd.DataFrame)
                and not a_df.empty
                and e_df is not None
                and isinstance(e_df, pd.DataFrame)
                and not e_df.empty
            ):
                show_chart = st.checkbox("Show sentiment chart", key=f"arch_sent_{idx}")
                if show_chart:
                    try:
                        fig = create_sentiment_chart(a_df, e_df)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as chart_err:
                        st.warning(f"Could not render chart: {chart_err}")
