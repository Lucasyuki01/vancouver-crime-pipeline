"""
etl.py — Vancouver Crime Data Pipeline
Reads raw VPD CSVs from data/raw/, cleans them, and loads into PostgreSQL (AWS RDS).

Usage:
    python src/etl.py                        # load to DB
    python src/etl.py --dry-run              # just print sample, no DB
"""

import os
import glob
import argparse
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


# ── 1. EXTRACT ────────────────────────────────────────────────────────────────

def extract(raw_dir: str = RAW_DIR) -> pd.DataFrame:
    """Load all CSVs from data/raw/ and concatenate into one DataFrame."""
    files = glob.glob(os.path.join(raw_dir, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir}. Download them from geodash.vpd.ca/opendata")

    frames = []
    for f in sorted(files):
        df = pd.read_csv(f, low_memory=False)
        frames.append(df)
        print(f"  ✓ Loaded {os.path.basename(f)} — {len(df):,} rows")

    combined = pd.concat(frames, ignore_index=True)
    print(f"\n  Total rows combined: {len(combined):,}")
    return combined


# ── 2. TRANSFORM ──────────────────────────────────────────────────────────────

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize the raw VPD data."""

    # Standardize column names (VPD CSVs use ALL CAPS)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    print(f"\n  Columns found: {list(df.columns)}")

    # Expected columns from VPD dataset:
    # TYPE, YEAR, MONTH, DAY, HOUR, MINUTE, HUNDRED_BLOCK, NEIGHBOURHOOD, X, Y

    # Drop rows with no neighbourhood or type
    df = df.dropna(subset=["type", "neighbourhood"])

    # Clean strings
    df["type"] = df["type"].str.strip().str.title()
    df["neighbourhood"] = df["neighbourhood"].str.strip().str.title()

    # Build a proper datetime column where possible
    # (HOUR/MINUTE are missing for Offences Against a Person — privacy)
    df["hour"] = pd.to_numeric(df.get("hour", pd.Series(dtype=float)), errors="coerce")
    df["minute"] = pd.to_numeric(df.get("minute", pd.Series(dtype=float)), errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["day"] = pd.to_numeric(df.get("day", pd.Series(dtype=float)), errors="coerce")

    # Coordinates — VPD uses BC Albers (EPSG:3153), convert to lat/lon (WGS84)
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:26910", "EPSG:4326", always_xy=True)

    df["x"] = pd.to_numeric(df.get("x", pd.Series(dtype=float)), errors="coerce")
    df["y"] = pd.to_numeric(df.get("y", pd.Series(dtype=float)), errors="coerce")

    # Flag: coords available or not (Offences Against Person have no coords)
    df["has_coords"] = df["x"].notna() & df["y"].notna()

    # Convert projected coords to lon/lat where available
    mask_coords = df["has_coords"]
    lon, lat = transformer.transform(
        df.loc[mask_coords, "x"].values,
        df.loc[mask_coords, "y"].values,
    )
    df.loc[mask_coords, "x"] = lon
    df.loc[mask_coords, "y"] = lat

    # Sanity check — Vancouver should be around lon -123, lat 49
    valid_range = (
        df["x"].between(-123.3, -122.9) & df["y"].between(49.0, 49.4)
    )
    df.loc[mask_coords & ~valid_range, "has_coords"] = False

    # Crime category grouping (high level)
    property_crimes = [
        "Theft Of Vehicle", "Theft From Vehicle", "Other Theft",
        "Break And Enter Commercial", "Break And Enter Residential/Other",
        "Mischief", "Vehicle Collision Or Pedestrian Struck (With Fatality)",
        "Vehicle Collision Or Pedestrian Struck (With Injury)"
    ]
    df["is_property_crime"] = df["type"].isin(property_crimes)

    # Remove exact duplicates
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Removed {before - len(df):,} duplicate rows")

    # Final column selection
    keep_cols = [
        "type", "year", "month", "day", "hour", "minute",
        "hundred_block", "neighbourhood", "x", "y",
        "has_coords", "is_property_crime"
    ]
    # Only keep columns that exist
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols]

    print(f"  Clean rows ready to load: {len(df):,}")
    print(f"\n  Crime types found:")
    print(df["type"].value_counts().to_string())

    return df


# ── 3. LOAD ───────────────────────────────────────────────────────────────────

def get_engine():
    """Create SQLAlchemy engine from environment variables."""
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "crimedb")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([host, user, password]):
        raise EnvironmentError(
            "Missing DB env vars. Set DB_HOST, DB_USER, DB_PASSWORD in your .env file."
        )

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)


def load(df: pd.DataFrame, table: str = "crime_incidents", if_exists: str = "replace"):
    """Load DataFrame into PostgreSQL table."""
    engine = get_engine()

    print(f"\n  Connecting to database...")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"  ✓ Connection successful")

    print(f"  Loading {len(df):,} rows into table '{table}'...")
    df.to_sql(table, engine, if_exists=if_exists, index=False, chunksize=5000)
    print(f"  ✓ Load complete")

    # Create indexes for dashboard query performance
    with engine.connect() as conn:
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_year ON {table} (year)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_neighbourhood ON {table} (neighbourhood)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_type ON {table} (type)"))
        conn.commit()
    print(f"  ✓ Indexes created")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip DB load, just print stats")
    args = parser.parse_args()

    print("=" * 50)
    print("VANCOUVER CRIME PIPELINE — ETL")
    print("=" * 50)

    print("\n[1/3] Extracting...")
    df_raw = extract()

    print("\n[2/3] Transforming...")
    df_clean = transform(df_raw)

    if args.dry_run:
        print("\n[DRY RUN] Skipping DB load. Sample output:")
        print(df_clean.head(10).to_string())
        return

    print("\n[3/3] Loading to PostgreSQL (AWS RDS)...")
    load(df_clean)

    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
