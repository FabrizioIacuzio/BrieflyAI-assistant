import base64
import html as _html
import re
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as _components

from analytics import (
    analyze_emails_with_llm,
    create_market_impact_chart,
    create_sentiment_chart,
    create_urgency_market_chart,
    sentiment_badge_html,
)
from logic import (
    VOICE_ACCENTS,
    answer_briefing_question,
    detect_briefing_trends,
    multi_agent_debate,
    process_reports_and_generate_audio,
)
from news_fetcher import fetch_newsapi_articles, refresh_csv_from_newsapi
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
    "Major Sources Only",
]

MAJOR_FINANCIAL_SOURCES = {
    "Bloomberg", "Reuters", "CNBC", "The Wall Street Journal", "Wall Street Journal",
    "Financial Times", "Forbes", "MarketWatch", "Yahoo Finance", "Barron's",
    "Business Insider", "Associated Press", "BBC News", "BBC Business",
    "CNN Business", "The Guardian", "FactSet", "Goldman Sachs", "Investopedia",
    "Seeking Alpha", "The Motley Fool", "Morningstar", "Nasdaq", "AP News",
}

# ── Mock non-financial inbox emails (always injected so inbox looks realistic) ─
MOCK_NOISE_EMAILS = [
    {
        "ID": 1001, "Sender": "Amazon",
        "Subject": "Your order #114-8732641 has shipped",
        "Date": "2026-03-09",
        "Content": (
            "Hi Fabrizio, great news — your order has shipped and is on its way!\n\n"
            "Order: Kindle Paperwhite 16 GB (Black)\n"
            "Carrier: UPS\n"
            "Tracking: 1Z999AA10123456784\n"
            "Estimated delivery: Tuesday, March 11\n\n"
            "You can track your package in real time on the Amazon website using "
            "the tracking number above. If you have any questions about your order, "
            "please visit the Help section. Thank you for shopping with us!"
        ),
        "URL": "",
    },
    {
        "ID": 1002, "Sender": "LinkedIn",
        "Subject": "7 people viewed your profile this week",
        "Date": "2026-03-09",
        "Content": (
            "Hi Fabrizio, your profile is getting noticed!\n\n"
            "7 people viewed your profile in the last 7 days, including 3 recruiters. "
            "Sarah Mitchell from Goldman Sachs and 2 others also endorsed your Python skill.\n\n"
            "You also have 4 pending connection requests waiting for your response. "
            "Don't miss the chance to grow your network — log in to see who's interested "
            "in connecting with you and what opportunities might be waiting."
        ),
        "URL": "",
    },
    {
        "ID": 1003, "Sender": "HR Department",
        "Subject": "Q1 Performance Review — action required by March 15",
        "Date": "2026-03-08",
        "Content": (
            "Hi Fabrizio,\n\n"
            "This is a reminder that Q1 performance reviews are due by end of day "
            "Friday, March 15. Please complete your self-assessment form in Workday "
            "under the Performance module.\n\n"
            "Your manager Marco Ricci has already submitted their evaluation. To avoid "
            "delays, please submit yours at the earliest convenience. If you have any "
            "issues accessing the Workday portal, contact us at hr@company.com.\n\n"
            "Thank you,\nHR Team"
        ),
        "URL": "",
    },
    {
        "ID": 1004, "Sender": "IT Support",
        "Subject": "Scheduled system maintenance — Sunday 23:00 to 02:00 CET",
        "Date": "2026-03-08",
        "Content": (
            "Dear team,\n\n"
            "We will be performing scheduled maintenance on our core infrastructure "
            "this Sunday, March 10, between 23:00 and 02:00 CET.\n\n"
            "During this window the following services will be intermittently "
            "unavailable: VPN, internal wikis, Jira, and the company email server. "
            "Please ensure all your work is saved before the maintenance window begins. "
            "Laptop OS updates will be pushed automatically overnight — your device "
            "may restart once during this period.\n\n"
            "We apologise for any inconvenience.\n— IT Operations"
        ),
        "URL": "",
    },
    {
        "ID": 1005, "Sender": "Spotify",
        "Subject": "Your Discover Weekly is ready — 30 new tracks",
        "Date": "2026-03-07",
        "Content": (
            "Hi Fabrizio, your personalised Discover Weekly has been updated!\n\n"
            "This week we've handpicked 30 tracks we think you'll love based on your "
            "recent listening. Featured artists this week include Khruangbin, "
            "Floating Points, and Caribou.\n\n"
            "Your playlist refreshes every Monday morning. Open Spotify to start "
            "listening — and if you enjoy any tracks, don't forget to save them to "
            "your library before next Monday or they'll be replaced."
        ),
        "URL": "",
    },
    {
        "ID": 1006, "Sender": "Google",
        "Subject": "Storage alert: your Google account is 91% full",
        "Date": "2026-03-07",
        "Content": (
            "Hi Fabrizio,\n\n"
            "Your Google Account is nearly full. You are currently using 14.1 GB "
            "of your 15 GB free storage limit across Gmail, Google Drive, and "
            "Google Photos.\n\n"
            "When you run out of storage you will no longer be able to send or "
            "receive emails, upload files to Drive, or back up photos from your "
            "phone. To avoid interruption, consider deleting large attachments in "
            "Gmail or upgrading to Google One (100 GB for €1.99/month)."
        ),
        "URL": "",
    },
    {
        "ID": 1007, "Sender": "Expedia",
        "Subject": "Trip reminder: your flight to London departs in 5 days",
        "Date": "2026-03-06",
        "Content": (
            "Hi Fabrizio, your trip is just around the corner!\n\n"
            "Flight FR2041 · Milan MXP → London STN\n"
            "Departure: March 15 at 07:25 — check-in opens 24 hours before\n"
            "Bags: 1 checked bag included in your fare\n\n"
            "Hotel: Premier Inn Canary Wharf, 2 nights (check-in March 15)\n"
            "Booking reference: EXPXK8821\n\n"
            "Remember to download the Ryanair app to check in online and save your "
            "boarding pass to your phone. Have a great trip!"
        ),
        "URL": "",
    },
    {
        "ID": 1008, "Sender": "Notion",
        "Subject": "Weekly digest: 3 pages updated in your workspace",
        "Date": "2026-03-06",
        "Content": (
            "Hi Fabrizio,\n\n"
            "Here's what changed in your Notion workspace this week:\n\n"
            "- Project Roadmap Q1 2026 — edited by Marco (2 days ago)\n"
            "- Meeting Notes — 3 new entries added\n"
            "- Reading List — 1 new book added by you\n\n"
            "You have 2 comments awaiting your reply in the Project Roadmap page. "
            "Open Notion to catch up on the latest updates from your team."
        ),
        "URL": "",
    },
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

# ── Login gate ─────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "login_user" not in st.session_state:
    st.session_state["login_user"] = ""


def _show_login() -> None:
    # ── Global chrome removal + two fixed background panels ───────────────────
    st.markdown("""
    <style>
    #stDecoration, [data-testid="stSidebarNav"],
    #MainMenu, footer, [data-testid="stHeader"],
    [data-testid="stSidebar"] { display: none !important; }

    .stApp { background: transparent !important; }
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    [data-testid="stMain"] { padding: 0 !important; }

    /* Fixed split background — left dark, right blue */
    .login-bg-left {
        position: fixed; top: 0; left: 0;
        width: 50%; height: 100vh;
        background: #0C1220;
        z-index: 0;
    }
    .login-bg-right {
        position: fixed; top: 0; right: 0;
        width: 50%; height: 100vh;
        background: linear-gradient(145deg, #1E3A5F 0%, #2563EB 100%);
        z-index: 0;
    }

    /* Bring all Streamlit content above the backgrounds */
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stColumn"],
    [data-testid="stVerticalBlock"] { position: relative; z-index: 1; }

    [data-testid="stHorizontalBlock"] { gap: 0 !important; }

    /* Login form card */
    .login-card {
        background: #162032;
        border: 1px solid #1E293B;
        border-radius: 16px;
        padding: 40px 36px 36px;
        margin: 0 auto;
        max-width: 380px;
    }

    /* Inputs inside the card */
    .login-card input {
        background: #0C1220 !important;
        border: 1px solid #1E293B !important;
        color: white !important;
        border-radius: 8px !important;
    }
    .login-card input::placeholder { color: #475569 !important; }
    .login-card input:focus { border-color: #2563EB !important; }

    /* Labels inside card */
    .login-card label { color: #94A3B8 !important; font-size: 13px !important; }

    /* Sign-in button */
    .st-key-li_btn button {
        background: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 9px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        height: 50px !important;
        box-shadow: 0 4px 16px rgba(37,99,235,0.35) !important;
    }
    .st-key-li_btn button:hover {
        background: #1D4ED8 !important;
        transform: translateY(-1px) !important;
    }

    /* Feature cards on the right — solid, large, full-width */
    .feat-card {
        display: flex;
        align-items: center;
        gap: 20px;
        background: rgba(255,255,255,0.13);
        border: 1.5px solid rgba(255,255,255,0.25);
        border-radius: 16px;
        padding: 22px 24px;
        margin-bottom: 14px;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        backdrop-filter: blur(8px);
    }
    .feat-card-icon-wrap {
        width: 52px; height: 52px; min-width: 52px;
        background: rgba(255,255,255,0.18);
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px;
    }
    .feat-card-title {
        font-size: 16px; font-weight: 800;
        color: white; margin-bottom: 5px; line-height: 1.2;
    }
    .feat-card-sub {
        font-size: 13px; color: #BFDBFE; line-height: 1.55;
    }
    </style>

    <div class="login-bg-left"></div>
    <div class="login-bg-right"></div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns(2, gap="small")

    # ── LEFT: login form ──────────────────────────────────────────────────────
    with col_left:
        for _ in range(8):
            st.markdown("&nbsp;", unsafe_allow_html=True)

        # Card header
        st.markdown(
            '<div style="max-width:380px;margin:0 auto 20px;">'
            '<p style="font-size:12px;font-weight:700;color:#60A5FA;letter-spacing:0.1em;'
            'text-transform:uppercase;margin:0 0 10px;">BRIEFLY AI</p>'
            '<p style="font-size:26px;font-weight:800;color:white;line-height:1.2;'
            'letter-spacing:-0.4px;margin:0 0 6px;">Welcome back</p>'
            '<p style="font-size:14px;color:#64748B;margin:0;">Sign in to your account</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Constrain form width
        _, fc, _ = st.columns([0.05, 0.9, 0.05])
        with fc:
            username = st.text_input("Username", placeholder="e.g. fabrizio", key="li_user")
            password = st.text_input("Password", placeholder="Your password",
                                     type="password", key="li_pass")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Sign in  →", use_container_width=True, key="li_btn"):
                users = {}
                try:
                    users = dict(st.secrets.get("users", {}))
                except Exception:
                    pass
                if username and users.get(username) == password:
                    st.session_state["logged_in"] = True
                    st.session_state["login_user"] = username
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")

            st.markdown(
                '<div style="margin-top:24px;padding-top:18px;border-top:1px solid #1E293B;">'
                '<p style="font-size:11.5px;color:#475569;font-weight:600;'
                'text-transform:uppercase;letter-spacing:0.07em;margin:0 0 8px;">Credentials</p>'
                '<p style="font-size:13px;color:#64748B;margin:0;">'
                'Contact the administrator for access.</p></div>',
                unsafe_allow_html=True,
            )

    # ── RIGHT: branding + feature cards — ONE block, no Streamlit gaps ───────
    with col_right:
        features_html = "".join(
            f'<div class="feat-card">'
            f'<div class="feat-card-icon-wrap">{icon}</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div class="feat-card-title">{title}</div>'
            f'<div class="feat-card-sub">{sub}</div>'
            f'</div></div>'
            for icon, title, sub in [
                ("&#9993;",   "Smart Inbox",
                 "Live financial news merged with your inbox, auto-ranked by relevance"),
                ("&#127897;", "AI Audio Briefings",
                 "Multi-step LLM pipeline clusters, ranks and narrates your top stories"),
                ("&#128202;", "Sentiment Analytics",
                 "Per-article sentiment, urgency &amp; market impact scored by AI"),
                ("&#128193;", "Briefing Archive",
                 "Every briefing saved with full transcript and analytics"),
            ]
        )

        st.markdown(
            '<div style="display:flex;flex-direction:column;justify-content:center;'
            'min-height:90vh;padding:48px 12px 48px 4px;">'

            # Logo
            '<p style="font-size:48px;font-weight:900;color:white;'
            'letter-spacing:-2px;line-height:1;margin:0 0 12px;">'
            'Briefly <span style="color:#60A5FA;">AI</span></p>'

            # Tagline
            '<p style="font-size:15px;color:#93C5FD;margin:0 0 32px;line-height:1.75;">'
            'Turn your financial inbox into a briefing.</p>'

            # All 4 cards
            + features_html +

            # Footer
            '<p style="font-size:11.5px;color:rgba(255,255,255,0.35);margin-top:8px;">'
            'Powered by Groq LLaMA&nbsp;3.3 &nbsp;&middot;&nbsp; '
            'gTTS &nbsp;&middot;&nbsp; NewsAPI</p>'
            '</div>',
            unsafe_allow_html=True,
        )


if not st.session_state["logged_in"]:
    _show_login()
    st.stop()

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

/* ─── Nav card buttons — styled directly as cards ─── */
/* Base for all three */
.st-key-nav_inbox button,
.st-key-nav_analytics button,
.st-key-nav_archive button {
    height: 86px !important;
    border-radius: 12px !important;
    font-size: 14.5px !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em !important;
    transition: transform 0.12s, box-shadow 0.12s !important;
    transform: none !important;
}
.st-key-nav_inbox button:hover,
.st-key-nav_analytics button:hover,
.st-key-nav_archive button:hover {
    transform: translateY(-2px) !important;
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
    "latest_audio_bytes": None,
    "_last_suggestion": None,
    "open_archive_idx": None,
    "open_email_id": None,
    "active_view": "inbox",
    "starred_emails": set(),
    "chatbot_messages": [],
    "data_loaded_at": None,
    "trend_analysis": None,
    "debate_result": None,
    "briefing_feedback": None,  # "up" | "down" | None
    "briefing_feedback_note": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ────────────────────────────────────────────────────────────────────

# Keyword-based urgency scoring (no LLM call — instant)
_URGENCY_TIERS = [
    (9, r"breaking|emergency|crisis|crash|collapse|default|panic|meltdown"),
    (7, r"surge|plunge|soar|tumble|shock|unexpected|record|unexpected|unprecedented"),
    (5, r"rise|fall|gain|loss|report|announce|cut|hike|warning|concern"),
    (3, r"review|analysis|trend|outlook|forecast|update|plan"),
]

def inbox_urgency(text: str) -> int:
    for score, pattern in _URGENCY_TIERS:
        if re.search(pattern, text, re.I):
            return score
    return 2

def urgency_badge(score: int) -> str:
    if score >= 8:
        color, label = "#DC2626", "High"
    elif score >= 5:
        color, label = "#D97706", "Med"
    else:
        color, label = "#94A3B8", "Low"
    return (
        f'<span style="display:inline-block;background:{color}18;color:{color};'
        f'border:1px solid {color}40;padding:1px 7px;border-radius:20px;'
        f'font-size:10.5px;font-weight:700;white-space:nowrap;">{label}</span>'
    )

def custom_audio_player(audio_bytes: bytes) -> None:
    """HTML5 player with playback-speed buttons, rendered inside a component iframe."""
    b64 = base64.b64encode(audio_bytes).decode()
    html_str = f"""
    <style>
      body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
      audio {{ width:100%; border-radius:8px; }}
      .speed-row {{ display:flex; align-items:center; gap:8px; margin-top:8px; }}
      .speed-lbl {{ font-size:12px; color:#64748B; font-weight:600; }}
      .spd {{ background:#F1F5F9; border:1px solid #E2E8F0; border-radius:6px;
              padding:4px 10px; font-size:12px; font-weight:600; color:#1E293B;
              cursor:pointer; transition:background 0.12s; }}
      .spd:hover {{ background:#2563EB; color:white; border-color:#2563EB; }}
      .spd.active {{ background:#2563EB; color:white; border-color:#2563EB; }}
    </style>
    <audio id="ap" controls>
      <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    <div class="speed-row">
      <span class="speed-lbl">Speed:</span>
      <button class="spd" onclick="setSpeed(0.75)">0.75×</button>
      <button class="spd active" id="s1" onclick="setSpeed(1)">1×</button>
      <button class="spd" onclick="setSpeed(1.25)">1.25×</button>
      <button class="spd" onclick="setSpeed(1.5)">1.5×</button>
      <button class="spd" onclick="setSpeed(2)">2×</button>
    </div>
    <script>
      function setSpeed(r) {{
        document.getElementById('ap').playbackRate = r;
        document.querySelectorAll('.spd').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
      }}
    </script>
    """
    _components.html(html_str, height=110)


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
    if suggestion == "Major Sources Only":         return row["Sender"] in MAJOR_FINANCIAL_SOURCES
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
    """Render an email reading pane that looks like a real email client."""
    is_fin      = bool(row.get("Is_Financial", False))
    raw_content = str(row.get("Content", "")).strip() or "No content available."
    url         = str(row.get("URL", "")).strip()
    email_tp    = get_email_type(row)

    # Raw values for lookups
    raw_sender = str(row["Sender"])
    sender_color   = SENDER_COLORS.get(raw_sender, "#64748B")
    sender_initial = raw_sender[0].upper() if raw_sender else "?"

    # HTML-escape every text value that will be injected into markup
    sender  = _html.escape(raw_sender)
    subject = _html.escape(str(row["Subject"]))
    date    = _html.escape(str(row["Date"]))

    # Split on newlines then escape each paragraph individually
    para_chunks = [
        _html.escape(p.strip())
        for p in re.split(r"\n\n|\n", raw_content)
        if p.strip()
    ] or [_html.escape(raw_content)]

    intro = ""
    if is_fin and url:
        intro = (
            '<p style="margin:0 0 14px;font-size:13.5px;color:#64748B;font-style:italic;">'
            "Here's a brief update on this story from your financial feed:"
            "</p>"
        )

    paragraphs_html = "".join(
        f'<p style="margin:0 0 14px 0;font-size:14px;color:#334155;line-height:1.8;">{p}</p>'
        for p in para_chunks
    )

    link_html = ""
    if url and url.startswith("http"):
        safe_url = _html.escape(url, quote=True)
        link_html = (
            '<div style="margin-top:20px;padding-top:16px;border-top:1px solid #F1F5F9;">'
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer"'
            ' style="display:inline-flex;align-items:center;gap:6px;background:#2563EB;'
            'color:white;padding:9px 20px;border-radius:8px;text-decoration:none;'
            'font-size:13px;font-weight:600;letter-spacing:0.01em;">'
            'Read full article &#x2192;</a>'
            '<span style="margin-left:12px;font-size:12px;color:#94A3B8;">Opens in a new tab</span>'
            '</div>'
        )

    header = (
        f'<div style="padding:18px 24px 16px;border-bottom:1px solid #F1F5F9;'
        f'background:linear-gradient(135deg,{sender_color}12 0%,#FAFBFC 100%);">'
        '<div style="display:flex;align-items:center;gap:14px;">'
        f'<div style="width:42px;height:42px;min-width:42px;border-radius:50%;'
        f'background:{sender_color}22;display:flex;align-items:center;'
        f'justify-content:center;font-size:18px;font-weight:700;color:{sender_color};">'
        f'{sender_initial}</div>'
        '<div style="flex:1;min-width:0;">'
        f'<div style="font-size:14px;font-weight:700;color:#0F172A;">{sender}</div>'
        '<div style="font-size:12px;color:#94A3B8;margin-top:2px;">'
        f'To: <strong style="color:#64748B;">me</strong>'
        f' &nbsp;&middot;&nbsp; {date}'
        '</div></div>'
        f'{type_pill(email_tp)}'
        '</div>'
        f'<div style="font-size:17px;font-weight:700;color:#0F172A;'
        f'margin-top:14px;line-height:1.4;">{subject}</div>'
        '</div>'
    )

    body = (
        f'<div style="padding:22px 26px 20px;">'
        f'{intro}{paragraphs_html}{link_html}'
        '</div>'
    )

    return (
        '<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;'
        'margin:4px 0 16px;box-shadow:0 4px 16px rgba(0,0,0,0.07);overflow:hidden;">'
        + header + body +
        '</div>'
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
def _newsapi_key() -> str:
    try:
        return st.secrets.get("NEWSAPI_KEY", "")
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def _load_newsapi(api_key: str):
    if not api_key:
        return None
    return fetch_newsapi_articles(api_key, max_articles=30)


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
    """Priority: NewsAPI → RSS → CSV fallback. Returns (DataFrame, source_label)."""
    key = _newsapi_key()
    if key:
        df = _load_newsapi(key)
        if df is not None and len(df) > 0:
            return df, "NewsAPI"

    df = _load_rss()
    if df is not None and len(df) > 0:
        return df, "Live RSS"

    return _load_csv(), "Sample Data"


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
    duration_minutes = st.slider(
        "duration", min_value=1, max_value=10, value=3,
        format="%d min", label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Voice Accent**")
    voice_name = st.selectbox(
        "voice", list(VOICE_ACCENTS.keys()),
        label_visibility="collapsed",
    )
    voice_accent = VOICE_ACCENTS[voice_name]

    st.divider()
    if st.button("Refresh Feed", use_container_width=True):
        st.cache_data.clear()
        for k in list(st.session_state.keys()):
            if k.startswith("sel_"):
                del st.session_state[k]
        st.session_state["_last_suggestion"] = None
        st.rerun()

    # Save current live articles as the CSV fallback
    nk = _newsapi_key()
    if nk and st.button("Save to CSV fallback", use_container_width=True):
        with st.spinner("Saving…"):
            ok = refresh_csv_from_newsapi(nk)
        if ok:
            st.cache_data.clear()
            st.success("Saved!")
            st.rerun()
        else:
            st.error("NewsAPI fetch failed.")

    st.divider()
    user_label = st.session_state.get("login_user", "user").capitalize()
    st.markdown(
        f'<div style="font-size:12px;color:#64748B;margin-bottom:8px;">'
        f'Signed in as <strong style="color:#94A3B8;">{user_label}</strong></div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign out", use_container_width=True, key="logout_btn"):
        st.session_state["logged_in"] = False
        st.session_state["login_user"] = ""
        st.rerun()

    if st.session_state["data_loaded_at"]:
        st.markdown(
            f'<div style="font-size:10px;color:#334155;text-align:center;margin-top:8px;">'
            f'Last refreshed {st.session_state["data_loaded_at"]}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div style="font-size:10px;color:#334155;text-align:center;margin-top:8px;">Powered by Groq · gTTS</div>',
        unsafe_allow_html=True,
    )


# ── Load & prepare data ────────────────────────────────────────────────────────
with st.spinner("Loading feed…"):
    df, source_label = get_data()
    if st.session_state["data_loaded_at"] is None:
        st.session_state["data_loaded_at"] = datetime.now().strftime("%H:%M")

if df is None:
    st.error("No data available. Run `python setup_data.py` to generate sample data.")
    st.stop()

# Always inject the mock non-financial emails so the inbox looks realistic
mock_df = pd.DataFrame(MOCK_NOISE_EMAILS)
if "URL" not in df.columns:
    df["URL"] = ""
df = pd.concat([df, mock_df], ignore_index=True)
# Re-number IDs to be unique and sequential
df = df.drop_duplicates(subset=["Subject"]).reset_index(drop=True)
df["ID"] = range(1, len(df) + 1)
df = df.sort_values("Date", ascending=False).reset_index(drop=True)

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
src_colors = {"NewsAPI": "#7C3AED", "Live RSS": "#059669", "Sample Data": "#D97706"}
src_color  = src_colors.get(source_label, "#64748B")

hdr_l, hdr_r = st.columns([5, 1])
with hdr_l:
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
with hdr_r:
    st.markdown(
        f'<div style="text-align:right;padding-top:20px;">'
        f'<span style="background:{src_color}14;color:{src_color};border:1px solid {src_color}40;'
        f'padding:4px 12px;border-radius:20px;font-size:11.5px;font-weight:600;">'
        f'● {source_label}</span></div>',
        unsafe_allow_html=True,
    )

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


# ── Navigation cards ────────────────────────────────────────────────────────────
# ── Navigation: inject per-render CSS so each card button reflects active state ─
_av = st.session_state["active_view"]

def _nav_css(view_key: str) -> str:
    active = _av == view_key
    bg      = "#2563EB" if active else "white"
    fg      = "white"   if active else "#0F172A"
    border  = "#2563EB" if active else "#E2E8F0"
    shadow  = "0 4px 14px rgba(37,99,235,0.22)" if active else "0 1px 4px rgba(0,0,0,0.07)"
    hov_bg  = "#1D4ED8" if active else "#F8FAFC"
    hov_bdr = "#1D4ED8" if active else "#BFDBFE"
    return (
        f".st-key-nav_{view_key} button {{"
        f"  background:{bg} !important; color:{fg} !important;"
        f"  border:1.5px solid {border} !important;"
        f"  box-shadow:{shadow} !important; }}"
        f".st-key-nav_{view_key} button:hover {{"
        f"  background:{hov_bg} !important; border-color:{hov_bdr} !important; }}"
    )

st.markdown(
    "<style>"
    + _nav_css("inbox") + _nav_css("analytics") + _nav_css("archive")
    + "</style>",
    unsafe_allow_html=True,
)

nav1, nav2, nav3 = st.columns(3)
with nav1:
    lbl = f"✉  Inbox" + (f"   ({fin_count})" if fin_count else "")
    if st.button(lbl, key="nav_inbox", use_container_width=True):
        st.session_state["active_view"] = "inbox"
        st.rerun()
with nav2:
    if st.button("📊  Analytics", key="nav_analytics", use_container_width=True):
        st.session_state["active_view"] = "analytics"
        st.rerun()
with nav3:
    lbl = f"🗂  Archive" + (f"   ({archive_count})" if archive_count else "")
    if st.button(lbl, key="nav_archive", use_container_width=True):
        st.session_state["active_view"] = "archive"
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
active_view = st.session_state["active_view"]


# ══════════════════════════════════════════════════════════════════════════════
# INBOX
# ══════════════════════════════════════════════════════════════════════════════
if active_view == "inbox":

    # ── Search bar ────────────────────────────────────────────────────────────
    srch_l, srch_r = st.columns([5, 1])
    with srch_l:
        inbox_search = st.text_input(
            "search", placeholder="Search by subject or sender…",
            label_visibility="collapsed", key="inbox_search",
        )
    with srch_r:
        starred_only = st.toggle("Starred only", key="starred_toggle")

    # Apply search / starred filter
    display_df = df.copy()
    if inbox_search.strip():
        q = inbox_search.strip().lower()
        display_df = display_df[
            display_df["Subject"].str.lower().str.contains(q, na=False) |
            display_df["Sender"].str.lower().str.contains(q, na=False)
        ]
    if starred_only:
        display_df = display_df[display_df["ID"].isin(st.session_state["starred_emails"])]

    # Sub-header
    top_l, top_r = st.columns([4, 1])
    top_l.markdown(
        f'<p style="font-size:13px;color:#64748B;margin:0 0 14px;">'
        f'<strong style="color:#0F172A;">{len(display_df)}</strong> emails &nbsp;·&nbsp; '
        f'<strong style="color:#2563EB;">{int(display_df["Is_Financial"].sum())}</strong> financial reports</p>',
        unsafe_allow_html=True,
    )
    sel_slot = top_r.empty()

    if display_df.empty:
        st.markdown(
            '<div style="text-align:center;padding:48px 20px;">'
            '<p style="font-size:32px;color:#E2E8F0;margin-bottom:12px;">&#128269;</p>'
            '<p style="font-size:16px;font-weight:600;color:#1E293B;margin-bottom:6px;">No emails match</p>'
            '<p style="font-size:13px;color:#64748B;">Try a different search term or clear the filter.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # Column headers — added Urgency column
        _ind, h0, hstar, h1, h2, h3, h4, h5, h6 = st.columns(
            [0.008, 0.04, 0.04, 0.15, 0.42, 0.09, 0.12, 0.07, 0.055]
        )
        for col, lbl in zip([h1, h2, h3, h4, h5], ["Source", "Subject", "Date", "Type", "Urgency"]):
            col.markdown(
                f'<div style="font-size:10.5px;font-weight:700;color:#94A3B8;'
                f'text-transform:uppercase;letter-spacing:0.08em;padding-bottom:6px;">{lbl}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<hr style="margin:0 0 4px;border-color:#E2E8F0;">', unsafe_allow_html=True)

        # Email rows
        selected_rows = []
        for _, row in display_df.iterrows():
            rid      = row["ID"]
            is_fin   = bool(row["Is_Financial"])
            email_tp = get_email_type(row)
            is_open  = st.session_state["open_email_id"] == rid
            is_starred = rid in st.session_state["starred_emails"]
            urg_score  = inbox_urgency(f"{row['Subject']} {row.get('Content','')}")

            c_ind, c0, cstar, c1, c2, c3, c4, c5, c6 = st.columns(
                [0.008, 0.04, 0.04, 0.15, 0.42, 0.09, 0.12, 0.07, 0.055]
            )

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

            with cstar:
                star_icon = "★" if is_starred else "☆"
                if st.button(star_icon, key=f"star_{rid}", type="secondary"):
                    starred = st.session_state["starred_emails"]
                    if rid in starred:
                        starred.discard(rid)
                    else:
                        starred.add(rid)
                    st.session_state["starred_emails"] = starred
                    st.rerun()

            with c1:
                st.markdown(sender_pill(str(row["Sender"])), unsafe_allow_html=True)

            with c2:
                weight = "600" if is_fin else "400"
                color  = "#0F172A" if is_fin else "#94A3B8"
                st.markdown(
                    f'<span style="font-size:13.5px;font-weight:{weight};color:{color};">'
                    f'{_html.escape(str(row["Subject"]))}</span>',
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
                if is_fin:
                    st.markdown(urgency_badge(urg_score), unsafe_allow_html=True)
                else:
                    st.markdown("&nbsp;", unsafe_allow_html=True)

            with c6:
                icon = "▼" if is_open else "›"
                if st.button(icon, key=f"open_{rid}", type="secondary"):
                    st.session_state["open_email_id"] = None if is_open else rid
                    st.rerun()

            st.markdown('<hr class="inbox-divider">', unsafe_allow_html=True)

            if is_open:
                st.markdown(email_detail_html(row), unsafe_allow_html=True)

        # Selection counter
        n_sel = len(selected_rows)
        sel_slot.markdown(
            f'<div style="text-align:right;font-size:13px;color:#2563EB;font-weight:600;">'
            f'{n_sel} selected</div>',
            unsafe_allow_html=True,
        )

    # selected_rows is defined inside the else block above; default to [] if search was empty
    if "selected_rows" not in dir():
        selected_rows = []
    n_sel = len(selected_rows)
    selected_df = pd.DataFrame(selected_rows) if selected_rows else pd.DataFrame()
    has_sel     = len(selected_df) > 0

    # ── Chatbot (before briefing) ────────────────────────────────────────────
    st.markdown(
        '<hr style="margin:24px 0 16px;border-color:#E2E8F0;">'
        '<p style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:4px;">'
        'Ask about any article in your inbox</p>'
        '<p style="font-size:12px;color:#64748B;margin-bottom:12px;">'
        'The AI answers using all articles in your inbox as context.</p>',
        unsafe_allow_html=True,
    )
    for msg in st.session_state.chatbot_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(
                    f'<div style="font-family: inherit; font-size: 14px; font-weight: 400; '
                    f'font-style: normal; line-height: 1.6; color: #1E293B; white-space: pre-wrap;">'
                    f'{_html.escape(msg["content"])}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(msg["content"])
    chat_q = st.chat_input("e.g. What did Reuters say about gold? Which sector was most bearish?")
    if chat_q:
        st.session_state.chatbot_messages.append({"role": "user", "content": chat_q})
        with st.chat_message("user"):
            st.markdown(chat_q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    script_ctx = st.session_state.get("latest_script") or ""
                    answer = answer_briefing_question(script_ctx, df, chat_q)
                except Exception as e:
                    answer = f"Sorry, I couldn't answer that: {e}"
                st.markdown(
                    f'<div style="font-family: inherit; font-size: 14px; font-weight: 400; '
                    f'font-style: normal; line-height: 1.6; color: #1E293B; white-space: pre-wrap;">'
                    f'{_html.escape(answer)}</div>',
                    unsafe_allow_html=True,
                )
        st.session_state.chatbot_messages.append({"role": "assistant", "content": answer})
        st.rerun()

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
                selected_df, duration_minutes, voice_accent
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
            st.session_state.chatbot_messages  = []  # reset chat for new briefing
            st.session_state.debate_result     = None
            st.session_state.briefing_feedback = None
            st.session_state.briefing_feedback_note = ""

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            st.session_state.latest_audio_bytes = audio_bytes

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
                "feedback":         None,
                "feedback_note":    "",
            })

            # Rerun so the KPI counter and Archive tab reflect the new briefing immediately
            st.rerun()

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

        # ── Custom audio player ─────────────────────────────────────────────
        if st.session_state.latest_audio_bytes:
            custom_audio_player(st.session_state.latest_audio_bytes)
        else:
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
                f'{_html.escape(st.session_state.latest_script)}</div>',
                unsafe_allow_html=True,
            )
            # Download button
            st.download_button(
                label="Download script (.txt)",
                data=st.session_state.latest_script.encode("utf-8"),
                file_name=f"briefing_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                key="dl_script",
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

        # ── Risk Alert Banner ───────────────────────────────────────────────
        adf_check = st.session_state.analytics_df
        if adf_check is not None and not (isinstance(adf_check, pd.DataFrame) and adf_check.empty):
            high_risk = adf_check[
                (adf_check.get("urgency", pd.Series(dtype=int)) >= 8) |
                (adf_check.get("market_impact", pd.Series(dtype=int)) >= 8)
            ] if "urgency" in adf_check.columns and "market_impact" in adf_check.columns else pd.DataFrame()
            if not high_risk.empty:
                alert_items = []
                for _, r in high_risk.iterrows():
                    u = r.get("urgency", "?")
                    mi = r.get("market_impact", "?")
                    s = str(r.get("one_line_summary", "High-impact story"))[:90]
                    alert_items.append(
                        f'<li style="margin-bottom:4px;">'
                        f'<span style="font-weight:600;">{s}</span>'
                        f'&nbsp;<span style="color:#DC2626;font-size:11px;">'
                        f'[Urgency {u}/10 · Impact {mi}/10]</span></li>'
                    )
                items_html = "".join(alert_items)
                st.markdown(
                    f'<div style="margin-top:20px;background:#FEF2F2;border:1px solid #FCA5A5;'
                    f'border-left:4px solid #DC2626;border-radius:8px;padding:14px 18px;">'
                    f'<p style="font-size:12px;font-weight:700;color:#991B1B;'
                    f'text-transform:uppercase;letter-spacing:0.08em;margin:0 0 8px;">'
                    f'&#9888; High-Impact Alert</p>'
                    f'<p style="font-size:12px;color:#7F1D1D;margin:0 0 8px;">'
                    f'{len(high_risk)} article(s) flagged with urgency or market impact &ge; 8/10:</p>'
                    f'<ul style="margin:0;padding-left:18px;font-size:13px;color:#991B1B;">'
                    f'{items_html}</ul></div>',
                    unsafe_allow_html=True,
                )

        # ── Feedback Loop ───────────────────────────────────────────────────
        st.markdown(
            '<div style="margin-top:24px;padding-top:20px;border-top:1px solid #F1F5F9;">'
            '<p style="font-size:12px;font-weight:700;color:#94A3B8;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">'
            'Was this briefing useful?</p></div>',
            unsafe_allow_html=True,
        )
        fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 4])
        with fb_col1:
            if st.button("👍 Yes", key="fb_up", use_container_width=True):
                st.session_state.briefing_feedback = "up"
                if st.session_state.archive:
                    st.session_state.archive[0]["feedback"] = "up"
        with fb_col2:
            if st.button("👎 No", key="fb_down", use_container_width=True):
                st.session_state.briefing_feedback = "down"
                if st.session_state.archive:
                    st.session_state.archive[0]["feedback"] = "down"

        current_fb = st.session_state.get("briefing_feedback")
        if current_fb == "up":
            st.markdown(
                '<p style="font-size:13px;color:#16A34A;margin:8px 0 0;">Thanks! Glad it helped.</p>',
                unsafe_allow_html=True,
            )
        elif current_fb == "down":
            note = st.text_input(
                "What could be improved?",
                key="fb_note_input",
                placeholder="e.g. topics weren't relevant, too long, missing context…",
            )
            if note:
                st.session_state.briefing_feedback_note = note
                if st.session_state.archive:
                    st.session_state.archive[0]["feedback_note"] = note

        # ── Multi-Agent Debate ──────────────────────────────────────────────
        st.markdown(
            '<div style="margin-top:24px;padding-top:20px;border-top:1px solid #F1F5F9;">'
            '<p style="font-size:12px;font-weight:700;color:#94A3B8;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">'
            'Multi-Agent Analysis</p>'
            '<p style="font-size:12px;color:#94A3B8;margin-bottom:12px;">'
            'Chief Risk Officer · Trader · Analyst debate the briefing</p></div>',
            unsafe_allow_html=True,
        )
        if st.session_state.get("debate_result") is None:
            if st.button("Run debate", key="run_debate"):
                with st.spinner("Convening the war room…"):
                    debate = multi_agent_debate(
                        st.session_state.latest_script or "",
                        st.session_state.latest_emails,
                        st.session_state.analytics_df,
                    )
                    st.session_state.debate_result = debate
                    st.rerun()

        debate = st.session_state.get("debate_result")
        if debate:
            _DEBATE_PERSONAS = [
                ("cro",     "Chief Risk Officer", "#DC2626", "#FEF2F2", "#FCA5A5", "&#9888;"),
                ("trader",  "Trader",             "#16A34A", "#F0FDF4", "#86EFAC", "&#128200;"),
                ("analyst", "Research Analyst",   "#2563EB", "#EFF6FF", "#BFDBFE", "&#128202;"),
            ]
            for key, label, color, bg, border, icon in _DEBATE_PERSONAS:
                text = debate.get(key, "")
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {border};border-left:4px solid {color};'
                    f'border-radius:8px;padding:14px 18px;margin-bottom:10px;">'
                    f'<p style="font-size:11px;font-weight:700;color:{color};'
                    f'text-transform:uppercase;letter-spacing:0.08em;margin:0 0 6px;">'
                    f'{icon} {label}</p>'
                    f'<p style="font-size:13.5px;color:#1E293B;line-height:1.65;margin:0;">{_html.escape(text)}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            consensus = debate.get("consensus", "")
            if consensus:
                st.markdown(
                    f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
                    f'padding:12px 18px;margin-top:4px;">'
                    f'<p style="font-size:11px;font-weight:700;color:#64748B;'
                    f'text-transform:uppercase;letter-spacing:0.08em;margin:0 0 4px;">Consensus</p>'
                    f'<p style="font-size:13px;color:#475569;line-height:1.6;margin:0;">'
                    f'<em>{_html.escape(consensus)}</em></p></div>',
                    unsafe_allow_html=True,
                )
            if st.button("Regenerate debate", key="regen_debate"):
                st.session_state.debate_result = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
if active_view == "analytics":
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
                st.plotly_chart(create_sentiment_chart(adf, edf), use_container_width=True, key="analytics_sentiment")
            except Exception as e:
                st.error(f"Sentiment chart: {e}")
            try:
                st.plotly_chart(create_market_impact_chart(adf, edf), use_container_width=True, key="analytics_market_impact")
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
            st.plotly_chart(create_urgency_market_chart(adf, edf), use_container_width=True, key="analytics_urgency")
        except Exception as e:
            st.error(f"Urgency chart: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════
if active_view == "archive":
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
                fb = entry.get("feedback")
                fb_html = (
                    '&nbsp;<span style="font-size:13px;" title="You found this useful">&#128077;</span>'
                    if fb == "up" else
                    '&nbsp;<span style="font-size:13px;" title="Marked as not useful">&#128078;</span>'
                    if fb == "down" else ""
                )

                st.markdown(
                    f'<div class="arc-card {featured}">'
                    f'  <div class="arc-ts">{ts} &nbsp; <span style="font-weight:400;color:#94A3B8;">{t_time}</span>{fb_html}</div>'
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
                        st.plotly_chart(fig, use_container_width=True, key=f"archive_sentiment_{idx}")
                    except Exception as chart_err:
                        st.warning(f"Could not render chart: {chart_err}")

        # ── Trend chart + LLM trend detection ────────────────────────────────
        if len(archive) >= 2:
            st.markdown(
                '<hr style="margin:32px 0 24px;border-color:#E2E8F0;">'
                '<p style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:4px;">'
                'Briefing Trends</p>'
                '<p style="font-size:12px;color:#64748B;margin-bottom:18px;">'
                'Sentiment, urgency and market impact across your last briefings.</p>',
                unsafe_allow_html=True,
            )

            # Build trend data from archive analytics
            trend_rows = []
            for i, ent in enumerate(reversed(archive)):
                adf = ent.get("analytics_df")
                if adf is not None and isinstance(adf, pd.DataFrame) and not adf.empty:
                    trend_rows.append({
                        "Briefing": ent["timestamp"].strftime("%d %b %H:%M"),
                        "Avg Sentiment": round(float(adf["sentiment_score"].mean()), 2),
                        "Avg Urgency":   round(float(adf["urgency"].mean()), 1),
                        "Avg Impact":    round(float(adf["market_impact"].mean()), 1),
                    })

            if trend_rows:
                import plotly.graph_objects as go
                trend_df = pd.DataFrame(trend_rows)
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=trend_df["Briefing"], y=trend_df["Avg Sentiment"],
                    name="Sentiment Score", mode="lines+markers",
                    line=dict(color="#2563EB", width=2),
                    marker=dict(size=7),
                ))
                fig_trend.add_trace(go.Scatter(
                    x=trend_df["Briefing"], y=trend_df["Avg Urgency"],
                    name="Avg Urgency", mode="lines+markers",
                    line=dict(color="#7C3AED", width=2, dash="dot"),
                    marker=dict(size=7),
                    yaxis="y2",
                ))
                fig_trend.add_trace(go.Scatter(
                    x=trend_df["Briefing"], y=trend_df["Avg Impact"],
                    name="Avg Impact", mode="lines+markers",
                    line=dict(color="#059669", width=2, dash="dash"),
                    marker=dict(size=7),
                    yaxis="y2",
                ))
                fig_trend.update_layout(
                    height=300, margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="white", plot_bgcolor="#F8FAFC",
                    legend=dict(orientation="h", y=-0.25),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(title="Sentiment (−1 to +1)", showgrid=True,
                               gridcolor="#F1F5F9", range=[-1.1, 1.1]),
                    yaxis2=dict(title="Score (1–10)", overlaying="y", side="right",
                                showgrid=False, range=[0, 11]),
                )
                st.plotly_chart(fig_trend, use_container_width=True, key="archive_trend_chart")

            # LLM trend analysis button
            tc1, tc2 = st.columns([2, 5])
            with tc1:
                if st.button("Detect trends with AI", key="detect_trends_btn", use_container_width=True):
                    with st.spinner("Analysing trends across briefings…"):
                        try:
                            result = detect_briefing_trends(archive)
                            st.session_state["trend_analysis"] = result
                        except Exception as e:
                            st.session_state["trend_analysis"] = f"Error: {e}"
            with tc2:
                if st.session_state.get("trend_analysis"):
                    st.markdown(
                        f'<div style="background:#F0F7FF;border:1px solid #BFDBFE;border-radius:9px;'
                        f'padding:14px 18px;font-size:13.5px;color:#1E3A5F;line-height:1.7;">'
                        f'{_html.escape(st.session_state["trend_analysis"]).replace(chr(10), "<br>")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
