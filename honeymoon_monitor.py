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

from prawcore.exceptions import NotFound

for name in ["travel", "weddingplanning", "honeymoon", "solotravel", "IWantOut"]:
    try:
        # Accessing .id will force PRAW to fetch and raise 404 if not found
        _ = reddit.subreddit(name).id
        print(f"✅ r/{name} exists")
    except NotFound:
        print(f"❌ r/{name} NOT FOUND")


# Keywords to detect honeymoon intent
KEYWORDS = [
    "honeymoon", "just married", "getting married", "destination wedding",
    "romantic getaway", "couples trip", "post-wedding vacation", "wedding trip"
]

# Function to fetch and filter posts
from prawcore.exceptions import NotFound   
def get_honeymoon_posts(subreddit_name="travel"):
    posts = []
    sub_name = subreddit_name.lower()

    try:
        # Force a lookup to catch 404s early
        _ = reddit.subreddit(sub_name).id
        submissions = reddit.subreddit(sub_name).new(limit=50)
    except NotFound:
        st.warning(f"r/{sub_name} not found or inaccessible—skipping.")
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
    # Match your sheet’s exact name:
    sheet = client.open("honeymoon spreadsheet").sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())


# Streamlit UI
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")
st.title("🌴 Honeymoon Travel Leads Monitor")

# Subreddit selection
TARGET_SUBREDDITS = [
  "travel",
  "weddingplanning",
  "JustEngaged",
  "Weddings",
  "HoneymoonTravel",
  "HoneymoonIdeas",
  "Marriage",
  "relationship_advice",
  "DestinationWedding",
  "BridalFashion",
  "BridetoBe",
  "AskMarriage",
    "travelagent",
]

sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)
df  = get_honeymoon_posts(sub.lower())

# Fetch and display posts
df = get_honeymoon_posts(sub.lower())
st.dataframe(df)

# Automatically export any non-empty results
if not df.empty:
    try:
        export_to_google_sheet(df)
        st.success(f"Automatically exported {len(df)} leads to Google Sheets!")
    except Exception as e:
        st.error(f"Export failed: {e}")

# Subreddit selection
sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)

# Fetch & show
df = get_honeymoon_posts(sub.lower())
st.dataframe(df)

# Auto-export
if not df.empty:
    try:
        export_to_google_sheet(df)
        st.success(f"Automatically exported {len(df)} leads to Google Sheets!")
    except Exception as e:
        st.error(f"Export failed: {e}")




