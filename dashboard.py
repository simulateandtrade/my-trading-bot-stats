import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Server Analytics", layout="wide")
st.title("📊 Community Engagement Dashboard")

def load_data():
    conn = sqlite3.connect('analytics.db')
    df = pd.read_sql_query("SELECT * FROM daily_stats", conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    return df

df = load_data()

# 1. Sidebar Filters
st.sidebar.header("Date Range")
start_date = st.sidebar.date_input("Start Date", df['date'].min())
end_date = st.sidebar.date_input("End Date", df['date'].max())

mask = (df['date'] >= pd.Timestamp(start_date)) & (df['date'] <= pd.Timestamp(end_date))
f_df = df.loc[mask].copy()

# 2. Key Metrics (The Header Boxes)
avg_uniques = f_df['uniques'].mean()
total_msgs = f_df['msgs'].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total Messages", f"{total_msgs:,}")
col2.metric("Unique Members (Total)", f"{f_df['uniques'].sum():,}")
col3.metric("Daily Average Uniques", f"{avg_uniques:.2f}")

# 3. The Main Graph (Bars + Moving Average)
st.subheader("Daily Unique Messengers")

# Create the Bar Chart
fig = px.bar(f_df, x='date', y='uniques', 
             labels={'uniques': 'Unique Members', 'date': 'Date'},
             color_discrete_sequence=['#7d54b2']) # Matching that purple in your screenshot

# Add the "Moving Average" line (7-day trend)
f_df['moving_avg'] = f_df['uniques'].rolling(window=7).mean()
fig.add_trace(go.Scatter(x=f_df['date'], y=f_df['moving_avg'], 
                         mode='lines', name='7-Day Trend', 
                         line=dict(color='#ffa500', width=3)))

fig.update_layout(hovermode="x unified", template="plotly_dark", 
                  showlegend=False, height=500)
st.plotly_chart(fig, use_container_width=True)

# 4. Secondary Growth Chart
st.subheader("Total Member Growth")
fig_growth = px.area(f_df, x='date', y='total_mems', color_discrete_sequence=['#2ecc71'])
fig_growth.update_layout(template="plotly_dark", height=300)
st.plotly_chart(fig_growth, use_container_width=True)