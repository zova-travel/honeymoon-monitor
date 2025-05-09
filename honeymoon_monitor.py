import os
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from prawcore.exceptions import NotFound, Redirect

# ─── 1) Page config (must be first) ─────────────────────────────────────────────
st.set_page_config(page_title="Honeymoon Leads Monitor", layout="wide")

# ─── 2) Build auth config from ENV vars ──────────────────────────────────────────
usernames = {}
u1 = os.getenv("AUTH_USER1_NAME")
p1 = os.getenv("AUTH_USER1_PASSWORD")
if u1 and p1:
    usernames[u1] = {"name": u1, "password": p1}
u2 = os.getenv("AUTH_USER2_NAME")
p2 = os.getenv("AUTH_USER2_PASSWORD")
if u2 and p2:
    usernames[u2] = {"name": u2, "password": p2}

credentials = {"usernames": usernames}
cookie_conf  = {
    "name":        os.getenv("AUTH_COOKIE_NAME"),
    "key":         os.getenv("AUTH_COOKIE_KEY"),
    "expiry_days": int(os.getenv("AUTH_COOKIE_EXPIRY_DAYS", "7")),
}

# ─── 3) Init authenticator ─────────────────────────────────────────────────────
authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name=cookie_conf["name"],
    key=cookie_conf["key"],
    cookie_expiry_days=cookie_conf["expiry_days"],
)

# ─── 4) Render login widget with correct 'location' keyword ────────────────────
name, auth_status, username = authenticator.login(
    "Login",
    location="sidebar"
)
if not auth_status:
    if auth_status is False:
        st.sidebar.error("❌ Incorrect username or password")
    st.stop()

# ─── 5) Show logout & welcome ──────────────────────────────────────────────────
authenticator.logout("Logout", "sidebar")
st.sidebar.write(f"👋 Welcome *{name}*!')")

# ─── 6) Reddit & Google Sheets setup ────────────────────────────────────────────
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
        "https://www.googleapis.com/auth/drive"
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_name(
        "honeymoonmonitor-1e60328f5b40.json", scope
    )
    client = gspread.authorize(creds)
    sheet  = client.open("honeymoon spreadsheet").sheet1

    try:
        existing_urls = set(sheet.col_values(4))  # col D
    except:
        existing_urls = set()

    rows = []
    for _, row in df.iterrows():
        url = row["URL"]
        if url not in existing_urls:
            rows.append([
                "",                # col A blank
                row["Title"],      # col B
                row["Author"],     # col C
                url,                # col D
                row["Subreddit"]   # col E
            ])
            existing_urls.add(url)

    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")

# ─── 7) Main Streamlit UI ───────────────────────────────────────────────────────
st.title("🌴 Honeymoon Travel Leads Monitor")

sub = st.selectbox("Choose subreddit to scan:", TARGET_SUBREDDITS)
df  = get_honeymoon_posts(sub)
st.dataframe(df)

if st.button("Export to Google Sheets"):
    export_to_google_sheet(df)
    st.success("✅ New leads appended!")
