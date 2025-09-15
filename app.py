import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

# ----------------- CONFIG -----------------
FUNDS = {
    "Parag Parikh Flexi Cap": "122639",
    "Motilal Oswal Midcap 30": "127042",
    "Quant Small Cap": "120828"
}

COLORS = ["#4CAF50", "#2196F3", "#FF9800"]

# ----------------- FUNCTIONS -----------------
def get_fund_data(code):
    """Fetch NAV data for last 2 years, only 3rd day NAVs, with % change."""
    try:
        data = requests.get(f"https://api.mfapi.in/mf/{code}").json()['data']
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y")
        df['nav'] = df['nav'].astype(float)

        # Filter last 2 years
        cutoff = datetime.today() - timedelta(days=730)
        df = df[df['date'] >= cutoff]

        # Only 3rd day NAVs
        df = df[df['date'].dt.day == 3].sort_values("date", ascending=False)

        # % change
        df['Fund Change (%)'] = df['nav'].pct_change() * 100
        df = df[['date', 'nav', 'Fund Change (%)']]
        df.rename(columns={"date": "Date", "nav": "NAV"}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching fund data: {e}")
        return pd.DataFrame()

def get_current_and_alltime_nav(code):
    """Get current and all-time high NAV for a fund."""
    data = requests.get(f"https://api.mfapi.in/mf/{code}").json()['data']
    df = pd.DataFrame(data)
    df['nav'] = df['nav'].astype(float)
    df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y")

    current = df.iloc[0]
    all_time_max = df.loc[df['nav'].idxmax()]

    return {
        "current_nav": float(current['nav']),
        "current_date": current['date'].strftime("%Y-%m-%d"),
        "max_nav": float(all_time_max['nav']),
        "max_date": all_time_max['date'].strftime("%Y-%m-%d")
    }

def get_nifty_data():
    """Fetch Nifty 50 monthly prices for last 2 years."""
    end = datetime.today()
    start = end - timedelta(days=730)
    nifty = yf.download("^NSEI", start=start, end=end, interval="1mo")['Close'].reset_index()
    nifty.rename(columns={"Date": "Date", "Close": "Nifty"}, inplace=True)
    nifty['Date'] = pd.to_datetime(nifty['Date'])
    nifty['Nifty Change (%)'] = nifty['Nifty'].pct_change() * 100
    return nifty

def merge_fund_nifty(fund_df, nifty_df):
    """Merge fund NAV data with closest Nifty date for comparison."""
    df = fund_df.copy()
    df['Nifty Change (%)'] = df['Date'].apply(
        lambda d: nifty_df.iloc[(nifty_df['Date'] - d).abs().argsort()[:1]]['Nifty Change (%)'].values[0]
    )
    return df

def calculate_cagr(start_value, end_value, years):
    """Calculate CAGR given start and end values and number of years."""
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    return ((end_value / start_value) ** (1 / years) - 1) * 100

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")
st.title("📈 Mutual Fund NAV Tracker with Nifty 50 Comparison & Buy Alert")
st.write("Track NAV on **3rd day of each month** (last 2 years), compare with Nifty 50, see CAGR, and potential buying opportunities.")

# ----------------- Latest NAV + All-Time High + CAGR + Buy Alert -----------------
st.subheader("🔹 Current & All-Time High NAVs + CAGR (2Y)")
cols = st.columns(len(FUNDS))

nifty_df_full = get_nifty_data()  # Fetch once for all funds

for i, (fund_name, code) in enumerate(FUNDS.items()):
    try:
        fund_df = get_fund_data(code)
        nav_info = get_current_and_alltime_nav(code)

        # Calculate 2-year CAGR
        if not fund_df.empty:
            start_nav = fund_df['NAV'].iloc[-1]
            end_nav = fund_df['NAV'].iloc[0]
            years = 2
            fund_cagr = calculate_cagr(start_nav, end_nav, years)

            start_nifty = nifty_df_full['Nifty'].iloc[-1]
            end_nifty = nifty_df_full['Nifty'].iloc[0]
            nifty_cagr = calculate_cagr(start_nifty, end_nifty, years)
        else:
            fund_cagr = nifty_cagr = None

        # ----------------- Buy Alert (20% below all-time high) -----------------
        alert_msg = None
        if nav_info['current_nav'] < 0.80 * nav_info['max_nav']:
            alert_msg = f"🚨 {fund_name} NAV is below 80% of its all-time high. Consider reviewing for potential buying opportunity!"

        with cols[i]:
            st.markdown(
                f"""
                <div style="
                    background-color:{COLORS[i % len(COLORS)]};
                    padding:18px;
                    border-radius:10px;
                    text-align:center;
                    color:white;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                ">
                    <h4 style="margin:0;">{fund_name}</h4>
                    <p style="margin:0; font-size:14px;">Current NAV: <b>{nav_info['current_nav']:.2f}</b> ({nav_info['current_date']})</p>
                    <p style="margin:0; font-size:14px;">All-Time High: <b>{nav_info['max_nav']:.2f}</b> ({nav_info['max_date']})</p>
                    <p style="margin:0; font-size:14px;">Fund CAGR (2Y): <b>{fund_cagr:.2f}%</b></p>
                    <p style="margin:0; font-size:14px;">Nifty CAGR (2Y): <b>{nifty_cagr:.2f}%</b></p>
                </div>
                """,
                unsafe_allow_html=True
            )
        if alert_msg:
            st.success(alert_msg)

    except:
        with cols[i]:
            st.error(f"{fund_name}: Data not available")

# ----------------- Fund Analysis -----------------
st.subheader("🔎 Fund Analysis vs Nifty 50")
fund_choice = st.selectbox("Choose a Mutual Fund", list(FUNDS.keys()))

if fund_choice:
    fund_df = get_fund_data(FUNDS[fund_choice])
    if not fund_df.empty:
        df_merged = merge_fund_nifty(fund_df, nifty_df_full)

        # Highlight row red if fund underperforms Nifty by >3%
        def highlight_row(row):
            if row['Fund Change (%)'] < row['Nifty Change (%)'] - 3:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        styled_df = df_merged.style.apply(highlight_row, axis=1).format(
            {"NAV": "{:.2f}", "Fund Change (%)": "{:.2f}%", "Nifty Change (%)": "{:.2f}%"}
        )

        st.dataframe(styled_df, width='stretch')

        # ----------------- Line Chart -----------------
        st.subheader(f"📊 Performance Comparison: {fund_choice} vs Nifty 50")
        chart_df = df_merged[['Date', 'NAV']].copy()
        chart_df.set_index('Date', inplace=True)
        chart_df['Fund'] = (chart_df['NAV'] / chart_df['NAV'].iloc[-1]) * 100

        nifty_norm = []
        for d in df_merged['Date']:
            nifty_val = nifty_df_full.iloc[(nifty_df_full['Date'] - d).abs().argsort()[:1]]['Nifty'].values[0]
            nifty_norm.append(nifty_val)
        nifty_norm = pd.Series(nifty_norm)
        nifty_norm = (nifty_norm / nifty_norm.iloc[-1]) * 100
        chart_df['Nifty'] = nifty_norm.values

        st.line_chart(chart_df[['Fund', 'Nifty']])
    else:
        st.warning("No data available for this fund.")