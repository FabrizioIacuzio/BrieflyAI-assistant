"""
demo_inbox.py — Pre-built fake inbox returned to demo-credential users.
Articles follow the same schema as fetch_gmail_inbox() so the rest of the
pipeline (generate-raw, analytics, briefing) works identically.
"""

_FINANCIAL = [
    {
        "ID": "demo_001",
        "Subject": "NVIDIA crushes Q1 earnings — data-centre revenue up 78% YoY",
        "Sender": "Bloomberg Markets",
        "Date": "2026-04-23",
        "Content": (
            "NVIDIA reported first-quarter revenue of $34.1 billion, beating the Wall Street "
            "consensus of $30.8 billion, as demand for its Blackwell GPU architecture showed no "
            "sign of saturation. Data-centre revenue — overwhelmingly driven by AI model training "
            "and inference workloads — rose 78% year-on-year to $26.3 billion. CEO Jensen Huang "
            "said the company was 'supply-constrained, not demand-constrained' and guided Q2 "
            "revenue to $38 billion ±2%. Gross margin of 78.4% also exceeded forecasts. Shares "
            "rose 9% in after-hours trading, pushing NVIDIA's market cap above $2.8 trillion."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "AI & Tech",
        "urgency_kw": 8,
    },
    {
        "ID": "demo_002",
        "Subject": "Fed holds rates at 4.25–4.50%, signals two cuts later in 2026",
        "Sender": "Reuters Finance",
        "Date": "2026-04-23",
        "Content": (
            "The Federal Open Market Committee voted unanimously to hold the fed funds rate at "
            "4.25–4.50% at its April meeting, as expected. Chair Jerome Powell said in a press "
            "conference that while inflation had 'made real progress', it remained 'modestly above' "
            "the 2% target and that the Committee needed 'greater confidence' before cutting. The "
            "dot-plot showed a median expectation of two 25 basis-point cuts in the second half of "
            "2026, unchanged from March. Two-year Treasury yields fell 6 bps to 4.11% on the news. "
            "Market-implied odds for a June cut dropped to 22% from 31% before the statement."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Central Banks",
        "urgency_kw": 9,
    },
    {
        "ID": "demo_003",
        "Subject": "S&P 500 closes at all-time high of 6,284 on AI-led tech surge",
        "Sender": "CNBC Markets",
        "Date": "2026-04-23",
        "Content": (
            "The S&P 500 gained 1.4% to close at a record 6,284.17, with the Nasdaq Composite up "
            "2.1% to a new high of 19,820. NVIDIA, Microsoft, and Alphabet drove the bulk of "
            "gains after a string of AI-related earnings beats. The equal-weight S&P 500 rose "
            "just 0.5%, highlighting narrow leadership. The VIX fell to 13.2, its lowest since "
            "January. Breadth was modest: 320 stocks advanced versus 180 declining. Small-caps "
            "lagged, with the Russell 2000 flat. Options positioning ahead of Friday's expiry "
            "suggests dealers are short gamma, amplifying moves in either direction."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Equities",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_004",
        "Subject": "ECB cuts rates 25bps to 2.25% — euro slides to 1.07 vs dollar",
        "Sender": "Financial Times",
        "Date": "2026-04-22",
        "Content": (
            "The European Central Bank reduced its deposit facility rate by 25 basis points to "
            "2.25%, the fourth consecutive cut in this cycle. President Christine Lagarde said "
            "the disinflation process was 'well on track' and that the ECB remained 'data-dependent'. "
            "Eurozone inflation fell to 2.1% in March, just above target. The euro slid 0.8% "
            "against the dollar to 1.0712, the weakest since February. German 10-year Bund yields "
            "fell 9 bps to 2.41%. Markets now price a further 50 bps of ECB easing by year-end, "
            "versus just 25 bps for the Fed — widening the rate differential that has pressured "
            "the single currency."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Central Banks",
        "urgency_kw": 8,
    },
    {
        "ID": "demo_005",
        "Subject": "OPEC+ extends production cuts through Q3 — Brent crude jumps to $89",
        "Sender": "Reuters Energy",
        "Date": "2026-04-22",
        "Content": (
            "OPEC+ agreed to extend its 2.2 million barrel-per-day voluntary production cuts "
            "through the end of September 2026, surprising markets that had expected a partial "
            "rollback. Saudi Arabia and Russia led the consensus, citing 'elevated inventory "
            "levels and uncertain demand prospects' in a joint statement. Brent crude surged "
            "3.1% to $89.20/barrel, while WTI gained 2.9% to $85.40. Energy stocks led market "
            "gains. US shale producers' activity in the Permian Basin remains elevated, however, "
            "with the rig count up 8% year-to-date — a structural offset that OPEC+ must "
            "navigate. Analysts at Goldman Sachs raised their Q3 Brent target from $85 to $93."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Energy",
        "urgency_kw": 8,
    },
    {
        "ID": "demo_006",
        "Subject": "US Q1 GDP growth revised to 1.8%, below 2.4% consensus estimate",
        "Sender": "Wall Street Journal",
        "Date": "2026-04-22",
        "Content": (
            "The Bureau of Economic Analysis's advance estimate showed the US economy expanded "
            "at an annualised rate of 1.8% in Q1 2026, below the 2.4% consensus and down from "
            "3.1% in Q4 2025. Personal consumption grew 2.2%, net exports subtracted 0.6 pp "
            "as imports surged ahead of tariff deadlines, and government spending contracted "
            "for the second consecutive quarter. The deflator rose to 3.1%, hotter than expected, "
            "worsening the stagflation optics. The dollar weakened 0.4% on a trade-weighted "
            "basis. Economists at JPMorgan trimmed their full-year US GDP forecast from 2.3% "
            "to 2.1% and flagged rising downside risks."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Macro",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_007",
        "Subject": "Gold hits $3,420/oz — all-time high on safe-haven and central-bank demand",
        "Sender": "Bloomberg Commodities",
        "Date": "2026-04-23",
        "Content": (
            "Gold climbed to a record $3,420 per troy ounce, up 1.8% on the day and 24% "
            "year-to-date. Central bank buying — particularly from China, India, and Turkey — "
            "has absorbed over 1,100 tonnes in the past 12 months according to the World Gold "
            "Council. Western ETF inflows also restarted in Q1, adding 87 tonnes after two "
            "years of net outflows. Analysts at Citi raised their 12-month target to $3,600, "
            "citing 'persistent de-dollarisation demand and structurally negative real yields' "
            "in emerging markets. Silver outperformed, rising 3.2% to $38.90/oz, while the "
            "gold-silver ratio compressed to 87.8."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Commodities",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_008",
        "Subject": "Microsoft Azure revenue up 35% — AI services now 15% of cloud mix",
        "Sender": "MarketWatch",
        "Date": "2026-04-22",
        "Content": (
            "Microsoft reported fiscal Q3 revenue of $72.4 billion, beating estimates by 4%. "
            "Azure grew 35% in constant currency, accelerating from 31% last quarter, with "
            "management attributing 7 percentage points of growth directly to AI services — "
            "Copilot, Azure OpenAI Service, and inference APIs. CFO Amy Hood said AI backlog "
            "had reached $18 billion, up from $12 billion three months ago. Operating margin "
            "expanded 200 bps to 45.6% despite elevated capex. The company raised full-year "
            "capex guidance to $75 billion to meet cloud infrastructure demand. Shares rose "
            "4.3% in after-hours trading."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "AI & Tech",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_009",
        "Subject": "March jobs report: +247k payrolls, unemployment steady at 3.7%",
        "Sender": "Reuters",
        "Date": "2026-04-21",
        "Content": (
            "The US economy added 247,000 non-farm payrolls in March, ahead of the 210,000 "
            "consensus, while the unemployment rate held at 3.7%. Average hourly earnings rose "
            "0.4% month-on-month (4.3% year-on-year), above the 0.3% forecast. Labour force "
            "participation edged up to 62.8%. Healthcare (+58k), government (+41k), and "
            "construction (+33k) led gains. Manufacturing shed 8,000 jobs amid import tariff "
            "uncertainty. The strong reading reduced the probability of a May Fed cut to under "
            "5%. Revisions subtracted 18,000 from the prior two months."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Macro",
        "urgency_kw": 6,
    },
    {
        "ID": "demo_010",
        "Subject": "Copper prices surge 5% on China stimulus package worth $500bn",
        "Sender": "FT Commodities",
        "Date": "2026-04-21",
        "Content": (
            "Copper futures on the LME surged 5.1% to $10,640/tonne, a 16-month high, after "
            "China's State Council announced a RMB 3.6 trillion ($500 billion) infrastructure "
            "stimulus package focused on clean-energy grids, high-speed rail, and urban "
            "renewal. Analysts estimate the programme would require 1.8 million additional "
            "tonnes of copper over three years. Chile's state-owned Codelco and Rio Tinto "
            "shares jumped 6% and 4% respectively in London trading. Aluminium gained 3.8% "
            "and iron ore was up 4.6% in Dalian. The broader mining index hit its highest "
            "level since August 2025."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Commodities",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_011",
        "Subject": "Tesla Q1 2026: deliveries of 478k beat estimate, gross margin recovers to 18.4%",
        "Sender": "CNBC Tech",
        "Date": "2026-04-21",
        "Content": (
            "Tesla delivered 478,000 vehicles in Q1 2026, ahead of the 451,000 analyst consensus "
            "and recovering from the weak 387,000 in Q4 2025. Revenue rose 9% to $24.2 billion. "
            "Auto gross margin (ex-credits) rebounded to 18.4% from 16.2%, helped by cost "
            "reductions in the Model Y refresh and higher average selling prices in Europe. "
            "Full-self driving subscription revenue hit $1.1 billion quarterly for the first "
            "time. Energy storage deployments of 11.8 GWh set a record. Management guided "
            "for 'at least 20% delivery growth' in 2026. Shares climbed 7% in after-hours "
            "trading after two consecutive quarters of disappointment."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Equities",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_012",
        "Subject": "Goldman Sachs upgrades US equities to Overweight, lifts S&P 500 target to 6,500",
        "Sender": "Bloomberg Intelligence",
        "Date": "2026-04-22",
        "Content": (
            "Goldman Sachs equity strategist David Kostin upgraded US stocks to Overweight "
            "in a global asset-allocation shift, raising the year-end S&P 500 target from "
            "6,100 to 6,500. The note cited AI productivity tailwinds, better-than-expected "
            "earnings revision trends, and a benign credit environment. Goldman cut Emerging "
            "Markets to Neutral and European equities to Underweight. The bank projects "
            "S&P 500 EPS of $278 in 2026 and $310 in 2027. Key risks cited: a re-acceleration "
            "of inflation forcing the Fed to reverse course, and an escalation in US-China "
            "trade tensions. The note triggered significant institutional buying in S&P "
            "500 futures in early trading."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Equities",
        "urgency_kw": 6,
    },
    {
        "ID": "demo_013",
        "Subject": "IMF raises 2026 global growth forecast to 3.4%, warns on trade fragmentation",
        "Sender": "Reuters Macro",
        "Date": "2026-04-20",
        "Content": (
            "The International Monetary Fund raised its 2026 global growth forecast by 0.1 "
            "percentage point to 3.4% in its Spring World Economic Outlook, citing stronger "
            "momentum in the US and India. Advanced economies are projected to grow 1.9%, "
            "while emerging and developing economies are seen at 4.5%. The Fund kept its China "
            "forecast unchanged at 4.5%, flagging property sector headwinds. Chief Economist "
            "Pierre-Olivier Gourinchas warned that trade fragmentation could permanently "
            "reduce global output by up to 2% over the next decade if geopolitical blocs "
            "continue to decouple. Inflation is expected to return to target in most advanced "
            "economies by late 2026."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Macro",
        "urgency_kw": 5,
    },
    {
        "ID": "demo_014",
        "Subject": "US 10-year Treasury yield climbs to 4.68% — highest since November 2025",
        "Sender": "Bloomberg Fixed Income",
        "Date": "2026-04-23",
        "Content": (
            "The 10-year US Treasury yield rose 8 basis points to 4.68%, the highest since "
            "November 2025, following the hotter-than-expected Q1 GDP deflator and strong "
            "payrolls data. Real yields (10-year TIPS) hit 2.24%, near the top of their "
            "post-pandemic range. The 2s10s yield curve steepened to +52 bps — the widest "
            "since early 2025 — as short rates fell on dovish Fed-speak while long rates "
            "rose on term premium and fiscal concerns. Foreign demand at this week's $45bn "
            "10-year auction was below average, with the bid-to-cover at 2.31 versus the "
            "4-auction average of 2.48. Mortgage rates are likely to re-test 7.5%."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "Central Banks",
        "urgency_kw": 7,
    },
    {
        "ID": "demo_015",
        "Subject": "OpenAI launches GPT-5 enterprise API — 3x faster, 60% cheaper than GPT-4",
        "Sender": "TechCrunch Finance",
        "Date": "2026-04-20",
        "Content": (
            "OpenAI released the GPT-5 API for enterprise customers, claiming a 3× throughput "
            "improvement and a 60% cost reduction versus GPT-4 Turbo at equivalent quality. "
            "The model introduces 'dynamic reasoning depth', adjusting compute per query for "
            "cost efficiency. Enterprise pricing starts at $2 per million input tokens. Microsoft, "
            "which has exclusive cloud rights, said GPT-5 would be available on Azure OpenAI "
            "Service 'within weeks'. The announcement drove Anthropic and Google DeepMind to "
            "accelerate their own model releases. Analysts estimate the AI API market will "
            "exceed $80 billion annually by 2028, up from $18 billion in 2025."
        ),
        "URL": "",
        "is_financial": True,
        "topic": "AI & Tech",
        "urgency_kw": 6,
    },
]

_NOISE = [
    {
        "ID": "demo_n01",
        "Subject": "Your Amazon order #114-8821049 has shipped",
        "Sender": "Amazon",
        "Date": "2026-04-23",
        "Content": (
            "Hi there, your Sony WH-1000XM6 headphones are on their way. "
            "Estimated delivery: Friday, April 25. Tracking number: 1Z999AA10123456784. "
            "Track your package at amazon.com/orders."
        ),
        "URL": "",
        "is_financial": False,
        "topic": "Other",
        "urgency_kw": 1,
    },
    {
        "ID": "demo_n02",
        "Subject": "9 people viewed your profile this week",
        "Sender": "LinkedIn",
        "Date": "2026-04-22",
        "Content": (
            "Your profile is getting noticed! 9 people viewed your LinkedIn profile this week, "
            "including 4 from the financial services industry. Consider updating your headline "
            "to improve visibility."
        ),
        "URL": "",
        "is_financial": False,
        "topic": "Other",
        "urgency_kw": 1,
    },
    {
        "ID": "demo_n03",
        "Subject": "PR #312 merged into main — feat: star rating feedback system",
        "Sender": "GitHub",
        "Date": "2026-04-23",
        "Content": (
            "briefly-ai/briefly: feat: replace thumbs up/down with 1–5 star rating system "
            "merged by FabrizioIacuzio into main. 7 files changed, 139 insertions(+), "
            "51 deletions(-)."
        ),
        "URL": "",
        "is_financial": False,
        "topic": "Other",
        "urgency_kw": 1,
    },
    {
        "ID": "demo_n04",
        "Subject": "Q2 Performance Review — self-assessment due by May 1st",
        "Sender": "HR Department",
        "Date": "2026-04-21",
        "Content": (
            "The Q2 performance review cycle opens this week. Please complete your "
            "self-assessment in Workday under the Performance tab by Thursday, May 1st. "
            "Your manager will schedule a 1:1 review during the week of May 5th. "
            "Contact hr@company.com with any questions."
        ),
        "URL": "",
        "is_financial": False,
        "topic": "Other",
        "urgency_kw": 1,
    },
    {
        "ID": "demo_n05",
        "Subject": "Your Spotify Wrapped 2026 is ready",
        "Sender": "Spotify",
        "Date": "2026-04-20",
        "Content": (
            "You've listened to 418 hours of music so far in 2026. Your top genre: Jazz. "
            "Most-played artist: Miles Davis. You're in the top 5% of listeners for "
            "your favourite playlist. Check your full stats in the app."
        ),
        "URL": "",
        "is_financial": False,
        "topic": "Other",
        "urgency_kw": 1,
    },
]


def get_demo_inbox() -> list[dict]:
    """Return enriched demo articles in the same schema as fetch_gmail_inbox()."""
    articles = []
    for a in _FINANCIAL + _NOISE:
        articles.append({
            **a,
            # generate-raw compatible aliases
            "title":       a["Subject"],
            "source":      a["Sender"],
            "description": a["Content"][:400].replace("\n", " ").strip(),
            "content":     a["Content"],
            "publishedAt": a["Date"],
        })
    return articles
