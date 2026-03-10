import pandas as pd

financial_emails = [
    {
        "ID": 1,
        "Sender": "Bloomberg",
        "Subject": "NVIDIA Extends Rally as AI Chip Demand Surges",
        "Date": "2026-02-13",
        "Content": (
            "NVIDIA shares continued their upward momentum as investors responded to stronger-than-expected "
            "demand for advanced AI accelerators across cloud and enterprise markets. Several investment banks "
            "raised their price targets, citing improved visibility into NVIDIA's data-center revenue pipeline. "
            "Executives from major cloud providers have emphasized that AI infrastructure remains their highest-priority "
            "capital expenditure category for 2026. With demand outpacing supply in several regions, analysts expect "
            "continued volatility but maintain a constructive outlook for the company's long-term growth trajectory."
        ),
    },
    {
        "ID": 2,
        "Sender": "Reuters",
        "Subject": "Microsoft Advances AI Integration Across Enterprise Cloud",
        "Date": "2026-02-12",
        "Content": (
            "Microsoft shares traded higher after the company announced expanded AI capabilities across its enterprise "
            "cloud portfolio. The update includes new model-hosting options, enhanced security layers, and improved "
            "cost-optimization tools. Analysts noted that Microsoft's strategy continues to emphasize vertical-specific "
            "solutions, particularly in healthcare, financial services, and manufacturing. Investors reacted positively "
            "to comments from executives indicating that AI-related revenue growth remains ahead of internal forecasts."
        ),
    },
    {
        "ID": 3,
        "Sender": "Reuters",
        "Subject": "OPEC+ Signals Cautious Approach to Production Adjustments",
        "Date": "2026-02-13",
        "Content": (
            "Oil markets traded in a narrow range after OPEC+ officials signaled a cautious approach to future "
            "production adjustments. Delegates indicated that the group remains focused on maintaining market stability "
            "amid uneven global demand recovery. Traders are closely watching upcoming economic indicators that could "
            "influence demand forecasts for the second quarter. Market participants expect the group to revisit its "
            "strategy at the next ministerial meeting."
        ),
    },
    {
        "ID": 4,
        "Sender": "Bloomberg",
        "Subject": "Brent Crude Edges Higher on Supply Tightness",
        "Date": "2026-02-12",
        "Content": (
            "Brent crude prices moved higher as traders assessed tightening supply conditions across key exporting regions. "
            "Several unplanned outages at offshore facilities contributed to reduced shipments, prompting refiners to seek "
            "alternative sources. Market participants also pointed to declining inventories in Europe and Asia as evidence "
            "of a more constrained environment. Investors will be watching upcoming OPEC+ communications for signals on "
            "whether the group intends to offset the recent disruptions with additional production."
        ),
    },
    {
        "ID": 5,
        "Sender": "Bloomberg",
        "Subject": "Fed Officials Signal Patience Ahead of Next Rate Decision",
        "Date": "2026-02-13",
        "Content": (
            "Federal Reserve officials signaled a patient approach to upcoming policy decisions, citing the need for "
            "additional data to assess the trajectory of inflation and labor-market conditions. Analysts noted that "
            "policymakers are increasingly focused on balancing the risks of easing too early against the potential "
            "costs of maintaining restrictive conditions for too long. Treasury yields moved slightly lower following "
            "the comments, reflecting expectations that the Fed may delay any policy adjustments until later in the year."
        ),
    },
    {
        "ID": 6,
        "Sender": "FactSet",
        "Subject": "Inflation Data Shows Gradual Cooling Across Key Sectors",
        "Date": "2026-02-11",
        "Content": (
            "New inflation data indicates gradual cooling across several key sectors, providing cautious optimism for "
            "policymakers. Core goods prices continued their downward trend, supported by improved supply-chain efficiency. "
            "Services inflation, while still elevated, showed signs of easing as wage growth moderated. Bond markets "
            "reacted positively to the report, with yields declining across the curve. Economists noted that while the "
            "data supports the case for eventual policy easing, the Federal Reserve is likely to maintain a cautious stance."
        ),
    },
    {
        "ID": 7,
        "Sender": "Bloomberg",
        "Subject": "Global Bond Markets Steady Ahead of Key Fed Testimony",
        "Date": "2026-02-11",
        "Content": (
            "Global bond markets traded steadily as investors awaited key testimony from Federal Reserve leadership. "
            "Analysts noted that recent economic data has provided mixed signals, contributing to uncertainty around "
            "the timing of potential policy adjustments. Treasury yields remained range-bound, while European and Asian "
            "bond markets showed similar stability. Many expect policymakers to maintain a cautious tone, emphasizing "
            "the importance of sustained progress toward inflation targets."
        ),
    },
    {
        "ID": 8,
        "Sender": "Reuters",
        "Subject": "Retailers Report Steady Foot Traffic Despite Economic Uncertainty",
        "Date": "2026-02-10",
        "Content": (
            "Major retailers reported steady foot traffic in early February, suggesting that consumer spending remains "
            "resilient despite broader economic uncertainty. Several chains highlighted improved inventory management "
            "as a key factor supporting margins, particularly in apparel and home goods. Economists cautioned that "
            "consumer sentiment could shift if labor-market conditions weaken or inflation reaccelerates. For now, "
            "retailers appear focused on maintaining operational efficiency and optimizing product assortments."
        ),
    },
]

noise_emails = [
    {
        "ID": 9,
        "Sender": "Amazon",
        "Subject": "Your order #114-8273641 has shipped",
        "Date": "2026-02-13",
        "Content": (
            "Hi Fabrizio, your order has been dispatched and is on its way. Estimated delivery: Wednesday, February 15. "
            "Items: 1x USB-C Hub (7-in-1), 1x Laptop Stand Aluminium. Track your package using the link below. "
            "If you have any issues, visit our Help Centre or contact customer support."
        ),
    },
    {
        "ID": 10,
        "Sender": "LinkedIn",
        "Subject": "You have 4 new connection requests this week",
        "Date": "2026-02-13",
        "Content": (
            "Hi Fabrizio, you have 4 people waiting to connect with you on LinkedIn. Don't keep them waiting! "
            "Check who wants to connect and grow your professional network. You also have 2 unread messages and "
            "12 new profile views this week. Log in to see who's been looking at your profile."
        ),
    },
    {
        "ID": 11,
        "Sender": "HR Department",
        "Subject": "Reminder: Q1 Performance Review deadline is Friday",
        "Date": "2026-02-12",
        "Content": (
            "Dear colleagues, this is a friendly reminder that Q1 self-assessment forms are due by Friday, February 14. "
            "Please ensure you have completed your objectives section and submitted to your line manager. "
            "The 360-degree feedback window opens next Monday. If you have any questions, contact hr@company.com."
        ),
    },
    {
        "ID": 12,
        "Sender": "IT Support",
        "Subject": "Scheduled Maintenance: VPN services offline Feb 14, 02:00-04:00 UTC",
        "Date": "2026-02-12",
        "Content": (
            "IT will perform scheduled maintenance on VPN services on Friday, February 14, between 02:00 and 04:00 UTC. "
            "During this window, remote access will be unavailable. Please save your work and disconnect before the "
            "maintenance window begins. Contact itsupport@company.com if you experience issues after the window."
        ),
    },
    {
        "ID": 13,
        "Sender": "Spotify",
        "Subject": "Your Discover Weekly is ready",
        "Date": "2026-02-10",
        "Content": (
            "Your personalised Discover Weekly playlist for this week is now available. We have picked 30 new songs "
            "based on your recent listening history. Highlights this week include artists you might not have heard yet. "
            "Open Spotify and start listening now. Enjoy your music!"
        ),
    },
    {
        "ID": 14,
        "Sender": "Google Workspace",
        "Subject": "Storage alert: you have used 85% of your Drive storage",
        "Date": "2026-02-11",
        "Content": (
            "Your Google account fabri@gmail.com has used 12.75 GB out of 15 GB of free storage. "
            "When you run out of storage, you will not be able to send or receive emails, and Google Drive "
            "file syncing will stop. Consider upgrading to Google One or deleting large files to free up space."
        ),
    },
    {
        "ID": 15,
        "Sender": "Facilities",
        "Subject": "Building access restricted - Floor 3 HVAC works, Feb 14",
        "Date": "2026-02-11",
        "Content": (
            "Facilities management will be conducting HVAC maintenance on Floor 3 on Friday, February 14. "
            "Meeting rooms 3A through 3F will be inaccessible between 08:00 and 13:00. Please rebook any meetings "
            "scheduled in these rooms. Rooms on Floors 1 and 2 remain fully available. We apologise for any inconvenience."
        ),
    },
]

all_emails = financial_emails + noise_emails
df = pd.DataFrame(all_emails)
df = df.sort_values(by=["Date", "ID"], ascending=[False, True]).reset_index(drop=True)
df.to_csv("data.csv", index=False)

print(f"Created data.csv with {len(financial_emails)} financial + {len(noise_emails)} noise emails ({len(df)} total).")
