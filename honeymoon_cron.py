import os
import pandas as pd
import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from prawcore.exceptions import NotFound, Redirect

# 1) Reddit setup
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# 2) Keywords & subreddits
KEYWORDS = [
    "honeymoon", "just married", "getting married", "destination wedding",
    "romantic getaway", "couples trip", "post-wedding vacation", "wedding trip"
]
SUBS = [
    "travel", "weddingplanning", "JustEngaged", "Weddings",
    "HoneymoonTravel", "HoneymoonIdeas", "Marriage", "relationship_advice"
]

# 3) Fetch & filter
def fetch_leads():
    leads = []
    for sub in SUBS:
        try:
            # force lookup to catch NotFound or Redirect
            _ = reddit.subreddit(sub).id
            submissions = reddit.subreddit(sub).new(limit=50)
        except (NotFound, Redirect):
            continue

        for post in submissions:
            text = (post.title + " " + (post.selftext or "")).lower()
            if any(k in text for k in KEYWORDS):
                leads.append({
                    "Subreddit": sub,
                    "Title":      post.title,
                    "Author":     post.author.name if post.author else "N/A",
                    "URL":        f"https://reddit.com{post.permalink}"
                })

    return pd.DataFrame(leads)

# 4) Google Sheets export
def export_to_sheets(df):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-<your-json-filename>.json",  # replace with your actual JSON key name
        scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("honeymoon spreadsheet").sheet1
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

# 5) Run on schedule
if __name__ == "__main__":
    df = fetch_leads()
    if not df.empty:
        export_to_sheets(df)
