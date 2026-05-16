# Vancouver Crime Analytics Pipeline

End-to-end data pipeline that extracts, transforms, and loads Vancouver Police Department crime data into a cloud PostgreSQL database, then visualizes it in an interactive Streamlit dashboard.

**🔗 Live demo:** [vancouver-crime-analytics.streamlit.app](https://vancouver-crime-pipeline-3f5cvrnp5ywa7jwtfbkerl.streamlit.app/)

---

## Architecture

```
VPD Open Data (CSV)
      │
      ▼
 Python ETL (src/etl.py)
  ├── Extract: load all CSVs from data/raw/
  ├── Transform: clean, normalize, convert coords (UTM Zone 10N → WGS84)
  └── Load: insert into AWS RDS (PostgreSQL) with indexes
      │
      ▼
 AWS RDS PostgreSQL
  └── Aggregated views (src/run_views.py)
      │
      ▼
 Streamlit Dashboard (dashboard/app.py)
  ├── Crime heatmap (pydeck HeatmapLayer)
  ├── Trend by year (Plotly bar)
  ├── Top crime types (Plotly horizontal bar)
  ├── Incidents by neighbourhood
  └── Seasonal pattern by month
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| ETL | Pandas, SQLAlchemy, PyProj |
| Cloud DB | AWS RDS (PostgreSQL 15) |
| Dashboard | Streamlit, Plotly, Pydeck |
| Deploy | Streamlit Cloud |

---

## Dataset

**Source:** [Vancouver Police Department Open Data](https://geodash.vpd.ca/opendata/)  
**Coverage:** 2003–2026, all 24 Vancouver neighbourhoods  
**Records:** 880,249 incidents after cleaning  
**Update frequency:** Every Sunday  

> **Privacy note:** VPD deliberately offsets coordinates for *Offences Against a Person* to protect victim privacy. The heatmap uses property crimes only (theft, B&E, mischief), which have accurate block-level coordinates.

---

## Key Findings

**Vancouver is actually getting safer — the data says so.**

A common narrative among Vancouver residents is that the city is becoming increasingly unsafe. The data tells a different story:

- **Crime is trending down.** Annual incidents peaked around 2003–2004 (~55k/year) and have declined significantly over two decades, reaching ~31k in 2024–2025. Both property crimes and serious offences like homicide follow this downward trend.
- **Theft From Vehicle is the #1 crime type** (~250k incidents over the full dataset), followed by Other Theft (~243k) and Mischief (~115k). Violent crime represents a small fraction of total incidents.
- **Central Business District accounts for the most incidents** by a wide margin (~225k total), roughly 3x the second-ranked neighbourhood (West End). This is consistent with its high pedestrian density and commercial activity — not necessarily a sign of danger for residents.
- **Seasonal pattern follows Vancouver's climate.** Crime peaks in August (~79k incidents 
historically), driven by summer foot traffic and tourism. It then declines through the 
fall and winter, reaching its lowest point in February — consistent with Vancouver's 
rainy season reducing street activity. An interesting secondary peak appears in January, 
possibly linked to post-holiday activity before the February low.
- **794,794 incidents** have precise geospatial coordinates, enabling the heatmap to clearly show concentration hotspots in Downtown, the West End corridor, and along major arterials.

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/Lucasyuki01/vancouver-crime-pipeline
cd vancouver-crime-pipeline
pip install -r requirements.txt
```

### 2. Download the data

Go to [geodash.vpd.ca/opendata](https://geodash.vpd.ca/opendata), accept the disclaimer, select **All Years** + **All Neighbourhoods**, and download the CSVs into `data/raw/`.

### 3. Set up AWS RDS

1. Create a **PostgreSQL 15** instance on AWS RDS (free tier eligible: `db.t4g.micro`)
2. Set inbound rule in Security Group to allow port `5432`
3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 4. Run the ETL

```bash
# Test without loading to DB
python src/etl.py --dry-run

# Full load (~880k rows)
python src/etl.py
```

### 5. Create aggregated views

```bash
python src/run_views.py
```

### 6. Run the dashboard locally

```bash
streamlit run dashboard/app.py
```

---

## Author

**Lucas Nishimoto** — Data Science student at Cornerstone International Community College, Vancouver BC.  
[lucasnishimoto.dev](https://lucasnishimoto.dev) · [LinkedIn](https://www.linkedin.com/in/lucas-yuki-nishimoto-baaa55290/) · [GitHub](https://github.com/Lucasyuki01)