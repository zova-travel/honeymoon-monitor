
import streamlit as st
import praw
import pandas as pd
import os

# Setup Reddit API with environment variables
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# Streamlit App Title
st.title("Live Reddit Honeymoon Travel Monitor")

# Function to fetch posts
def get_honeymoon_posts(subreddit_name="travel"):
    posts = []
    for submission in reddit.subreddit(subreddit_name).search("honeymoon", sort="new", limit=20):
        posts.append({
            "Title": submission.title,
            "Author": submission.author.name if submission.author else "N/A",
            "URL": f"https://reddit.com{submission.permalink}"
        })
    return pd.DataFrame(posts)

# Display Data
df = get_honeymoon_posts()
st.dataframe(df)
