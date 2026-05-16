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
from sqlalchemy import create_engine
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


# ── DATA FUNCTIONS ────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def load_by_year():
    return pd.read_sql("SELECT * FROM v_incidents_by_year", get_engine())

@st.cache_data(ttl=86400)
def load_heatmap():
    return pd.read_sql("SELECT x AS lon, y AS lat FROM v_heatmap", get_engine())

@st.cache_data(ttl=86400)
def load_years():
    df = pd.read_sql("SELECT DISTINCT year FROM crime_incidents WHERE year IS NOT NULL ORDER BY year", get_engine())
    return df["year"].astype(int).tolist()

@st.cache_data(ttl=86400)
def load_neighbourhoods():
    df = pd.read_sql("SELECT DISTINCT neighbourhood FROM crime_incidents WHERE neighbourhood IS NOT NULL ORDER BY neighbourhood", get_engine())
    return df["neighbourhood"].tolist()

@st.cache_data(ttl=86400)
def load_types():
    df = pd.read_sql("SELECT DISTINCT type FROM crime_incidents WHERE type IS NOT NULL ORDER BY type", get_engine())
    return df["type"].tolist()

@st.cache_data(ttl=86400)
def load_filtered(year_min, year_max, neighbourhood, crime_type):
    engine = get_engine()
    conditions = [f"year BETWEEN {year_min} AND {year_max}"]
    if neighbourhood != "All":
        conditions.append(f"neighbourhood = '{neighbourhood}'")
    if crime_type != "All":
        conditions.append(f"type = '{crime_type}'")
    where = " AND ".join(conditions)

    type_q = f"SELECT type, COUNT(*) AS incident_count FROM crime_incidents WHERE {where} GROUP BY type ORDER BY incident_count DESC LIMIT 10"
    neigh_q = f"SELECT neighbourhood, COUNT(*) AS incident_count FROM crime_incidents WHERE {where} GROUP BY neighbourhood ORDER BY incident_count DESC"
    month_q = f"SELECT month, COUNT(*) AS incident_count FROM crime_incidents WHERE {where} GROUP BY month ORDER BY month"
    total_q = f"SELECT COUNT(*) AS total FROM crime_incidents WHERE {where}"

    return (
        pd.read_sql(type_q, engine),
        pd.read_sql(neigh_q, engine),
        pd.read_sql(month_q, engine),
        pd.read_sql(total_q, engine).iloc[0]["total"],
    )


# ── SIDEBAR FILTERS ───────────────────────────────────────────────────────────

st.sidebar.header("Filters")

years = load_years()
neighbourhoods = load_neighbourhoods()
crime_types = load_types()

selected_years = st.sidebar.slider(
    "Year range",
    min_value=int(min(years)),
    max_value=int(max(years)),
    value=(2019, int(max(years))),
)
selected_neighbourhood = st.sidebar.selectbox("Neighbourhood", ["All"] + neighbourhoods)
selected_type = st.sidebar.selectbox("Crime type", ["All"] + crime_types)


# ── LOAD DATA WITH PROGRESS BAR ───────────────────────────────────────────────

progress = st.progress(0, text="Connecting to database...")

df_year = load_by_year()
progress.progress(25, text="Loading crime trends...")

df_heatmap = load_heatmap()
progress.progress(50, text="Loading heatmap data...")

df_type_f, df_neigh_f, df_month_f, total_filtered = load_filtered(
    selected_years[0], selected_years[1], selected_neighbourhood, selected_type
)
progress.progress(100, text="Done!")
progress.empty()

df_year_f = df_year[df_year["year"].between(selected_years[0], selected_years[1])]


# ── KPI ROW ───────────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Incidents", f"{int(total_filtered):,}")
col2.metric("Crime Types", int(df_type_f["type"].nunique()))
col3.metric("Neighbourhoods", int(df_neigh_f["neighbourhood"].nunique()))
col4.metric("Years Covered", f"{selected_years[0]}–{selected_years[1]}")

st.divider()

# ── HEATMAP ───────────────────────────────────────────────────────────────────

st.subheader("🔥 Crime Heatmap")
st.caption(
    "Showing property crimes only (theft, B&E, mischief) — "
    "these have precise block-level coordinates. "
    "Offences Against a Person are excluded from the map due to VPD privacy offsetting."
)

if len(df_heatmap) > 0:
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=df_heatmap,
        get_position=["lon", "lat"],
        aggregation="MEAN",
        threshold=0.05,
        radius_pixels=30,
    )
    view_state = pdk.ViewState(latitude=49.2487, longitude=-123.1153, zoom=11, pitch=0)
    st.pydeck_chart(pdk.Deck(
        layers=[heatmap_layer],
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    ))
    st.caption(f"Plotting {len(df_heatmap):,} incidents with valid coordinates.")
else:
    st.info("No incidents with valid coordinates match your current filters.")

st.divider()

# ── CHARTS ────────────────────────────────────────────────────────────────────

left, right = st.columns(2)

with left:
    st.subheader("📈 Incidents by Year")
    fig_trend = px.bar(
        df_year_f, x="year", y="incident_count",
        color_discrete_sequence=["#e63946"],
        labels={"year": "Year", "incident_count": "Incidents"},
    )
    fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_trend, use_container_width=True)

with right:
    st.subheader("🏷️ Top Crime Types")
    fig_types = px.bar(
        df_type_f, x="incident_count", y="type",
        orientation="h",
        color_discrete_sequence=["#457b9d"],
        labels={"incident_count": "Incidents", "type": "Crime Type"},
    )
    fig_types.update_layout(yaxis={"categoryorder": "total ascending"}, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_types, use_container_width=True)

st.subheader("📍 Incidents by Neighbourhood")
fig_n = px.bar(
    df_neigh_f, x="neighbourhood", y="incident_count",
    color_discrete_sequence=["#2a9d8f"],
    labels={"neighbourhood": "Neighbourhood", "incident_count": "Incidents"},
)
fig_n.update_layout(xaxis_tickangle=-35, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
st.plotly_chart(fig_n, use_container_width=True)

st.subheader("📅 Seasonal Pattern (by Month)")
month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
             7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
df_month_f["month_name"] = df_month_f["month"].map(month_map)
fig_m = px.line(
    df_month_f, x="month", y="incident_count",
    markers=True,
    color_discrete_sequence=["#e9c46a"],
    labels={"month": "Month", "incident_count": "Incidents"},
)
fig_m.update_xaxes(tickvals=list(range(1, 13)), ticktext=list(month_map.values()))
fig_m.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig_m, use_container_width=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Data source: Vancouver Police Department Open Data (geodash.vpd.ca). "
    "Built by [Lucas Nishimoto](https://lucasnishimoto.dev) · "
    "Pipeline: Python + PostgreSQL (AWS RDS) + Streamlit"
)