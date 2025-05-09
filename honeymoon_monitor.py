import streamlit as st
import streamlit_authenticator as stauth

# 1) Load config from secrets.toml
config = st.secrets["credentials"]
cookie_conf = {
    "name":        st.secrets["cookie"]["name"],
    "key":         st.secrets["cookie"]["key"],
    "expiry_days": st.secrets["cookie"]["expiry_days"],
}

# 2) Create the authenticator
authenticator = stauth.Authenticate(
    credentials=config,
    cookie_name=cookie_conf["name"],
    key=cookie_conf["key"],
    cookie_expiry_days=cookie_conf["expiry_days"],
)

# 3) Render the login widget
name, auth_status, username = authenticator.login("Login", "sidebar")

# 4) Stop if not authenticated
if not auth_status:
    if auth_status is False:
        st.error("❌ Username/password is incorrect")
    st.stop()

# 5) Show a logout button
authenticator.logout("Logout", "sidebar")
st.write(f"👋 Welcome *{name}*!")

import os
import sqlite3
import hashlib
import pandas as pd
import praw
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from prawcore.exceptions import NotFound, Redirect

# ─── 1) Streamlit must be configured first ───────────────────────────────────────
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")

# ─── 2) Authentication (SQLite-backed) ──────────────────────────────────────────
# DB init
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username       TEXT PRIMARY KEY,
        password_hash  TEXT NOT NULL
    )
""")
conn.commit()

# session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# sidebar form
mode = st.sidebar.radio("Action", ["Login", "Create Account"])
uname = st.sidebar.text_input("Username")
pwd   = st.sidebar.text_input("Password", type="password")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

if mode == "Create Account":
    if st.sidebar.button("Sign Up"):
        c.execute("SELECT 1 FROM users WHERE username = ?", (uname,))
        if c.fetchone():
            st.sidebar.error("❌ Username already taken")
        else:
            c.execute(
                "INSERT INTO users (username, password_hash) VALUES (?,?)",
                (uname, hash_pw(pwd))
            )
            conn.commit()
            st.sidebar.success("✅ Account created! You can now log in.")
elif mode == "Login":
    if st.sidebar.button("Login"):
        c.execute(
            "SELECT password_hash FROM users WHERE username = ?", (uname,)
        )
        row = c.fetchone()
        if row and row[0] == hash_pw(pwd):
            st.session_state.logged_in = True
        else:
            st.sidebar.error("❌ Invalid username or password")

# block until logged in
if not st.session_state.logged_in:
    st.stop()

# optional logout
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()

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
        st.warning(f"r/{subreddit_name} not found or inaccessible—skipping.")
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
    # authorize
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json", scope
    )
    client = gspread.authorize(creds)
    sheet  = client.open("honeymoon spreadsheet").sheet1

    # avoid duplicates by URL
    try:
        existing_urls = set(sheet.col_values(4))  # column D
    except Exception:
        existing_urls = set()

    rows = []
    for _, row in df.iterrows():
        url = row["URL"]
        if url not in existing_urls:
            rows.append([
                "",              # blank for column A
                row["Title"],    # B
                row["Author"],   # C
                url,             # D
                row["Subreddit"] # E
            ])
            existing_urls.add(url)

    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")

# ─── 4) Streamlit Main UI ───────────────────────────────────────────────────────
st.title("🌴 Honeymoon Travel Leads Monitor")

sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)
df  = get_honeymoon_posts(sub)
st.dataframe(df)

if st.button("Export to Google Sheets"):
    export_to_google_sheet(df)
    st.success(f"✅ Appended {len(df[df['URL'].isin(existing_urls)])} new leads!")
