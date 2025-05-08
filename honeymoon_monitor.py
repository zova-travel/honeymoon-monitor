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

# Keywords to detect honeymoon intent
KEYWORDS = [
    "honeymoon", "just married", "getting married", "destination wedding",
    "romantic getaway", "couples trip", "post-wedding vacation", "wedding trip"
]

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
  "AskMarriage"
]

# Function to fetch and filter posts
def get_honeymoon_posts(subreddit_name="travel"):
    posts = []
    for submission in reddit.subreddit(subreddit_name).new(limit=50):
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
