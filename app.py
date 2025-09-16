# app.py — fixed version: correct pct_change + caching for speed
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

# ----------------- FETCH & CACHE -----------------
@st.cache_data(ttl=24 * 60 * 60)  # cache 24 hours
def fetch_fund_history(code):
    """Fetch full fund history once and return ascending-by-date DataFrame."""
    data = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=10).json().get('data', [])
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y")
    df['nav'] = df['nav'].astype(float)
    # Sort ascending (oldest -> newest) — important for correct pct_change
    return df.sort_values('date').reset_index(drop=True)

@st.cache_data(ttl=24 * 60 * 60)
def get_nifty_data():
    """Fetch Nifty monthly prices (last 5 years) and return DataFrame."""
    end = datetime.today()
    start = end - timedelta(days=5 * 365)
    nifty = yf.download("^NSEI", start=start, end=end, interval="1mo")
    if nifty.empty:
        return pd.DataFrame()
    # prefer Close, fallback to Adj Close
    col = 'Close' if 'Close' in nifty.columns else ('Adj Close' if 'Adj Close' in nifty.columns else None)
    if col is None:
        return pd.DataFrame()
    prices = nifty[col].reset_index()
    prices.rename(columns={'Date': 'Date', col: 'Nifty'}, inplace=True)
    prices['Date'] = pd.to_datetime(prices['Date'])
    prices['Nifty Change (%)'] = prices['Nifty'].pct_change() * 100
    return prices

# ----------------- DATA PREP -----------------
def get_fund_data(code):
    """
    Return fund DataFrame with:
      - last 5 years of data
      - only 3rd day NAVs
      - Fund Change (%) computed correctly (oldest->newest)
    The returned DataFrame is sorted newest->oldest for display.
    """
    df_all = fetch_fund_history(code)
    if df_all.empty:
        return pd.DataFrame(columns=['Date', 'NAV', 'Fund Change (%)'])

    # Keep last 5 years (based on full history)
    cutoff_5y = datetime.today() - timedelta(days=5 * 365)
    df_5y = df_all[df_all['date'] >= cutoff_5y].copy()

    # Pick only 3rd day rows (note df_all is ascending)
    df_3rd = df_5y[df_5y['date'].dt.day == 3].copy()

    # --- KEY FIX: compute pct_change on ascending series (oldest -> newest) ---
    df_3rd = df_3rd.sort_values('date')  # ensure ascending
    df_3rd['Fund Change (%)'] = df_3rd['nav'].pct_change() * 100

    # keep/rename columns and return sorted newest->oldest for UI
    df_3rd = df_3rd[['date', 'nav', 'Fund Change (%)']].rename(columns={'date': 'Date', 'nav': 'NAV'})
    return df_3rd.sort_values('Date', ascending=False).reset_index(drop=True)

def get_current_and_alltime_nav(code):
    """Return current and all-time high NAV info using cached history."""
    df_all = fetch_fund_history(code)
    if df_all.empty:
        return {"current_nav": None, "current_date": None, "max_nav": None, "max_date": None}
    # df_all is ascending (oldest -> newest)
    current = df_all.iloc[-1]
    all_time_max = df_all.loc[df_all['nav'].idxmax()]
    return {
        "current_nav": float(current['nav']),
        "current_date": current['date'].strftime("%Y-%m-%d"),
        "max_nav": float(all_time_max['nav']),
        "max_date": all_time_max['date'].strftime("%Y-%m-%d")
    }

def merge_fund_nifty(fund_df, nifty_df):
    """Attach nearest Nifty Change (%) to each fund Date (fund_df Date must be datetime)."""
    if fund_df.empty or nifty_df.empty:
        return fund_df.copy()
    df = fund_df.copy()
    # ensure types
    nifty_df = nifty_df.copy()
    nifty_df['Date'] = pd.to_datetime(nifty_df['Date'])
    df['Nifty Change (%)'] = df['Date'].apply(
        lambda d: nifty_df.iloc[(nifty_df['Date'] - d).abs().argsort()[:1]]['Nifty Change (%)'].values[0]
        if not nifty_df.empty else pd.NA
    )
    return df

def calculate_cagr(start_value, end_value, years):
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    return ((end_value / start_value) ** (1 / years) - 1) * 100

# ----------------- UI -----------------
st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")
st.title("📈 Mutual Fund NAV Tracker — fixed pct_change + caching")
st.write("Corrected NAV % change (calculated oldest→newest). Table shows last 2 years; CAGR shown for 2Y & 5Y.")

# fetch nifty once (cached)
nifty_df_full = get_nifty_data()

# Top tiles: current, all-time high, CAGR 2Y & 5Y
st.subheader("🔹 Current & All-Time High NAVs + CAGR (2Y & 5Y)")
cols = st.columns(len(FUNDS))
for i, (fund_name, code) in enumerate(FUNDS.items()):
    nav_info = get_current_and_alltime_nav(code)
    fund_df_full = get_fund_data(code)  # this returns last-5yr 3rd-day rows newest-first
    # compute CAGRs correctly using oldest->newest window
    def get_cagr_from_history(code, years, column='NAV'):
        # use the full 5y series (ascending) from cached history
        hist = fetch_fund_history(code)
        cutoff = datetime.today() - timedelta(days=years * 365)
        hist_f = hist[hist['date'] >= cutoff].sort_values('date')
        if len(hist_f) >= 2:
            start = hist_f[column.lower() if column == 'NAV' else column].iloc[0] if column == 'NAV' else hist_f[column].iloc[0]
            # for NAV case, column in hist is 'nav'
            if column == 'NAV':
                start = hist_f['nav'].iloc[0]
                end = hist_f['nav'].iloc[-1]
            else:
                start = hist_f[column].iloc[0]
                end = hist_f[column].iloc[-1]
            return calculate_cagr(start, end, years)
        return None

    fund_cagr_2y = get_cagr_from_history(code, 2, column='NAV')
    fund_cagr_5y = get_cagr_from_history(code, 5, column='NAV')

    # Nifty CAGR using nifty_df_full (which has 'Nifty' column)
    def nifty_cagr_years(nifty_df, years):
        if nifty_df.empty:
            return None
        cutoff = datetime.today() - timedelta(days=years * 365)
        df_f = nifty_df[nifty_df['Date'] >= cutoff].sort_values('Date')
        if len(df_f) >= 2:
            return calculate_cagr(df_f['Nifty'].iloc[0], df_f['Nifty'].iloc[-1], years)
        return None

    nifty_cagr_2y = nifty_cagr_years(nifty_df_full, 2)
    nifty_cagr_5y = nifty_cagr_years(nifty_df_full, 5)

    with cols[i]:
        col_color = COLORS[i % len(COLORS)]
        st.markdown(
            f"""
            <div style="
                background-color:{col_color};
                padding:16px;
                border-radius:10px;
                text-align:center;
                color:white;
            ">
                <h4 style="margin:0;">{fund_name}</h4>
                <p style="margin:2px 0;">Current NAV: <b>{nav_info['current_nav']:.2f}</b> ({nav_info['current_date']})</p>
                <p style="margin:2px 0;">All-Time High: <b>{nav_info['max_nav']:.2f}</b> ({nav_info['max_date']})</p>
                <p style="margin:2px 0;">Fund CAGR (2Y): <b>{(fund_cagr_2y or 0):.2f}%</b></p>
                <p style="margin:2px 0;">Fund CAGR (5Y): <b>{(fund_cagr_5y or 0):.2f}%</b></p>
                <p style="margin:2px 0;">Nifty CAGR (2Y): <b>{(nifty_cagr_2y or 0):.2f}%</b></p>
                <p style="margin:2px 0;">Nifty CAGR (5Y): <b>{(nifty_cagr_5y or 0):.2f}%</b></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Buy alert (20% below ATH)
        if nav_info['current_nav'] and nav_info['current_nav'] < 0.80 * nav_info['max_nav']:
            st.success(f"🚨 {fund_name} NAV is below 80% of its all-time high — possible buying opportunity")

# ----------------- Fund Analysis (Table shows last 2 years) -----------------
st.subheader("🔎 Fund Analysis vs Nifty 50 (Last 2 Years)")
fund_choice = st.selectbox("Choose a Mutual Fund", list(FUNDS.keys()))

if fund_choice:
    fund_df = get_fund_data(FUNDS[fund_choice])  # newest-first
    if fund_df.empty:
        st.warning("No fund data available")
    elif nifty_df_full.empty:
        st.warning("Nifty data not available")
    else:
        # merge (fund_df Date already datetime column)
        merged = merge_fund_nifty(fund_df, nifty_df_full)

        # Keep last 2 years only for table display
        two_yrs_cutoff = datetime.today() - timedelta(days=2 * 365)
        merged_table = merged[merged['Date'] >= two_yrs_cutoff].copy().reset_index(drop=True)

        # highlight row where fund underperforms Nifty by more than 3%
        def highlight_row(row):
            if pd.isna(row['Fund Change (%)']) or pd.isna(row['Nifty Change (%)']):
                return [''] * len(row)
            if row['Fund Change (%)'] < row['Nifty Change (%)'] - 3:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        # show only the three columns plus Nifty Change for comparison
        display_cols = ['Date', 'NAV', 'Fund Change (%)', 'Nifty Change (%)']
        # Ensure Date displays nicely
        merged_table['Date'] = pd.to_datetime(merged_table['Date'])

        styled = merged_table[display_cols].style.apply(highlight_row, axis=1).format({
            'NAV': '{:.2f}',
            'Fund Change (%)': '{:.2f}%',
            'Nifty Change (%)': '{:.2f}%'
        })

        st.dataframe(styled, width='stretch')

        # Line chart (normalized) — show full 5Y series if available
        st.subheader(f"📊 Performance Comparison (normalized): {fund_choice} vs Nifty")
        chart_df = merged.sort_values('Date').copy()  # ascending for chart
        if not chart_df.empty:
            chart_df = chart_df.set_index('Date')
            # normalize fund
            chart_df['Fund_norm'] = (chart_df['NAV'] / chart_df['NAV'].iloc[0]) * 100
            # build matching Nifty series (closest match) then normalize
            nifty_vals = []
            for d in chart_df.index:
                nifty_val = nifty_df_full.iloc[(nifty_df_full['Date'] - d).abs().argsort()[:1]]['Nifty'].values[0]
                nifty_vals.append(nifty_val)
            nifty_series = pd.Series(nifty_vals, index=chart_df.index)
            chart_df['Nifty_norm'] = (nifty_series / nifty_series.iloc[0]) * 100
            st.line_chart(chart_df[['Fund_norm', 'Nifty_norm']])