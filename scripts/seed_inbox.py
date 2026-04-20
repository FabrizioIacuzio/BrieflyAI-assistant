"""
seed_inbox.py — Send realistic mock financial emails to yourself for testing.

Usage:
    python scripts/seed_inbox.py --to you@gmail.com --count 30

Requires a Gmail App Password:
    1. Go to myaccount.google.com/security
    2. Enable 2-Step Verification (if not already)
    3. Search "App passwords" → create one for "Mail"
    4. Use that 16-char password as --password (or set GMAIL_APP_PASSWORD env var)
"""

import argparse
import os
import random
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SENDERS = [
    ("Bloomberg Markets", "noreply@bloomberg.com"),
    ("Reuters Finance", "newsletters@reuters.com"),
    ("CNBC Daily Open", "newsletters@cnbc.com"),
    ("Morning Brew", "hello@morningbrew.com"),
    ("Axios Markets", "markets@axios.com"),
    ("The Wall Street Journal", "newsletters@wsj.com"),
    ("Financial Times", "newsletters@ft.com"),
    ("MarketWatch", "newsletters@marketwatch.com"),
    ("Seeking Alpha", "news@seekingalpha.com"),
    ("Goldman Sachs Research", "research@gs.com"),
]

EMAILS = [
    {
        "subject": "Fed Holds Rates Steady, Signals Two Cuts in 2025",
        "body": """The Federal Reserve left interest rates unchanged at 5.25%–5.50% on Wednesday, as widely expected, while officials maintained their projection of two rate cuts this year despite persistent inflation pressures.

Chair Jerome Powell emphasized the committee needs "greater confidence" that inflation is moving sustainably toward the 2% target before easing policy. Core PCE inflation stood at 2.8% in the latest reading, above target but trending lower.

Markets responded positively, with the S&P 500 rising 0.7% and the 10-year Treasury yield falling 6 basis points to 4.31%. The dollar weakened slightly against major currencies.

"The economy is strong. We don't need to be in a hurry to adjust our policy stance," Powell told reporters at the post-meeting press conference.

Three officials now pencil in just one cut this year, up from one at the March meeting, suggesting a hawkish tilt within the committee. Fed funds futures now price in the first cut in September with 68% probability.""",
    },
    {
        "subject": "NVIDIA Surges 8% After Blowout Q1 Earnings Beat",
        "body": """NVIDIA Corporation reported first-quarter revenue of $26.0 billion, surging 262% year-over-year and crushing analyst estimates of $24.6 billion, driven by insatiable demand for its H100 and H200 AI chips.

Data center revenue hit $22.6 billion, up 427% from the prior year, as hyperscalers including Microsoft, Google, Amazon, and Meta continue to race to build AI infrastructure. Gross margins expanded to a record 78.4%.

CEO Jensen Huang announced the company is ramping production of its next-generation Blackwell architecture ahead of schedule, with "several billion dollars" in Blackwell revenue expected in Q2.

Shares rose 8.2% in after-hours trading to $950, pushing NVIDIA's market capitalization above $2.3 trillion.

"The next industrial revolution has begun," Huang said on the earnings call. "Companies and countries are partnering with NVIDIA to shift the world's installed base of data centers from general-purpose computing to accelerated computing and AI."

Analysts at Goldman Sachs raised their price target to $1,100 from $875.""",
    },
    {
        "subject": "Oil Climbs to $87 on OPEC+ Supply Discipline, Middle East Tensions",
        "body": """Brent crude futures rose $1.84, or 2.2%, to settle at $87.40 per barrel on Thursday as OPEC+ members reaffirmed their commitment to output cuts and geopolitical risk premiums widened following reports of drone strikes on key refinery infrastructure.

Saudi Arabia confirmed it would maintain voluntary cuts of 1 million barrels per day through at least Q3, while Russia pledged continued compliance with its 500,000 bpd reduction. The cartel's next formal meeting is scheduled for June 2.

EIA data released Wednesday showed a surprise draw of 3.2 million barrels in U.S. crude stockpiles versus expectations for a 1.1 million barrel build, adding upward pressure to prices.

Goldman Sachs maintained its year-end Brent forecast of $90 per barrel, citing "structural underinvestment in upstream capacity" and resilient emerging market demand, particularly from India and China.

Energy stocks outperformed the broader market, with the XLE ETF gaining 1.4%. Exxon Mobil and Chevron both rose more than 2%.""",
    },
    {
        "subject": "CPI Inflation Cools to 3.4% in April, Core Still Sticky",
        "body": """U.S. consumer prices rose 3.4% year-over-year in April, down from 3.5% in March and in line with economist expectations, offering modest relief to Federal Reserve officials watching for evidence that inflation is resuming its downward trend.

Core CPI, which excludes food and energy, rose 3.6% annually, matching forecasts and decelerating from 3.8% the prior month. On a monthly basis, both headline and core CPI increased 0.3%.

Shelter costs, which account for roughly one-third of the CPI basket, remained the primary driver of elevated inflation, rising 5.5% annually. However, rent of primary residence showed early signs of softening, up just 0.4% month-over-month.

"Today's report is consistent with the disinflation story remaining intact, even if progress is painfully slow," said Michael Gapen, chief U.S. economist at Bank of America.

Treasury yields fell sharply on the release. The 2-year note yield dropped 9 basis points to 4.72%, while the 10-year fell 7 basis points to 4.35%. S&P 500 futures jumped 0.8%.""",
    },
    {
        "subject": "Bitcoin Surges Past $68,000 as ETF Inflows Accelerate",
        "body": """Bitcoin climbed above $68,000 for the first time in three weeks on Thursday, extending its recovery as spot ETF products listed in the United States recorded their sixth consecutive day of positive net inflows.

The 11 U.S.-listed bitcoin ETFs attracted $886 million in combined inflows on Wednesday, led by BlackRock's iShares Bitcoin Trust (IBIT) with $523 million, according to data from BitMEX Research. Total assets under management across all spot bitcoin ETFs now exceed $58 billion.

Ethereum also rallied, gaining 4.2% to trade near $3,100, buoyed by growing optimism that U.S. regulators may approve spot ether ETFs as early as this summer.

"The structural demand shift from institutional adoption via ETFs is fundamentally different from previous bull cycles," said analysts at JPMorgan's digital assets research team.

Crypto-related equities surged in sympathy. Coinbase Global rose 6.1%, MicroStrategy gained 7.8%, and Marathon Digital Holdings jumped 9.3%.""",
    },
    {
        "subject": "JPMorgan Beats Q1 Estimates; CEO Dimon Warns of 'Stormy' Economic Outlook",
        "body": """JPMorgan Chase reported first-quarter net income of $13.4 billion, or $4.44 per share, beating analyst estimates of $4.11 per share, as investment banking revenue surged and net interest income remained resilient despite rate uncertainty.

Investment banking fees jumped 21% year-over-year to $2.0 billion, with debt underwriting up 36% and M&A advisory revenue nearly doubling. The firm's trading division posted revenue of $8.1 billion, up 3% from a year earlier.

CEO Jamie Dimon struck a cautious tone in his shareholder letter, warning that the U.S. faces a "confluence of risks" including persistent inflation, rising geopolitical tensions, and high fiscal deficits. "I would say this is dangerous and complicated," Dimon wrote.

The bank maintained its full-year net interest income guidance of approximately $89 billion, down from $89.3 billion previously. Shares fell 4.1% as investors focused on the cautious outlook rather than the earnings beat.

Chief Financial Officer Jeremy Barnum acknowledged the "unusually high" level of geopolitical and macroeconomic uncertainty, noting that loan growth has "modestly softened" in recent weeks.""",
    },
    {
        "subject": "ECB Cuts Rates for First Time Since 2019 in Historic Move",
        "body": """The European Central Bank cut its key interest rates by 25 basis points on Thursday, becoming the first major central bank to ease monetary policy in the current cycle, as inflation in the eurozone approaches the 2% target.

The deposit facility rate was lowered to 3.75% from 4.0%, the highest level since the euro's inception. ECB President Christine Lagarde stressed the decision was "not pre-committing to a particular rate path" and future moves would be data-dependent.

Eurozone inflation fell to 2.4% in April from a peak of 10.6% in October 2022, while core inflation moderated to 2.7%. However, services inflation remained elevated at 3.7%, complicating the outlook for further easing.

Markets had fully priced in the June cut but pared expectations for subsequent reductions following Lagarde's comments. Traders now see fewer than two additional cuts in 2024, down from three expected before the meeting.

The euro weakened 0.3% against the dollar to 1.0845. European equities closed mixed, with the DAX rising 0.2% and the CAC 40 falling 0.1%.""",
    },
    {
        "subject": "Apple Reports Declining iPhone Sales but Beats on Services Revenue",
        "body": """Apple Inc. reported fiscal second-quarter revenue of $90.8 billion, narrowly beating analyst expectations of $90.0 billion, as record services revenue offset a 10% decline in iPhone sales that reflected weak demand in China.

Services revenue — which includes the App Store, Apple TV+, Apple Music, and iCloud — hit an all-time high of $23.9 billion, up 14.2% year-over-year. CEO Tim Cook highlighted that the installed base of active Apple devices reached a new record during the quarter.

iPhone revenue fell to $45.96 billion from $51.33 billion a year ago, with Greater China revenue declining 8.1% to $16.37 billion as competition from domestic brands like Huawei intensified.

Apple announced a record $110 billion share buyback program, the largest in the company's history, sending shares up 7% in after-hours trading.

"We are very bullish on AI. We will be sharing more details at WWDC in June," Cook told analysts, fueling speculation about Apple's artificial intelligence strategy ahead of its annual developer conference.""",
    },
    {
        "subject": "U.S. Payrolls Add 175,000 Jobs in April, Unemployment Rises to 3.9%",
        "body": """The U.S. economy added 175,000 jobs in April, the fewest in six months and well below the 240,000 consensus estimate, while the unemployment rate ticked up to 3.9% from 3.8%, providing the Federal Reserve with some cover to begin cutting rates later this year.

Average hourly earnings rose 0.2% month-over-month and 3.9% year-over-year, the slowest annual pace since June 2021, signaling that wage pressures are gradually easing. The labor force participation rate held steady at 62.7%.

Hiring was led by healthcare (+56,000), government (+8,000), and transportation and warehousing (+22,000). Manufacturing shed 8,000 jobs for the second consecutive month, reflecting weaker factory activity.

Treasury yields plunged on the soft report, with the 10-year note dropping 10 basis points to 4.44% and the 2-year falling 14 basis points to 4.81% — its largest single-day decline since March 2023.

"This is exactly the kind of data the Fed needed to see," said Neil Dutta, head of U.S. economics at Renaissance Macro Research. "The door to a September cut is now wide open."

The S&P 500 rose 1.1% and the Nasdaq climbed 2.0%.""",
    },
    {
        "subject": "Goldman Sachs Raises S&P 500 Year-End Target to 5,600",
        "body": """Goldman Sachs strategists raised their year-end S&P 500 price target to 5,600 from 5,200 on Monday, citing stronger-than-expected corporate earnings growth and the prospect of Federal Reserve rate cuts in the second half of the year.

The bank's chief U.S. equity strategist David Kostin cited earnings per share growth of approximately 11% this year, driven by margin expansion from AI productivity gains and resilient consumer spending. The revised target implies about 4% upside from current levels.

"We raise our EPS estimate to $241 for 2024 and $256 for 2025," Kostin wrote in a note to clients. "The outlook for corporate profits has improved meaningfully since the start of the year."

Goldman also raised its 12-month target to 5,900, reflecting confidence in a soft economic landing. The bank now ranks as among the most bullish on Wall Street, alongside Yardeni Research's 5,800 target.

Technology, communication services, and healthcare are Goldman's preferred sectors heading into the second half of the year. The firm maintains underweight ratings on utilities and real estate.""",
    },
    {
        "subject": "China GDP Grows 5.3% in Q1, Beats Expectations but Property Drag Persists",
        "body": """China's economy grew 5.3% year-on-year in the first quarter, surpassing the 4.6% consensus forecast, but economists cautioned the headline figure masked ongoing structural weakness in the country's embattled property sector.

Industrial output and net exports drove the outperformance, with manufacturing activity — particularly in electric vehicles, solar panels, and consumer electronics — expanding rapidly. Retail sales growth, however, remained subdued at 4.7%, suggesting domestic consumption has yet to fully recover.

The property sector continued to weigh heavily, with investment in real estate falling 9.5% year-to-date through March. New home prices fell for the ninth consecutive month in March, declining 0.3% from February.

Beijing reiterated its approximately 5% full-year growth target, widely seen as achievable but requiring continued policy support. The People's Bank of China is expected to cut the reserve requirement ratio by another 25 basis points in the second half.

MSCI China rose 1.4% on the data, while Hong Kong's Hang Seng index gained 1.8%. Emerging market funds recorded net inflows for the third consecutive week.""",
    },
    {
        "subject": "Microsoft Cloud Revenue Jumps 23% as AI Copilot Adoption Accelerates",
        "body": """Microsoft reported fiscal third-quarter revenue of $61.9 billion, up 17% year-over-year and above analyst estimates of $60.8 billion, as its Azure cloud platform and AI-powered Copilot products drove accelerating enterprise adoption.

Azure and other cloud services grew 31% in constant currency terms, reaccelerating from 28% in the prior quarter. Management disclosed that AI services contributed 7 percentage points to Azure's growth, up from 6 points last quarter.

Microsoft 365 Copilot — the AI assistant integrated into Word, Excel, and Teams — now has over 1.8 million paid seats across more than 13,000 enterprise customers, according to CEO Satya Nadella.

"Every customer conversation I have starts with AI," Nadella told analysts. "We are seeing AI go from autopilot to copilot to actually agents that can accomplish tasks end to end."

Capital expenditure came in at $14.0 billion for the quarter, ahead of the $13.1 billion estimate, reflecting continued heavy investment in AI data center infrastructure. Management guided for capex to increase further in fiscal 2025.

Shares rose 4.2% in extended trading to $420.""",
    },
    {
        "subject": "Treasury Yields Hit 5% as Deficit Concerns Mount",
        "body": """The 10-year U.S. Treasury yield crossed 5% for the first time since 2007 on Tuesday, driven by a combination of stronger-than-expected economic data, hawkish Federal Reserve commentary, and growing investor concern about the sustainability of the federal government's fiscal trajectory.

The Congressional Budget Office projects the federal deficit will reach $1.6 trillion in fiscal year 2024, while the national debt has surpassed $34 trillion. The Treasury Department is expected to increase coupon auction sizes again when it announces its quarterly refunding plans next week.

"The term premium has clearly returned to bond markets," said strategists at Deutsche Bank. "Investors are demanding more compensation to hold long-duration government debt."

Mortgage rates, closely tied to 10-year Treasury yields, rose to 7.8% on 30-year fixed loans, the highest since 2000, putting further pressure on the housing market.

Stocks sold off sharply as yields rose, with the S&P 500 falling 1.6% and the Nasdaq shedding 1.9%. Utilities, REITs, and other rate-sensitive sectors bore the brunt of the selling.""",
    },
    {
        "subject": "Warren Buffett Dumps $17B in BofA Stock as Berkshire Cash Pile Hits Record",
        "body": """Warren Buffett's Berkshire Hathaway has sold approximately $17 billion worth of Bank of America shares over the past three months, reducing its stake to below 10% — the threshold below which it no longer needs to disclose transactions within two business days.

The sales, disclosed in SEC filings, reduced Berkshire's BofA position from approximately 1.03 billion shares to around 775 million, generating cumulative proceeds in excess of $6.2 billion at current prices. Bank of America remains Berkshire's second-largest equity holding after Apple.

Berkshire's total cash and Treasury bill holdings reached a record $277 billion at the end of the second quarter, prompting speculation about what Buffett is waiting to buy — or whether he sees elevated risks ahead.

Analysts noted the sales came amid high equity valuations, elevated interest rates, and significant geopolitical uncertainty. Buffett has historically trimmed large positions when he believes stocks are richly valued relative to their intrinsic worth.

Bank of America shares fell 2.1% on heavy volume. The stock has risen 18% year-to-date, one of the best performers among major U.S. banks.""",
    },
    {
        "subject": "Euro Zone Manufacturing PMI Signals Deepening Recession Risk",
        "body": """The HCOB Eurozone Manufacturing PMI fell to 45.7 in April, down from 46.1 in March and remaining deeply in contraction territory, as factory output declined for the 22nd consecutive month amid weak demand and elevated energy costs.

Germany's PMI deteriorated to 42.5, its lowest reading since January, while France slipped to 44.2. Only Spain and Ireland recorded readings above the 50-point threshold separating growth from contraction.

New orders continued to fall sharply, with the new orders sub-index at 44.3. Backlogs of work declined for the 24th straight month, and input inventories fell as firms destocked aggressively. Employment fell for the eighth consecutive month.

"European manufacturing is still a long way from recovery," said Cyrus de la Rubia, chief economist at Hamburg Commercial Bank. "The fundamental weakness in demand, both domestically and from key export markets, shows no signs of reversing."

The euro fell 0.2% against the dollar. European auto stocks led declines, with Volkswagen falling 2.3%, Stellantis down 1.8%, and BMW losing 1.5% on the session.""",
    },
]


def make_email(sender_name: str, sender_addr: str, to_addr: str,
               subject: str, body: str, date_offset_days: int = 0) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    date = datetime.now() - timedelta(days=date_offset_days)
    msg["Date"] = date.strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg["From"] = f"{sender_name} <{sender_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = subject

    html = f"""<html><body>
    <div style="font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:20px">
    <h2 style="color:#1a1a2e;font-size:20px">{subject}</h2>
    <div style="color:#333;line-height:1.7;font-size:15px">
    {"<br><br>".join(f"<p>{p.strip()}</p>" for p in body.strip().split(chr(10)+chr(10)) if p.strip())}
    </div>
    <hr style="margin-top:30px;border:1px solid #eee">
    <p style="color:#999;font-size:12px">
    {sender_name} · Financial Newsletter ·
    <a href="#" style="color:#999">Unsubscribe</a>
    </p>
    </div></body></html>"""

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def main():
    parser = argparse.ArgumentParser(description="Seed Gmail inbox with mock financial emails")
    parser.add_argument("--to",       required=True,  help="Your Gmail address")
    parser.add_argument("--user",     default=None,   help="SMTP user (defaults to --to)")
    parser.add_argument("--password", default=None,   help="Gmail App Password (or set GMAIL_APP_PASSWORD)")
    parser.add_argument("--count",    type=int, default=20, help="Number of emails to send (max 60)")
    args = parser.parse_args()

    password = args.password or os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        print("ERROR: Provide --password or set GMAIL_APP_PASSWORD env var")
        print("Get an App Password at: myaccount.google.com/apppasswords")
        raise SystemExit(1)

    smtp_user = args.user or args.to
    count = min(args.count, 60)

    # Build send list by cycling through templates
    pool = EMAILS * (count // len(EMAILS) + 1)
    random.shuffle(pool)
    to_send = pool[:count]

    print(f"Connecting to smtp.gmail.com:587 as {smtp_user}...")
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, password)
        print(f"Logged in. Sending {count} emails to {args.to}...\n")

        for i, template in enumerate(to_send):
            sender_name, sender_addr = random.choice(SENDERS)
            offset = random.randint(0, 6)
            msg = make_email(
                sender_name, sender_addr, args.to,
                template["subject"], template["body"],
                date_offset_days=offset,
            )
            server.send_message(msg)
            print(f"  [{i+1:02d}/{count}] {template['subject'][:60]}...")
            time.sleep(0.3)

    print(f"\nDone! {count} emails sent to {args.to}.")
    print("They'll appear in Gmail within seconds.")


if __name__ == "__main__":
    main()
