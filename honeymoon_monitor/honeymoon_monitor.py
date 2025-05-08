import streamlit as st
import praw
import pandas as pd
import datetime
import time
import os

# Reddit API credentials (use environment variables for security)
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# Keywords to detect honeymoon intent
HONEYMOON_KEYWORDS = [
    "honeymoon", "getting married", "just married", "destination wedding",
    "romantic getaway", "planning honeymoon", "honeymoon ideas", "couples trip"
]

# Subreddits to monitor
TARGET_SUBREDDITS = ["travel", "weddingplanning", "honeymoon", "solotravel", "IWantOut"]

# Setup Streamlit
st.set_page_config(page_title="Honeymoon Travel Monitor", layout="wide")
st.title("🌴 Honeymoon Travel Lead Finder")
st.write("Monitoring Reddit in real-time for posts about honeymoons and romantic travel...")

# Data storage
leads = []

# Streamlit placeholder for updates
table_placeholder = st.empty()

# Function to check if post matches honeymoon interest
def is_honeymoon_post(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in HONEYMOON_KEYWORDS)

# Function to fetch and filter posts
def fetch_posts():
    global leads
    for subreddit_name in TARGET_SUBREDDITS:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.new(limit=10):
            if is_honeymoon_post(post.title + " " + (post.selftext or "")):
                leads.append({
                    "Subreddit": subreddit_name,
                    "Title": post.title,
                    "Post URL": f"https://www.reddit.com{post.permalink}",
                    "Author": str(post.author),
                    "Score": post.score,
                    "Date": datetime.datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M')
                })

# Refresh loop for real-time effect
refresh_interval = st.slider("Refresh interval (seconds):", 10, 120, 30)

while True:
    fetch_posts()
    if leads:
        df = pd.DataFrame(leads).drop_duplicates(subset="Post URL")
        table_placeholder.dataframe(df, use_container_width=True)
        st.download_button("📥 Export Leads to CSV", df.to_csv(index=False), "honeymoon_leads.csv")
    else:
        table_placeholder.info("No honeymoon-related posts found yet. Scanning...")
    time.sleep(refresh_interval)
