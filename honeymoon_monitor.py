import streamlit as st
import streamlit_authenticator as stauth
import os
import pandas as pd
import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from prawcore.exceptions import NotFound, Redirect

# ─── 1) Page config MUST be first ────────────────────────────────────────────────
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")

# ─── 2) Authentication (cookie + “remember me”) ─────────────────────────────────
# Load your credentials & cookie settings from .streamlit/secrets.toml
config      = st.secrets["credentials"]
cookie_conf = st.secrets["cookie"]

authenticator = stauth.Authenticate(
    credentials=config,
    cookie_name=cookie_conf["name"],
    key=cookie_conf["key"],
    cookie_expiry_days=cookie_conf["expiry_days"],
)

# Show the login widget in the sidebar
name, auth_status, username = authenticator.login("Login", "sidebar")

if not auth_status:
    if auth_status is False:
        st.sidebar.error("❌ Incorrect username or password")
    st.stop()  # halt here until logged in

# Once logged in, show a logout button
authenticator.logout("Logout", "sidebar")
st.sidebar.write(f"👋 Welcome *{name}*!")

# ─── 3) Reddit & Google Sheets Setup ────────────────────────────────────────────
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

KEYWORDS = [
    "honeymoon", "just married", "getting married", "destination wedding",
    "romantic getaway", "couples trip", "post-wedding vacation", "wedding trip",
    "bridal shower", "engaged", "engagement ring", "bridal registry",
    "wedding venue", "wedding ceremony", "wedding photography",
    "bachelorette party", "anniversary trip", "minimoon", "elopement",
    "newlyweds", "bridal party", "wedding favors", "wedding music"
]

TARGET_SUBREDDITS = [
    "travel", "weddingplanning", "JustEngaged", "Weddings",
    "HoneymoonTravel", "WeddingAdvice", "MarriageAdvice",
    "JustMarried", "WeddingDIY", "WeddingPhotography",
    "weddingideas", "weddingvendors", "bachelorette",
    "weddingplanninghelp", "weddingdresses"
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
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json", scope
    )
    client = gspread.authorize(creds)
    sheet  = client.open("honeymoon spreadsheet").sheet1

    # Pull existing URLs (col D)
    existing = set(sheet.col_values(4))
    rows = []
    for _, row in df.iterrows():
        if row["URL"] not in existing:
            rows.append([
                "",                # col A blank
                row["Title"],      # col B
                row["Author"],     # col C
                row["URL"],        # col D
                row["Subreddit"]   # col E
            ])
            existing.add(row["URL"])

    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")

# ─── 4) Main UI ─────────────────────────────────────────────────────────────────
st.title("🌴 Honeymoon Travel Leads Monitor")

sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)
df  = get_honeymoon_posts(sub)
st.dataframe(df)

if st.button("Export to Google Sheets"):
    export_to_google_sheet(df)
    st.success("✅ New leads appended!")
