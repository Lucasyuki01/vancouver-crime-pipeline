# Vancouver Crime Analytics Pipeline

End-to-end data pipeline that extracts, transforms, and loads Vancouver Police Department crime data into a cloud PostgreSQL database, then visualizes it in an interactive Streamlit dashboard.

**Live demo:** [your-app.streamlit.app](https://your-app.streamlit.app)

---

## Architecture

```
VPD Open Data (CSV)
      │
      ▼
 Python ETL (src/etl.py)
  ├── Extract: load all CSVs from data/raw/
  ├── Transform: clean, normalize, flag coord availability
  └── Load: insert into AWS RDS (PostgreSQL) with indexes
      │
      ▼
 AWS RDS PostgreSQL
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
| ETL | Pandas, SQLAlchemy |
| Cloud DB | AWS RDS (PostgreSQL 15) |
| Dashboard | Streamlit, Plotly, Pydeck |
| Deploy | Streamlit Cloud |

---

## Dataset

**Source:** [Vancouver Police Department Open Data](https://geodash.vpd.ca/opendata/)  
**Coverage:** 2003–present, all 24 Vancouver neighbourhoods  
**Update frequency:** Every Sunday  
**Key fields:** `TYPE`, `YEAR`, `MONTH`, `DAY`, `HOUR`, `MINUTE`, `HUNDRED_BLOCK`, `NEIGHBOURHOOD`, `X`, `Y`

> **Privacy note:** VPD deliberately offsets coordinates for *Offences Against a Person* to protect victim privacy. The heatmap uses property crimes only (theft, B&E, mischief), which have accurate block-level coordinates.

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

1. Create a **PostgreSQL 15** instance on AWS RDS (free tier eligible: `db.t3.micro`)
2. Set inbound rule in Security Group to allow port `5432` from your IP
3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 4. Run the ETL

```bash
# Test without loading to DB
python src/etl.py --dry-run

# Full load
python src/etl.py
```

### 5. Run the dashboard locally

```bash
streamlit run dashboard/app.py
```

---

## Key Findings

*(To be filled after running the pipeline)*

- Most common crime type: ...
- Highest-crime neighbourhood: ...
- Peak crime month: ...
- YoY trend since 2020: ...

---

## Author

**Lucas Nishimoto** — Data Science student at Cornerstone International Community College, Vancouver BC.  
[lucasnishimoto.dev](https://lucasnishimoto.dev) · [LinkedIn](https://www.linkedin.com/in/lucas-yuki-nishimoto-baaa55290/) · [GitHub](https://github.com/Lucasyuki01)
