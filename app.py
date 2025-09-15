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
    """Fetch NAV data, keep last 2 years, and filter only 3rd day NAVs with % change."""
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        data = requests.get(url).json()
        navs = pd.DataFrame(data['data'])
        navs['date'] = pd.to_datetime(navs['date'], format="%d-%m-%Y")
        navs['nav'] = navs['nav'].astype(float)

        # Keep only last 2 years
        two_years_ago = datetime.today() - timedelta(days=730)
        navs = navs[navs['date'] >= two_years_ago]

        # Pick only 3rd day NAVs
        navs = navs[navs['date'].dt.day == 3].sort_values("date")

        # Calculate % change month-on-month
        navs['Change (%)'] = navs['nav'].pct_change() * 100

        # Keep only required columns
        navs = navs[['date', 'nav', 'Change (%)']]

        # Rename columns
        navs.rename(columns={
            "date": "Date",
            "nav": "NAV"
        }, inplace=True)

        return navs
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def get_current_nav(code):
    """Fetch latest NAV for a given fund."""
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        data = requests.get(url).json()
        latest = data['data'][0]
        return float(latest['nav']), latest['date']
    except:
        return None, None

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")

st.title("📈 Mutual Fund NAV Tracker")
st.write("Track NAV on **3rd day of each month** (last 2 years) and % change compared to previous month.")

# Show current NAVs at the top
st.subheader("🔹 Current NAVs")
cols = st.columns(len(FUNDS))
for i, (fund_name, code) in enumerate(FUNDS.items()):
    nav, date = get_current_nav(code)
    if nav:
        cols[i].metric(label=f"{fund_name} ({date})", value=f"{nav:.2f}")
    else:
        cols[i].error("No data")

# Fund selection
fund_choice = st.selectbox("Choose a Mutual Fund", list(FUNDS.keys()))

if fund_choice:
    st.subheader(f"📊 {fund_choice} - Last 2 Years (3rd Day NAVs)")
    df = get_fund_data(FUNDS[fund_choice])

    if not df.empty:
        # Highlight % change above 5% in green and below -5% in red
        def highlight_changes(val):
            if pd.isna(val):
                return ''
            if val > 5:
                return 'color: green; font-weight: bold;'
            elif val < -5:
                return 'color: red; font-weight: bold;'
            return ''

        styled_df = df.style.map(highlight_changes, subset=["Change (%)"])
        st.dataframe(styled_df, width='stretch')
    else:
        st.warning("No data available for this fund.")