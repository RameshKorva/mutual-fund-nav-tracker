import streamlit as st
import requests
import pandas as pd

# Mutual Fund Scheme Codes (from AMFI via mfapi.in)
FUNDS = {
    "Parag Parikh Flexi Cap": "120800",
    "Motilal Oswal Midcap 30": "118834",
    "Quant Small Cap": "120588"
}

def get_fund_data(code):
    """Fetch NAV data and filter only 3rd day NAVs with % change."""
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        data = requests.get(url).json()
        navs = pd.DataFrame(data['data'])
        navs['date'] = pd.to_datetime(navs['date'], format="%d-%m-%Y")
        navs['nav'] = navs['nav'].astype(float)
        # Pick only 3rd day NAVs
        navs = navs[navs['date'].dt.day == 3].sort_values("date")
        # Calculate % change month-on-month
        navs['pct_change'] = navs['nav'].pct_change() * 100
        return navs
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")

st.title("📈 Mutual Fund NAV Tracker")
st.write("Track NAV on **3rd day of each month** and % change compared to the previous month.")

# Fund selection
fund_choice = st.selectbox("Choose a Mutual Fund", list(FUNDS.keys()))

if fund_choice:
    st.subheader(fund_choice)
    df = get_fund_data(FUNDS[fund_choice])

    if not df.empty:
        st.dataframe(df[['date', 'nav', 'pct_change']], use_container_width=True)
        st.line_chart(df.set_index("date")[['nav', 'pct_change']])
    else:
        st.warning("No data available for this fund.")