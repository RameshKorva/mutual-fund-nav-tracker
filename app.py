import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Mutual Fund Scheme Codes (from AMFI via mfapi.in)
FUNDS = {
    "Parag Parikh Flexi Cap": "122639",
    "Motilal Oswal Midcap 30": "127042",
    "Quant Small Cap": "120828"
}

def get_fund_data(code):
    """Fetch NAV data, filter last 2 years, only 3rd day NAVs, with % change."""
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        data = requests.get(url).json()
        navs = pd.DataFrame(data['data'])
        navs['date'] = pd.to_datetime(navs['date'], format="%d-%m-%Y")
        navs['nav'] = navs['nav'].astype(float)

        # Filter last 2 years
        cutoff_date = datetime.today() - timedelta(days=2*365)
        navs = navs[navs['date'] >= cutoff_date]

        # Only 3rd day NAVs
        navs = navs[navs['date'].dt.day == 3].sort_values("date")

        # % change
        navs['pct_change'] = navs['nav'].pct_change() * 100
        return navs
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def get_latest_nav(code):
    """Fetch latest NAV for a given fund."""
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        data = requests.get(url).json()
        latest = data['data'][0]
        return latest['date'], float(latest['nav'])
    except:
        return None, None

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")

st.title("📈 Mutual Fund NAV Tracker")
st.write("Track NAV on **3rd day of each month** (last 2 years) and % change compared to previous month.")

# ----------------- Latest NAV Cards -----------------
st.subheader("📊 Latest NAVs")

cols = st.columns(len(FUNDS))
colors = ["#4CAF50", "#2196F3", "#FF9800"]  # green, blue, orange

for i, (name, code) in enumerate(FUNDS.items()):
    date, nav = get_latest_nav(code)
    if date and nav:
        with cols[i]:
            st.markdown(
                f"""
                <div style="
                    background-color:{colors[i % len(colors)]};
                    padding:18px;
                    border-radius:10px;
                    text-align:center;
                    color:white;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                ">
                    <h4 style="margin:0;">{name}</h4>
                    <h2 style="margin:8px 0;">{nav:.2f}</h2>
                    <p style="margin:0; font-size:14px;">as of {date}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

# ----------------- Fund Analysis -----------------
st.subheader("🔎 Fund Analysis")
fund_choice = st.selectbox("Choose a Mutual Fund", list(FUNDS.keys()))

if fund_choice:
    st.markdown(f"### {fund_choice}")
    df = get_fund_data(FUNDS[fund_choice])

    if not df.empty:
        # Style NAV % change
        def highlight(val):
            if pd.isna(val):
                return ""
            color = "red" if val > 5 else ("green" if val < -5 else "")
            return f"color:{color}; font-weight:bold;" if color else ""

        styled_df = df[['date', 'nav', 'pct_change']].style.format(
            {"nav": "{:.2f}", "pct_change": "{:.2f}%"}
        ).map(highlight, subset=['pct_change'])

        st.dataframe(styled_df, width="stretch")
        st.line_chart(df.set_index("date")[['nav', 'pct_change']])
    else:
        st.warning("No data available for this fund.")