import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Mutual Fund NAV Tracker", layout="wide")

FUNDS = {
    "Parag Parik Flexi Cap Fund": "120503",
    "Motilal Oswal Midcap Fund": "119830",
    "Quant Small Cap Fund": "120677"
}

@st.cache_data(show_spinner=False)
def fetch_nav(fund_code):
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    records = []
    for line in lines:
        if line.startswith(fund_code):
            parts = line.split(';')
            try:
                nav = float(parts[4])
                date = datetime.strptime(parts[5], '%d-%b-%Y')
                records.append({'date': date, 'nav': nav})
            except:
                continue
    df = pd.DataFrame(records)
    return df

def get_monthly_nav(df):
    monthly_nav = []
    # Group by year and month and get NAV for 3rd day or next available
    for (year, month), group in df.groupby([df['date'].dt.year, df['date'].dt.month]):
        third_day = datetime(year, month, 3)
        nav_row = group[group['date'] == third_day]
        if not nav_row.empty:
            nav_value = nav_row.iloc[0]['nav']
            nav_date = nav_row.iloc[0]['date']
        else:
            # Take first available NAV after 3rd, else before 3rd
            after = group[group['date'] > third_day]
            before = group[group['date'] < third_day]
            if not after.empty:
                row = after.iloc[0]
                nav_value = row['nav']
                nav_date = row['date']
            elif not before.empty:
                row = before.iloc[-1]
                nav_value = row['nav']
                nav_date = row['date']
            else:
                nav_value = None
                nav_date = None
        monthly_nav.append({'year': year, 'month': month, 'nav': nav_value, 'nav_date': nav_date})
    return monthly_nav

def calculate_changes(nav_list):
    data = []
    previous = None
    for entry in nav_list:
        change = None
        if previous and entry['nav'] is not None and previous['nav'] is not None:
            change = ((entry['nav'] - previous['nav']) / previous['nav']) * 100
        data.append({
            'Year': entry['year'],
            'Month': datetime(entry['year'], entry['month'], 1).strftime('%b'),
            'NAV Date': entry['nav_date'].strftime('%Y-%m-%d') if entry['nav_date'] else "N/A",
            'NAV': entry['nav'],
            '% Change (MoM)': change
        })
        previous = entry
    return pd.DataFrame(data)

st.title("Mutual Fund NAV Tracker")
st.write("Tracks NAV on the 3rd of each month and shows month-over-month % change.")

for fund_name, code in FUNDS.items():
    st.header(fund_name)
    df = fetch_nav(code)

    if df.empty:
        st.write("No data available for the selected fund.")
        continue

    nav_list = get_monthly_nav(df)
    df_changes = calculate_changes(nav_list)

    st.write("Data Preview:")
    st.dataframe(df_changes, hide_index=True, width=1000)

    if all(col in df_changes.columns for col in ['Year', 'Month', 'NAV']):
        st.line_chart(df_changes.set_index(['Year', 'Month'])['NAV'])
    else:
        st.write("Missing columns for line chart: 'Year', 'Month', or 'NAV'.")

    if '% Change (MoM)' in df_changes.columns:
        st.bar_chart(df_changes.set_index(['Year', 'Month'])['% Change (MoM)'])
    else:
        st.write("Column '% Change (MoM)' is missing for bar chart.")