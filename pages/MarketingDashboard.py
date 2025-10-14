import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime
import os 
from helpers.auth import check_password

if not check_password():
    st.stop()

date_query = datetime.now().strftime("%Y-%m-%d_%H")+"H"

df = pd.read_parquet(f"dataMarket/downloads_daily.parquet")
df["date"] = pd.to_datetime(df["created_at_date"])
df["verified_pct"] = round(df["verified"] / df["total"] * 100, 2)

# --- Weekly aggregation ---
df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="d")
df_weekly = (
    df.groupby("week_start", as_index=False)
      .agg({"verified": "sum", "not_verified": "sum", "total": "sum"})
)
df_weekly["verified_pct"] = round(df_weekly["verified"] / df_weekly["total"] * 100, 2)

# --- Streamlit App ---
st.set_page_config(page_title="Marketing Analysis Dashboard", layout="wide")
st.title("📬 Marketing Funnel Analysis Dashboard")

# Calendar filter
min_date, max_date = df["date"].min(), df["date"].max()
date_range = st.date_input("Select date range:", [min_date, max_date])

mask = (df["date"] >= pd.to_datetime(date_range[0])) & (df["date"] <= pd.to_datetime(date_range[1]))
df_filtered = df.loc[mask].copy()

df_daily = (
    df_filtered.groupby("date", as_index=False)[["verified", "not_verified", "total"]]
               .sum()
)
df_daily["verified_pct"] = round(df_daily["verified"] / df_daily["total"] * 100, 2)

# 2️⃣ Build dual-axis chart
fig_daily = go.Figure()

# Bars: verified / not verified counts
fig_daily.add_trace(go.Bar(
    x=df_daily["date"],
    y=df_daily["verified"],
    name="Verified",
    marker_color="#2ecc71",
))
fig_daily.add_trace(go.Bar(
    x=df_daily["date"],
    y=df_daily["not_verified"],
    name="Not Verified",
    marker_color="#e74c3c",
))

# Line: % verified (on secondary y-axis)
fig_daily.add_trace(go.Scatter(
    x=df_daily["date"],
    y=df_daily["verified_pct"],
    name="Verification Rate (%)",
    mode="lines+markers",
    marker=dict(size=8, color="#3498db"),
    line=dict(width=2, color="#3498db"),
    yaxis="y2",
))

# 3️⃣ Layout & styling
fig_daily.update_layout(
    title="Daily Verification Funnel (Counts + %)",
    xaxis_title="Date",
    yaxis_title="Number of Users",
    yaxis2=dict(
        title="Verification Rate (%)",
        overlaying="y",
        side="right",
        range=[0, 100],
        showgrid=False
    ),
    barmode="stack",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    template="plotly_white",
)

st.plotly_chart(fig_daily, use_container_width=True)

# --- Weekly summary ---
st.subheader("🗓️ Weekly Summary")

fig_weekly = px.bar(
    df_weekly,
    x="week_start",
    y="verified_pct",
    text="verified_pct",
    title="Weekly Verification Rate (%)",
)
fig_weekly.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
st.plotly_chart(fig_weekly, use_container_width=True)

# --- KPIs ---
st.subheader("📊 Key Metrics")
col1, col2 = st.columns(2)
col1.metric("Total Verified", int(df_filtered["verified"].sum()))
col2.metric("Average Verification Rate", f"{df_filtered['verified_pct'].mean():.2f}%")