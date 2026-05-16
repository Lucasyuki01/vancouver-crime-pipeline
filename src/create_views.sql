-- create_views.sql
-- Aggregated views for Vancouver Crime Analytics Dashboard
-- Run once after ETL load: python src/run_views.py

-- ── 1. Incidents by year ─────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_incidents_by_year AS
SELECT
    year,
    COUNT(*) AS incident_count
FROM crime_incidents
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year;

-- ── 2. Incidents by crime type ───────────────────────────────────────────────
CREATE OR REPLACE VIEW v_incidents_by_type AS
SELECT
    type,
    COUNT(*) AS incident_count
FROM crime_incidents
WHERE type IS NOT NULL
GROUP BY type
ORDER BY incident_count DESC;

-- ── 3. Incidents by neighbourhood ────────────────────────────────────────────
CREATE OR REPLACE VIEW v_incidents_by_neighbourhood AS
SELECT
    neighbourhood,
    COUNT(*) AS incident_count
FROM crime_incidents
WHERE neighbourhood IS NOT NULL
GROUP BY neighbourhood
ORDER BY incident_count DESC;

-- ── 4. Seasonal pattern (by month) ───────────────────────────────────────────
CREATE OR REPLACE VIEW v_incidents_by_month AS
SELECT
    month,
    COUNT(*) AS incident_count
FROM crime_incidents
WHERE month IS NOT NULL
GROUP BY month
ORDER BY month;

-- ── 5. Summary stats (for KPI cards) ─────────────────────────────────────────
CREATE OR REPLACE VIEW v_summary AS
SELECT
    COUNT(*)                        AS total_incidents,
    COUNT(DISTINCT type)            AS crime_types,
    COUNT(DISTINCT neighbourhood)   AS neighbourhoods,
    MIN(year)                       AS year_min,
    MAX(year)                       AS year_max
FROM crime_incidents;

-- ── 6. Heatmap coords (property crimes only, sampled for performance) ─────────
CREATE OR REPLACE VIEW v_heatmap AS
SELECT x, y
FROM crime_incidents
WHERE has_coords = TRUE
  AND is_property_crime = TRUE
  AND x IS NOT NULL
  AND y IS NOT NULL;
