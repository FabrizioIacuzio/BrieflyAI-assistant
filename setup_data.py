import pandas as pd

# IDs 1001-1099: financial seed emails
# IDs 2001-2099: non-financial seed emails
# (RSS live emails use IDs 1–100, so no collision)

financial_emails = [
    # ── Market Volatility  (Subject: Surge|Rally|Crash|Volatility|Shock|Plunge|Soar) ──────────
    {
        "ID": 1001,
        "Sender": "Bloomberg",
        "Subject": "Global Markets Plunge as Trade War Fears Reignite",
        "Date": "2026-03-12",
        "Content": (
            "Equity markets fell sharply on Wednesday after the U.S. administration announced sweeping new tariffs "
            "on imported goods from major trading partners. The S&P 500 dropped more than 2% intraday, while the "
            "Nasdaq Composite declined over 3%. Investors rushed to safe-haven assets including government bonds "
            "and gold. Analysts warned that escalating trade tensions could weigh on corporate earnings and dampen "
            "consumer confidence in the coming quarters, with several banks revising down their growth forecasts."
        ),
    },
    {
        "ID": 1002,
        "Sender": "Reuters",
        "Subject": "Wall Street Volatility Surges After Surprise Inflation Print",
        "Date": "2026-03-12",
        "Content": (
            "U.S. equity volatility spiked after a hotter-than-expected inflation report rattled bond markets and "
            "prompted investors to reassess the timeline for Federal Reserve rate cuts. The VIX index climbed to its "
            "highest level in three months. Treasury yields rose sharply, with the 10-year yield briefly touching a "
            "six-week high. Analysts cautioned that if inflation proves stickier than expected, the Fed may be forced "
            "to maintain restrictive policy well into the second half of the year."
        ),
    },
    # ── Tech & AI Sector  (Subject: NVIDIA|AI|Microsoft|Chips|Tech|Semiconductor|Apple|Google|Meta|OpenAI) ──
    {
        "ID": 1003,
        "Sender": "Bloomberg",
        "Subject": "NVIDIA Extends Rally as AI Chip Demand Surges",
        "Date": "2026-03-12",
        "Content": (
            "NVIDIA shares continued their upward momentum as investors responded to stronger-than-expected "
            "demand for advanced AI accelerators across cloud and enterprise markets. Several investment banks "
            "raised their price targets, citing improved visibility into NVIDIA's data-center revenue pipeline. "
            "Executives from major cloud providers emphasised that AI infrastructure remains their highest-priority "
            "capital expenditure category for 2026, with demand outpacing supply in several regions."
        ),
    },
    {
        "ID": 1004,
        "Sender": "Reuters",
        "Subject": "Microsoft AI Integration Drives Record Enterprise Cloud Growth",
        "Date": "2026-03-11",
        "Content": (
            "Microsoft shares traded higher after the company reported record-breaking adoption of its AI-powered "
            "cloud services. Analysts noted that Microsoft's AI strategy continues to show positive returns, "
            "with revenue from AI tools rising upward by 40% year-on-year. Investors reacted positively to "
            "comments from executives indicating that AI-related revenue growth remains ahead of internal forecasts."
        ),
    },
    # ── Bullish Sentiment  (Content must include: Growth|Higher|Positive|Upward|Gain|Bull|Rise|Record) ──
    {
        "ID": 1006,
        "Sender": "CNBC",
        "Subject": "Consumer Confidence Hits Record High in Q1 2026",
        "Date": "2026-03-12",
        "Content": (
            "U.S. consumer confidence rose to a record high in the first quarter of 2026, surpassing expectations "
            "and signalling a positive outlook for household spending. The upward trend reflects resilient labor "
            "markets, moderating inflation, and continued real wage growth. Analysts noted that bullish sentiment "
            "among consumers is a constructive sign for retailers, with gains concentrated in housing and travel."
        ),
    },
    # ── Central Banks & Rates  (Subject: Fed|Rate|Inflation|ECB|Central Bank|Monetary|Yield|Treasury|Hawkish|Dovish) ──
    {
        "ID": 1008,
        "Sender": "Bloomberg",
        "Subject": "Fed Officials Signal Patience Ahead of Next Rate Decision",
        "Date": "2026-03-12",
        "Content": (
            "Federal Reserve officials signaled a patient approach to upcoming policy decisions, citing the need for "
            "additional data to assess the trajectory of inflation and labor-market conditions. Analysts noted that "
            "policymakers are focused on balancing the risks of easing too early against the costs of maintaining "
            "restrictive conditions for too long. Treasury yields moved slightly lower following the comments."
        ),
    },
    {
        "ID": 1009,
        "Sender": "FactSet",
        "Subject": "ECB Dovish Pivot: Rate Cuts Expected as Euro Zone Growth Slows",
        "Date": "2026-03-11",
        "Content": (
            "The European Central Bank signaled a dovish pivot at its March policy meeting, indicating that rate cuts "
            "are on the table as euro zone economic growth shows signs of slowing. ECB President confirmed that the "
            "governing council discussed easing monetary conditions, with a first 25-basis-point cut potentially coming "
            "as early as June. Euro area bond yields fell across the curve following the announcement."
        ),
    },
    # ── Global Energy  (Subject: Oil|OPEC|Energy|Crude|Gas|Refin|Brent|WTI|LNG) ──
    {
        "ID": 1012,
        "Sender": "Reuters",
        "Subject": "OPEC+ Signals Cautious Approach to Production Adjustments",
        "Date": "2026-03-11",
        "Content": (
            "Oil markets traded in a narrow range after OPEC+ officials signaled a cautious approach to future "
            "production adjustments. Delegates indicated that the group remains focused on maintaining market stability "
            "amid uneven global demand recovery. Traders are closely watching upcoming economic indicators that could "
            "influence demand forecasts for the second quarter."
        ),
    },
    {
        "ID": 1014,
        "Sender": "MarketWatch",
        "Subject": "WTI Oil Climbs on Surprise Drop in US Energy Inventories",
        "Date": "2026-03-12",
        "Content": (
            "West Texas Intermediate crude oil climbed above the $80 per barrel mark after the U.S. Energy Information "
            "Administration reported a larger-than-expected draw in crude inventories. The data reinforced concerns about "
            "tightening domestic supply as gasoline demand picks up ahead of summer. LNG export volumes also hit a "
            "monthly record, adding further pressure to domestic natural gas prices."
        ),
    },
    # ── Bloomberg / Reuters + Equities ───────────────────────────────────────
    {
        "ID": 1015,
        "Sender": "Bloomberg",
        "Subject": "S&P 500 Closes at New High on Broad-Based Earnings Strength",
        "Date": "2026-03-12",
        "Content": (
            "The S&P 500 set a new record closing high, driven by stronger-than-expected quarterly earnings from "
            "major technology and financial companies. The rally was broad-based, with all eleven sectors finishing "
            "in positive territory. Market breadth improved significantly, with advancing issues outnumbering decliners "
            "by a wide margin. Analysts noted that outperformance of cyclical stocks signals improving macro confidence."
        ),
    },
]

noise_emails = [
    {
        "ID": 2001,
        "Sender": "Amazon",
        "Subject": "Your order #114-8273641 has shipped",
        "Date": "2026-03-12",
        "Content": (
            "Hi Fabrizio, your order has been dispatched and is on its way. Estimated delivery: Friday, March 14. "
            "Items: 1x USB-C Hub (7-in-1), 1x Laptop Stand Aluminium. Track your package using the link below. "
            "If you have any issues, visit our Help Centre or contact customer support."
        ),
    },
    {
        "ID": 2002,
        "Sender": "LinkedIn",
        "Subject": "You have 4 new connection requests this week",
        "Date": "2026-03-12",
        "Content": (
            "Hi Fabrizio, you have 4 people waiting to connect with you on LinkedIn. Don't keep them waiting! "
            "Check who wants to connect and grow your professional network. You also have 2 unread messages and "
            "12 new profile views this week. Log in to see who's been looking at your profile."
        ),
    },
    {
        "ID": 2003,
        "Sender": "HR Department",
        "Subject": "Reminder: Q1 Performance Review deadline is Friday",
        "Date": "2026-03-11",
        "Content": (
            "Dear colleagues, this is a friendly reminder that Q1 self-assessment forms are due by Friday, March 14. "
            "Please ensure you have completed your objectives section and submitted to your line manager. "
            "The 360-degree feedback window opens next Monday. If you have any questions, contact hr@company.com."
        ),
    },
    {
        "ID": 2004,
        "Sender": "IT Support",
        "Subject": "Scheduled Maintenance: VPN services offline Mar 14, 02:00–04:00 UTC",
        "Date": "2026-03-11",
        "Content": (
            "IT will perform scheduled maintenance on VPN services on Friday, March 14, between 02:00 and 04:00 UTC. "
            "During this window, remote access will be unavailable. Please save your work and disconnect before the "
            "maintenance window begins. Contact itsupport@company.com if you experience issues after the window."
        ),
    },
    {
        "ID": 2005,
        "Sender": "Spotify",
        "Subject": "Your Discover Weekly is ready — 30 new tracks",
        "Date": "2026-03-10",
        "Content": (
            "Your personalised Discover Weekly playlist for this week is now available. We have picked 30 new songs "
            "based on your recent listening history. Highlights this week include artists you might not have heard yet. "
            "Open Spotify and start listening now. Enjoy your music!"
        ),
    },
    {
        "ID": 2006,
        "Sender": "Google Workspace",
        "Subject": "Storage alert: you have used 85% of your Drive storage",
        "Date": "2026-03-10",
        "Content": (
            "Your Google account fabri@gmail.com has used 12.75 GB out of 15 GB of free storage. "
            "When you run out of storage, you will not be able to send or receive emails, and Google Drive "
            "file syncing will stop. Consider upgrading to Google One or deleting large files to free up space."
        ),
    },
    {
        "ID": 2007,
        "Sender": "Facilities",
        "Subject": "Building access restricted — Floor 3 HVAC works, Mar 14",
        "Date": "2026-03-11",
        "Content": (
            "Facilities management will be conducting HVAC maintenance on Floor 3 on Friday, March 14. "
            "Meeting rooms 3A through 3F will be inaccessible between 08:00 and 13:00. Please rebook any meetings "
            "scheduled in these rooms. Rooms on Floors 1 and 2 remain fully available. We apologise for any inconvenience."
        ),
    },
    {
        "ID": 2008,
        "Sender": "Netflix",
        "Subject": "New this week on Netflix: 5 shows you'll love",
        "Date": "2026-03-12",
        "Content": (
            "Based on what you've been watching, we think you'll enjoy these new arrivals this week. "
            "Don't miss the new season of your favourite drama series, plus a brand new documentary and a "
            "critically acclaimed film just added to the catalogue. Open Netflix and start watching now."
        ),
    },
    {
        "ID": 2009,
        "Sender": "Barclays",
        "Subject": "Your March account statement is now available",
        "Date": "2026-03-12",
        "Content": (
            "Your monthly account statement for March 2026 is now available in your online banking portal. "
            "Log in to review your transactions, download the PDF statement, or set up alerts for future activity. "
            "If you have any questions about your account, please contact us through the app or call 0800 400 100."
        ),
    },
    {
        "ID": 2010,
        "Sender": "Microsoft Teams",
        "Subject": "You missed a call from Sarah Chen in #strategy-team",
        "Date": "2026-03-12",
        "Content": (
            "Sarah Chen tried to reach you on Microsoft Teams at 10:14 AM. You also have 3 unread messages "
            "in the #strategy-team channel and 1 direct message from Alex Rossi. "
            "The Q2 planning meeting has been rescheduled to Thursday at 3:00 PM. Check your calendar for details."
        ),
    },
    {
        "ID": 2011,
        "Sender": "Uber Eats",
        "Subject": "Your lunch order from Itsu is on its way!",
        "Date": "2026-03-11",
        "Content": (
            "Great news! Your order from Itsu has been picked up by your delivery partner and is on its way to you. "
            "Estimated arrival: 12:45 PM. Your order: Salmon Sashimi (8pc), Miso Soup, Green Tea. "
            "Track your delivery in real time using the Uber Eats app. Enjoy your meal!"
        ),
    },
    {
        "ID": 2012,
        "Sender": "Lufthansa",
        "Subject": "Flight booking confirmation: LH 1234 London–Frankfurt, Mar 18",
        "Date": "2026-03-11",
        "Content": (
            "Your Lufthansa flight booking is confirmed. Flight LH 1234 departs London Heathrow (LHR) on Tuesday, "
            "March 18 at 07:50 AM and arrives in Frankfurt (FRA) at 10:25 AM. Booking reference: ABC123. "
            "Online check-in opens 23 hours before departure. Please ensure your travel documents are up to date."
        ),
    },
    {
        "ID": 2013,
        "Sender": "Slack",
        "Subject": "You have 5 unread messages in #general and #product",
        "Date": "2026-03-12",
        "Content": (
            "You have unread messages waiting for you on Slack: 3 in #general and 2 in #product-roadmap. "
            "Maria left a comment on your last message and tagged you in a thread. "
            "Don't miss the team standup at 9:30 AM — a reminder has been added to your calendar."
        ),
    },
    {
        "ID": 2014,
        "Sender": "DocuSign",
        "Subject": "Action required: please sign the NDA for Project Horizon",
        "Date": "2026-03-10",
        "Content": (
            "You have a document waiting for your signature. Sender: Legal Department. Document: Non-Disclosure "
            "Agreement — Project Horizon. Please review and sign by March 13, 2026. Click the button below to "
            "review the document in DocuSign. If you have questions, contact legal@company.com."
        ),
    },
]

all_emails = financial_emails + noise_emails
df = pd.DataFrame(all_emails)
df = df.sort_values(by=["Date", "ID"], ascending=[False, True]).reset_index(drop=True)
df.to_csv("data.csv", index=False)

print(
    f"Created data.csv with {len(financial_emails)} financial + {len(noise_emails)} noise emails "
    f"({len(df)} total)."
)
+