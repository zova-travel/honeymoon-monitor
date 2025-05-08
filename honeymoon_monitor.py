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
                "Title":  post.title,
                "Author": post.author.name if post.author else "N/A",
                "URL":    f"https://reddit.com{post.permalink}"
            })
    return pd.DataFrame(posts)

def export_to_google_sheet(df: pd.DataFrame):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json", scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("honeymoon spreadsheet").sheet1

    # Convert DataFrame to list of lists (without header)
    rows = df.values.tolist()
    # Append all rows at once
    sheet.append_rows(rows, table_range="A2")  
    # note: table_range="A2" starts appending at row 2,
    # so row 1 (your headers) stays intact

def export_titles_to_column_b(df: pd.DataFrame):
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

    # 2) Build a list-of-lists for B1:B{n}
    #    first row is header, then one title per list
    values = [["Title"]] + [[t] for t in df["Title"].tolist()]

    # 3) Compute the range (e.g. B1:B10)
    end_row = len(values)
    cell_range = f"B1:B{end_row}"

    # 4) Update just that range
    sheet.update(cell_range, values, value_input_option="USER_ENTERED")

# ─── 4) Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")
st.title("🌴 Honeymoon Travel Leads Monitor")

# ─── THIS is where `sub` gets defined ─────────────────────────────────────────────
sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)

# Now that `sub` exists, we can fetch and show results
df = get_honeymoon_posts(sub)
st.dataframe(df)

# Optional export button
if not df.empty:
    if st.button("Export to Google Sheets"):
        export_to_google_sheet(df)
        st.success(f"Exported {len(df)} leads to Google Sheets!")
    else:
        st.info("Click above to export leads to Google Sheets.")

