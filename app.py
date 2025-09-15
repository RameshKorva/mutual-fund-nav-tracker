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
    """Fetch NAV data, keep last 2 years, only 3rd day NAVs with % change."""
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        data = requests.get(url).json()
        navs = pd.DataFrame(data['data'])
        navs['date'] = pd.to_datetime(navs['date'], format="%d-%m-%Y")
        navs['nav'] = navs['nav'].astype(float)

        # Filter last 2 years
        two_years_ago = datetime.today() - timedelta(days=730)
        navs = navs[navs['date'] >= two_years_ago]

        # Only 3rd day NAVs
        navs = navs[navs['date'].dt.day == 3].sort_values("date", ascending=False)

        # Calculate % change month-on-month
        navs['Change (%)'] = navs['nav'].pct_change() * 100

        # Keep only 3 columns
        navs = navs[['date', 'nav', 'Change (%)']]

        # Rename columns
        navs.rename(columns={"date": "Date", "nav": "NAV"}, inplace=True)
        return navs
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")
st.title("📈 Mutual Fund NAV Tracker")
st.write("Track NAV on **3rd day of each month** (last 2 years) and % change compared to previous month.")

# ----------------- Latest NAV + All-Time High -----------------
st.subheader("🔹 Current & All-Time High NAVs")
cols = st.columns(len(FUNDS))
colors = ["#4CAF50", "#2196F3", "#FF9800"]  # green, blue, orange

for i, (fund_name, code) in enumerate(FUNDS.items()):
    try:
        data = requests.get(f"https://api.mfapi.in/mf/{code}").json()['data']
        df_all = pd.DataFrame(data)
        df_all['nav'] = df_all['nav'].astype(float)
        df_all['date'] = pd.to_datetime(df_all['date'], format="%d-%m-%Y")

        # Current NAV
        current = df_all.iloc[0]
        current_nav = float(current['nav'])
        current_date = current['date'].strftime("%Y-%m-%d")

        # All-time high NAV
        all_time_max = df_all.loc[df_all['nav'].idxmax()]
        max_nav = float(all_time_max['nav'])
        max_date = all_time_max['date'].strftime("%Y-%m-%d")

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
                    <h4 style="margin:0;">{fund_name}</h4>
                    <p style="margin:0; font-size:14px;">Current NAV: <b>{current_nav:.2f}</b> ({current_date})</p>
                    <p style="margin:0; font-size:14px;">All-Time High: <b>{max_nav:.2f}</b> ({max_date})</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    except:
        with cols[i]:
            st.error(f"{fund_name}: Data not available")

# ----------------- Fund Analysis -----------------
st.subheader("🔎 Fund Analysis")
fund_choice = st.selectbox("Choose a Mutual Fund", list(FUNDS.keys()))

if fund_choice:
    df = get_fund_data(FUNDS[fund_choice])

    if not df.empty:
        # Style entire row red if Change (%) < -3%
        def highlight_row(row):
            if row['Change (%)'] < -3:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        styled_df = df.style.apply(highlight_row, axis=1).format(
            {"NAV": "{:.2f}", "Change (%)": "{:.2f}%"}
        )

        st.dataframe(styled_df, width='stretch')
    else:
        st.warning("No data available for this fund.")