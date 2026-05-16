"""
run_views.py — Create aggregated views on AWS RDS
Run once after ETL load.

Usage:
    python src/run_views.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

VIEWS = {
    "v_incidents_by_year": """
        SELECT year, COUNT(*) AS incident_count
        FROM crime_incidents
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year
    """,
    "v_incidents_by_type": """
        SELECT type, COUNT(*) AS incident_count
        FROM crime_incidents
        WHERE type IS NOT NULL
        GROUP BY type
        ORDER BY incident_count DESC
    """,
    "v_incidents_by_neighbourhood": """
        SELECT neighbourhood, COUNT(*) AS incident_count
        FROM crime_incidents
        WHERE neighbourhood IS NOT NULL
        GROUP BY neighbourhood
        ORDER BY incident_count DESC
    """,
    "v_incidents_by_month": """
        SELECT month, COUNT(*) AS incident_count
        FROM crime_incidents
        WHERE month IS NOT NULL
        GROUP BY month
        ORDER BY month
    """,
    "v_heatmap": """
        SELECT x, y
        FROM crime_incidents
        WHERE has_coords = TRUE
          AND is_property_crime = TRUE
          AND x IS NOT NULL
          AND y IS NOT NULL
    """,
}


def get_engine():
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "crimedb")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)


def main():
    engine = get_engine()
    with engine.connect() as conn:
        for view_name, query in VIEWS.items():
            conn.execute(text(f"CREATE OR REPLACE VIEW {view_name} AS {query}"))
            print(f"  ✓ {view_name}")
        conn.commit()
    print("\n✅ All views created successfully!")


if __name__ == "__main__":
    main()