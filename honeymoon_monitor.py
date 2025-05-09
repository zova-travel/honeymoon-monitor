import os
import pandas as pd
import praw
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from prawcore.exceptions import NotFound, Redirect

# ─── 1) Setup Reddit API ─────────────────────────────────────────────────────────
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# ─── 2) Keywords & Subreddit List ───────────────────────────────────────────────
KEYWORDS = [
    "honeymoon", "just married", "getting married", "destination wedding",
    "romantic getaway", "couples trip", "post-wedding vacation", "wedding trip"
]

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

# ─── 3) Helper Functions ─────────────────────────────────────────────────────────
def get_honeymoon_posts(subreddit_name: str):
    posts = []
    try:
        # force a lookup to catch missing or redirected subs
        _ = reddit.subreddit(subreddit_name).id
        submissions = reddit.subreddit(subreddit_name).new(limit=50)
    except (NotFound, Redirect):
        st.warning(f"r/{subreddit_name} not found or inaccessible—skipping.")
        return pd.DataFrame(posts)

    for post in submissions:
        text = (post.title + " " + (post.selftext or "")).lower()
        if any(k in text for k in KEYWORDS):
          posts.append({
    "Subreddit": subreddit_name,               # ← new field
    "Title":     post.title,
    "Author":    post.author.name if post.author else "N/A",
    "URL":       f"https://reddit.com{post.permalink}"
})

    return pd.DataFrame(posts)

def export_titles_to_column_b(df: pd.DataFrame):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json",
        scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("honeymoon spreadsheet").sheet1

    # Build the 2D list for B1:B{n}
    values = [["Title"]] + [[t] for t in df["Title"].tolist()]
    end_row = len(values)
    cell_range = f"B1:B{end_row}"

    # Update only column B
    sheet.update(cell_range, values, value_input_option="USER_ENTERED")


def export_to_google_sheet(df: pd.DataFrame):
    # 1) Authorize
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json",
        scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("honeymoon spreadsheet").sheet1

    # 2) Pull existing URLs from column D
    try:
        existing_urls = set(sheet.col_values(4))
    except Exception:
        existing_urls = set()

    # 3) Build rows to append
    rows_to_append = []
    for _, row in df.iterrows():
        url = row["URL"]
        if url not in existing_urls:
            rows_to_append.append([
                "",                 # blank for column A
                row["Title"],       # column B
                row["Author"],      # column C
                url,                # column D
                row["Subreddit"]    # column E
            ])
            existing_urls.add(url)  # <— same indent as the append above

    # 4) Append new rows if any
    if rows_to_append:
        sheet.append_rows(
            rows_to_append,
            value_input_option="USER_ENTERED"
        )

# ─── 4) Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")
st.title("🌴 Honeymoon Travel Leads Monitor")

# Dropdown for the user to pick a subreddit
sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)

# Fetch & display posts for that choice
df = get_honeymoon_posts(sub)
st.dataframe(df)

# Export button (or auto-export logic)
if st.button("Export to Google Sheets"):
    export_to_google_sheet(df)
    st.success(f"Appended {len(df)} new leads!")
