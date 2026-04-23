"""
gmail_service.py — Fetch Gmail inbox server-side using a stored Google access token.
Maps Gmail messages to the article format expected by the frontend.
"""
import base64
import html as html_lib
import re

import httpx

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

_FINANCIAL_KW = re.compile(
    r"\bstock\b|\bmarket\b|equity|bond|yield|\betf\b|nasdaq|\bs&p\b|\bdow\b|earnings|"
    r"revenue|inflation|federal reserve|\bfed\b|\becb\b|interest rate|\bgdp\b|"
    r"bitcoin|\bcrypto\b|\boil\b|gold price|\bgold\b|commodity|portfolio|dividend|"
    r"merger|acquisition|\bipo\b|quarterly|hedge fund|bloomberg|reuters|"
    r"cnbc|wall street|goldman|jpmorgan|morgan stanley|barclays|blackrock|"
    r"rate cut|rate hike|basis point|bull market|bear market|fiscal|monetary|"
    r"treasury|bund|futures|options|volatility|rally|plunge|correction|"
    r"marketwatch|financial times|morningstar|seeking alpha|motley fool",
    re.IGNORECASE,
)

_FINANCIAL_SENDER = re.compile(
    r"bloomberg|reuters|cnbc|financial times|\bft\b|wall street|morningstar|"
    r"barclays|jpmorgan|goldman|morgan stanley|blackrock|fidelity|vanguard|"
    r"marketwatch|seeking alpha|motley fool|yahoo finance|investopedia|zacks|"
    r"the economist|axios markets|morning brew|daily upside|briefing\.com|"
    r"alphastreet|streetinsider|benzinga",
    re.IGNORECASE,
)

# Senders that are never financial regardless of body content
_EXCLUDE_SENDER = re.compile(
    r"careers@|@[^>]*hiring|@[^>]*jobs\b|recruitment|workday|"
    r"@quora\.com|quora-digest|@reddit\.com|"
    r"marriott|hilton|hyatt|\bihg\b|"
    r"@spotify|@netflix|@airbnb|@uber\b|@lyft\b|"
    r"noreply@amazon|shipment-tracking|order-update",
    re.IGNORECASE,
)

# Subjects that are never financial
_EXCLUDE_SUBJECT = re.compile(
    r"job opportunit|we.?re hiring|now hiring|career opportunit|open position|"
    r"your order|has shipped|delivery|tracking number|"
    r"viewed your profile|new connection request|"
    r"password reset|verify your email|confirm your (email|account)",
    re.IGNORECASE,
)

_TOPIC_PATTERNS = [
    ("AI & Tech",     re.compile(r"ai |artificial intelligence|nvidia|microsoft|apple|google|meta|semiconductor|chip|software|cloud|openai|\bllm\b", re.I)),
    ("Crypto",        re.compile(r"bitcoin|\bethereum\b|\bcrypto\b|blockchain|defi|\bbtc\b|\beth\b|coinbase", re.I)),
    ("Central Banks", re.compile(r"federal reserve|\bfed\b|\becb\b|\bboe\b|monetary policy|interest rate|rate cut|rate hike|basis point", re.I)),
    ("Energy",        re.compile(r"\boil\b|\bgas\b|\benergy\b|opec|crude|brent|wti|renewable|solar|wind|\blng\b", re.I)),
    ("Macro",         re.compile(r"\bgdp\b|recession|unemployment|\bcpi\b|\bppi\b|deflation|macro|payroll|deficit", re.I)),
    ("Equities",      re.compile(r"\bstock\b|equity|s&p|nasdaq|\bdow\b|earnings|\bipo\b|dividend|buyback|rally|bear market", re.I)),
    ("Commodities",   re.compile(r"\bgold\b|silver|copper|wheat|corn|commodity|futures|aluminum|lithium", re.I)),
    ("Retail",        re.compile(r"\bretail\b|consumer|amazon|walmart|e-commerce|spending|consumer confidence", re.I)),
]

_URGENCY_KW = re.compile(
    r"breaking|urgent|flash|alert|crash|plunge|surge|soar|rally|record|tumble|spike|meltdown|collapse",
    re.IGNORECASE,
)


def _decode_b64(s: str) -> str:
    s = s.replace("-", "+").replace("_", "/")
    try:
        return base64.b64decode(s + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(raw: str) -> str:
    """Strip HTML tags and decode entities — sufficient for keyword classification."""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_body(part: dict) -> str:
    """Recursively extract readable text, preferring plain text but falling back to HTML."""
    if not part:
        return ""
    mime = part.get("mimeType", "")
    data_b64 = part.get("body", {}).get("data", "")

    if mime == "text/plain" and data_b64:
        text = _decode_b64(data_b64).strip()
        if text:
            return text

    if mime == "text/html" and data_b64:
        text = _strip_html(_decode_b64(data_b64)).strip()
        if text:
            return text

    for sub in part.get("parts", []):
        text = _extract_body(sub)
        if text:
            return text
    return ""


def _get_header(headers: list, name: str) -> str:
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value", "")
    return ""


def _classify(subject: str, body: str, sender: str = "") -> tuple[bool, str, int]:
    # Hard exclusions: known non-financial senders and obvious spam subjects
    if _EXCLUDE_SENDER.search(sender) or _EXCLUDE_SUBJECT.search(subject):
        return False, "Other", 1

    from_financial_sender = bool(_FINANCIAL_SENDER.search(sender))
    subject_is_financial  = bool(_FINANCIAL_KW.search(subject))

    # Tier 1: trusted financial publisher → always financial
    # Tier 2: financial keyword in the subject → financial
    # Body-only matches are too noisy (job emails, prediction markets, etc.)
    is_financial = from_financial_sender or subject_is_financial

    combined = f"{subject} {body[:600]}"
    topic = "Other"
    for name, pat in _TOPIC_PATTERNS:
        if pat.search(combined):
            topic = name
            break
    urgency_hits = len(_URGENCY_KW.findall(combined))
    urgency_score = min(urgency_hits * 3 + (5 if is_financial else 2), 10)
    return is_financial, topic, urgency_score


async def fetch_gmail_inbox(access_token: str, max_results: int = 50) -> list[dict]:
    """Fetch recent Gmail messages and return them in article format."""
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    articles = []

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GMAIL_BASE}/messages",
            headers=auth_headers,
            params={"maxResults": max_results},
        )
        if resp.status_code == 401:
            raise PermissionError("Google token expired or revoked")
        resp.raise_for_status()

        message_refs = resp.json().get("messages", [])

        for ref in message_refs:
            try:
                r = await client.get(
                    f"{GMAIL_BASE}/messages/{ref['id']}",
                    headers=auth_headers,
                    params={"format": "full"},
                )
                r.raise_for_status()
                msg = r.json()

                hdrs    = msg.get("payload", {}).get("headers", [])
                subject = _get_header(hdrs, "subject") or "(no subject)"
                sender  = _get_header(hdrs, "from")    or "Unknown"
                date    = _get_header(hdrs, "date")    or ""
                body    = _extract_body(msg.get("payload", {}))

                is_financial, topic, urgency = _classify(subject, body, sender)

                articles.append({
                    # Web app fields
                    "ID":           ref["id"],
                    "Subject":      subject,
                    "Sender":       sender,
                    "Date":         date[:40],
                    "Content":      body[:3000],
                    "URL":          f"https://mail.google.com/mail/u/0/#inbox/{ref['id']}",
                    "is_financial": is_financial,
                    "topic":        topic,
                    "urgency_kw":   urgency,
                    # generate-raw compatible fields (same data, different keys)
                    "title":        subject,
                    "source":       sender,
                    "description":  body[:400].replace("\n", " ").strip(),
                    "content":      body[:3000],
                    "publishedAt":  date,
                })
            except Exception:
                continue

    return articles
