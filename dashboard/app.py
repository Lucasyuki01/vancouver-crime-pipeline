"""
app.py — Vancouver Crime Analytics Dashboard
Connects to AWS RDS PostgreSQL and renders interactive visualizations.

Run locally:
    streamlit run dashboard/app.py
"""

import os
import pandas as pd
import streamlit as st
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vancouver Crime Analytics",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Vancouver Crime Analytics")
st.markdown(
    "Interactive analysis of crime incidents reported by the "
    "[Vancouver Police Department](https://geodash.vpd.ca/opendata/). "
    "Data updated weekly. Coordinates for *Offences Against a Person* are "
    "deliberately offset by VPD to protect privacy."
)

# ── DB CONNECTION ─────────────────────────────────────────────────────────────

@st.cache_resource
def get_engine():
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "crimedb")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    engine = get_engine()
    query = "SELECT * FROM crime_incidents"
    return pd.read_sql(query, engine)


# ── LOAD & FILTER ─────────────────────────────────────────────────────────────

with st.spinner("Loading data from database..."):
    df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

years = sorted(df["year"].dropna().astype(int).unique())
selected_years = st.sidebar.slider(
    "Year range",
    min_value=int(min(years)),
    max_value=int(max(years)),
    value=(2019, int(max(years))),
)

neighbourhoods = ["All"] + sorted(df["neighbourhood"].dropna().unique())
selected_neighbourhood = st.sidebar.selectbox("Neighbourhood", neighbourhoods)

crime_types = ["All"] + sorted(df["type"].dropna().unique())
selected_type = st.sidebar.selectbox("Crime type", crime_types)

# Apply filters
mask = (df["year"] >= selected_years[0]) & (df["year"] <= selected_years[1])
if selected_neighbourhood != "All":
    mask &= df["neighbourhood"] == selected_neighbourhood
if selected_type != "All":
    mask &= df["type"] == selected_type

filtered = df[mask]

# ── KPI ROW ───────────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Incidents", f"{len(filtered):,}")
col2.metric("Crime Types", filtered["type"].nunique())
col3.metric("Neighbourhoods", filtered["neighbourhood"].nunique())
col4.metric("Years Covered", f"{selected_years[0]}–{selected_years[1]}")

st.divider()

# ── HEATMAP ───────────────────────────────────────────────────────────────────

st.subheader("🔥 Crime Heatmap")
st.caption(
    "Showing property crimes only (theft, B&E, mischief) — "
    "these have precise block-level coordinates. "
    "Offences Against a Person are excluded from the map due to VPD privacy offsetting."
)

map_df = filtered[filtered["has_coords"] == True].dropna(subset=["x", "y"])
map_df = map_df.rename(columns={"x": "lon", "y": "lat"})

# VPD uses BC Albers projection — need to check if coords are lat/lon or projected
# Typical VPD export uses lat/lon (WGS84). Values around -123, 49 are Vancouver.
map_df = map_df[(map_df["lat"].between(49.0, 49.4)) & (map_df["lon"].between(-123.3, -122.9))]

if len(map_df) > 0:
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=map_df[["lat", "lon"]],
        get_position=["lon", "lat"],
        aggregation="MEAN",
        threshold=0.05,
        radius_pixels=30,
    )

    view_state = pdk.ViewState(
        latitude=49.2487,
        longitude=-123.1153,
        zoom=11,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[heatmap_layer],
            initial_view_state=view_state,
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        )
    )
    st.caption(f"Plotting {len(map_df):,} incidents with valid coordinates.")
else:
    st.info("No incidents with valid coordinates match your current filters.")

st.divider()

# ── CHARTS ROW ────────────────────────────────────────────────────────────────

left, right = st.columns(2)

# Trend over time
with left:
    st.subheader("📈 Incidents by Year")
    trend = filtered.groupby("year").size().reset_index(name="count")
    fig_trend = px.bar(
        trend, x="year", y="count",
        color_discrete_sequence=["#e63946"],
        labels={"year": "Year", "count": "Incidents"},
    )
    fig_trend.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# By crime type
with right:
    st.subheader("🏷️ Top Crime Types")
    top_types = (
        filtered["type"].value_counts().head(10).reset_index()
    )
    top_types.columns = ["type", "count"]
    fig_types = px.bar(
        top_types, x="count", y="type",
        orientation="h",
        color_discrete_sequence=["#457b9d"],
        labels={"count": "Incidents", "type": "Crime Type"},
    )
    fig_types.update_layout(
        yaxis={"categoryorder": "total ascending"},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig_types, use_container_width=True)

# Neighbourhood ranking
st.subheader("📍 Incidents by Neighbourhood")
neighbourhood_counts = (
    filtered.groupby("neighbourhood").size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
fig_n = px.bar(
    neighbourhood_counts,
    x="neighbourhood", y="count",
    color_discrete_sequence=["#2a9d8f"],
    labels={"neighbourhood": "Neighbourhood", "count": "Incidents"},
)
fig_n.update_layout(
    xaxis_tickangle=-35,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    showlegend=False,
)
st.plotly_chart(fig_n, use_container_width=True)

# Monthly seasonality
st.subheader("📅 Seasonal Pattern (by Month)")
month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
             7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
monthly = filtered.groupby("month").size().reset_index(name="count")
monthly["month_name"] = monthly["month"].map(month_map)
fig_m = px.line(
    monthly, x="month", y="count",
    markers=True,
    color_discrete_sequence=["#e9c46a"],
    labels={"month": "Month", "count": "Avg Incidents"},
)
fig_m.update_xaxes(tickvals=list(range(1, 13)), ticktext=list(month_map.values()))
fig_m.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_m, use_container_width=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Data source: Vancouver Police Department Open Data (geodash.vpd.ca). "
    "Built by [Lucas Nishimoto](https://lucasnishimoto.dev) · "
    "Pipeline: Python + PostgreSQL (AWS RDS) + Streamlit"
)
