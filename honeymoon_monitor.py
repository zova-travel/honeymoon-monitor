import streamlit as st
import praw
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Reddit API
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

import prawcore

for name in ["travel", "weddingplanning", "honeymoon", "solotravel", "IWantOut"]:
    try:
        reddit.subreddit(name).about()
        print(f"✅ r/{name} exists")
    except prawcore.exceptions.NotFound:
        print(f"❌ r/{name} NOT FOUND")


# Keywords to detect honeymoon intent
KEYWORDS = [
    "honeymoon", "just married", "getting married", "destination wedding",
    "romantic getaway", "couples trip", "post-wedding vacation", "wedding trip"
]

# Function to fetch and filter posts
from prawcore import NotFound

def get_honeymoon_posts(subreddit_name="travel"):
    posts = []
    sub_name = subreddit_name.lower()                  # normalize
    try:
        submissions = reddit.subreddit(sub_name).new(limit=50)
    except NotFound:
        st.warning(f"r/{sub_name} not found. Skipping.")
        return pd.DataFrame(posts)

    for submission in submissions:
        text = (submission.title + " " + (submission.selftext or "")).lower()
        if any(keyword in text for keyword in KEYWORDS):
            posts.append({
                "Title": submission.title,
                "Author": submission.author.name if submission.author else "N/A",
                "URL": f"https://reddit.com{submission.permalink}"
            })
    return pd.DataFrame(posts)


# Function to export DataFrame to Google Sheets
def export_to_google_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Honeymoon Leads").sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# Streamlit UI
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")
st.title("🌴 Honeymoon Travel Leads Monitor")

# Subreddit selection
TARGET_SUBREDDITS = ["travel", "weddingplanning", "honeymoon", "solotravel", "IWantOut"]
sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)
df  = get_honeymoon_posts(sub.lower())

# Fetch and display posts
df = get_honeymoon_posts(sub)
st.dataframe(df)

# Export button
if not df.empty:
    if st.button("Export to Google Sheets"):
        export_to_google_sheet(df)
        st.success(f"Exported {len(df)} leads to Google Sheets!")
    else:
        st.info("Click above to export leads to Google Sheets.")
