import streamlit as st
import requests
import pandas as pd

# Mutual Fund Scheme Codes (from AMFI via mfapi.in)
FUNDS = {
    "Parag Parikh Flexi Cap": "122639",
    "Motilal Oswal Midcap 30": "127042",
    "Quant Small Cap": "120828"
}

@st.cache_data(ttl=86400)  # cache for 1 day
def get_fund_data(code):
    """Fetch NAV data and filter only 3rd day NAVs with % change."""
    url = f"https://api.mfapi.in/mf/{code}"
    data = requests.get(url).json()
    navs = pd.DataFrame(data['data'])
    navs['date'] = pd.to_datetime(navs['date'], format="%d-%m-%Y")
    navs['nav'] = navs['nav'].astype(float)

    # If 3rd day missing (holiday), take nearest available (2nd/4th)
    navs = navs.set_index("date").sort_index()
    navs = navs.resample("MS").nearest()  # pick nearest at start of month

    # Calculate % change month-on-month
    navs['pct_change'] = navs['nav'].pct_change() * 100
    return navs.reset_index()

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", page_icon="📊", layout="wide")

# Custom style
st.markdown("""
    <style>
        .big-font { font-size:22px !important; font-weight: bold; }
        .positive { color: green; font-weight: bold; }
        .negative { color: red; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Mutual Fund NAV Tracker")
st.write("Track NAV on **3rd day of each month** (or nearest) and monthly % change.")

# Multi-fund selection
fund_choices = st.multiselect("Choose Mutual Funds", list(FUNDS.keys()), default=list(FUNDS.keys())[:1])

for choice in fund_choices:
    st.subheader(choice)
    df = get_fund_data(FUNDS[choice])

    if not df.empty:
        # Apply styling for % change
        styled_df = df[['date', 'nav', 'pct_change']].style.format({
            "nav": "{:.2f}",
            "pct_change": "{:.2f}%"
        }).applymap(
            lambda v: "color: green; font-weight: bold;" if isinstance(v, float) and v > 5 else
                      "color: red; font-weight: bold;" if isinstance(v, float) and v < -5 else ""
        , subset=['pct_change'])

        st.dataframe(styled_df, use_container_width=True)
        st.line_chart(df.set_index("date")[['nav', 'pct_change']])
    else:
        st.warning("No data available for this fund.")