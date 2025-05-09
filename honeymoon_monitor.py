import os
import streamlit as st

# ─── 0) Simple login ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")
st.sidebar.title("🔒 Login")

user = st.sidebar.text_input("Username")
pw   = st.sidebar.text_input("Password", type="password")
login = st.sidebar.button("Login")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if login:
    if user == os.getenv("APP_USERNAME") and pw == os.getenv("APP_PASSWORD"):
        st.session_state.logged_in = True
    else:
        st.sidebar.error("❌ Invalid username or password")

if not st.session_state.logged_in:
    st.stop()

# ─── 1) Reddit & Google Sheets setup ────────────────────────────────────────────
import pandas as pd
import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from prawcore.exceptions import NotFound, Redirect

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

KEYWORDS = [
    "honeymoon","just married","getting married","destination wedding",
    "romantic getaway","couples trip","post-wedding vacation","wedding trip",
    "bridal shower","engaged","engagement ring","bridal registry",
    "wedding venue","wedding ceremony","wedding photography",
    "bachelorette party","anniversary trip","minimoon","elopement",
    "newlyweds","bridal party","wedding favors","wedding music"
]

TARGET_SUBREDDITS = [
    "travel","weddingplanning","JustEngaged","Weddings",
    "HoneymoonTravel","WeddingAdvice","MarriageAdvice",
    "JustMarried","WeddingDIY","WeddingPhotography",
    "weddingideas","weddingvendors","bachelorette",
    "weddingplanninghelp","weddingdresses"
]

def get_honeymoon_posts(subreddit_name: str) -> pd.DataFrame:
    posts = []
    try:
        _ = reddit.subreddit(subreddit_name).id
        submissions = reddit.subreddit(subreddit_name).new(limit=50)
    except (NotFound, Redirect):
        st.warning(f"r/{subreddit_name} not found—skipping.")
        return pd.DataFrame(posts)

    for post in submissions:
        text = (post.title + " " + (post.selftext or "")).lower()
        if any(k in text for k in KEYWORDS):
            posts.append({
                "Subreddit": subreddit_name,
                "Title":     post.title,
                "Author":    post.author.name if post.author else "N/A",
                "URL":       f"https://reddit.com{post.permalink}"
            })
    return pd.DataFrame(posts)

def export_to_google_sheet(df: pd.DataFrame):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json", scope
    )
    client = gspread.authorize(creds)
    sheet  = client.open("honeymoon spreadsheet").sheet1

    try:
        existing_urls = set(sheet.col_values(4))
    except Exception:
        existing_urls = set()

    rows_to_append = []
    for _, row in df.iterrows():
        url = row["URL"]
        if url not in existing_urls:
            rows_to_append.append([
                "",                # blank col A
                row["Title"],      # col B
                row["Author"],     # col C
                url,               # col D
                row["Subreddit"]   # col E
            ])
            existing_urls.add(url)

    if rows_to_append:
        sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

# ─── 2) Streamlit Main UI ───────────────────────────────────────────────────────
st.title("🌴 Honeymoon Travel Leads Monitor")

sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)
df  = get_honeymoon_posts(sub)
st.dataframe(df)

if st.button("Export to Google Sheets"):
    export_to_google_sheet(df)
    st.success("✅ New leads appended!")
