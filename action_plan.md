# NYC Flights 2023 — Interactive Dash Dashboard Action Plan

## Overview

Convert the NYC flights SQL analysis from HW3 into a multi-page interactive Dash dashboard using Plotly for all visualizations. The dashboard will feature an airplane/aviation theme and include an interactive route map.

**Data:** 435K flights from 3 NYC airports (JFK, EWR, LGA) to 118 destinations, operated by 14 carriers, across all 12 months of 2023. Airport coordinates available for map visualizations.

---

## Dashboard Structure (4 Pages)

### Page 1: Flight Routes Map (Hero Page)

**Purpose:** Interactive geographic view of all routes from NYC — the "wow factor" page with the plane icon theme.

**Visualizations:**
- **Plotly Scattergeo map** showing all routes as arcs from NYC to destination airports
  - Arcs colored by airline or by average delay
  - Arc thickness proportional to flight volume
  - Airplane marker icons on the 3 NYC origin airports
  - Hover shows: route, airline, avg delay, flight count
- **KPI cards** at the top: total flights, total destinations, total carriers, overall avg delay

**Interactive elements:**
- Dropdown: filter by origin airport (JFK / EWR / LGA / All)
- Dropdown: filter by carrier (all 14 airlines)
- Dropdown: color arcs by metric (flight count / avg departure delay / avg arrival delay / avg speed)

---

### Page 2: Airline Performance

**Purpose:** Converts Tasks 2, 4, and 6 from the notebook — carrier-level summaries and delay analysis.

**Visualizations:**
- **Horizontal bar chart:** flights per carrier (Task 2) — full airline names from the JOIN
- **Grouped bar chart:** avg departure delay vs avg arrival delay per airline (Task 6)
- **Scatter plot:** avg distance vs avg delay per airline (from Task 6 data), bubble size = total flights

**Interactive elements:**
- Dropdown: select metric for sorting (total flights / avg dep delay / avg arr delay / avg distance)
- Range slider: filter by month (1–12) so users can compare seasonal airline performance
- Radio buttons: toggle between departure delay and arrival delay views

---

### Page 3: Delay Deep Dive

**Purpose:** Converts Tasks 1 and 3 — individual flight delays and time-made-up analysis.

**Visualizations:**
- **Histogram/Distribution:** departure delay distribution for selected airport(s), with a vertical line at 60 min (the Task 1 threshold)
- **Scatter plot:** dep_delay vs arr_delay, colored by carrier — shows time made up (Task 3). Points below the diagonal = time made up in the air
- **Heatmap:** average departure delay by month × hour-of-day (uses `month` and `hour` columns from flights)

**Interactive elements:**
- Dropdown: filter by origin (JFK / EWR / LGA / All)
- Multi-select dropdown: filter by carrier(s)
- Range slider: filter by month
- Slider: minimum departure delay threshold (to focus on significantly delayed flights)

---

### Page 4: Fleet & Speed

**Purpose:** Converts Task 5 — flight speed analysis, extended with plane/fleet data from the `planes` table.

**Visualizations:**
- **Bar chart:** top 20 fastest routes by avg speed (Task 5)
- **Box plot:** speed distribution by carrier
- **Scatter plot:** aircraft age (from `planes.year`) vs avg speed, bubble size = number of flights

**Interactive elements:**
- Dropdown: filter by origin airport
- Dropdown: filter by manufacturer (from planes table)
- Slider: minimum number of flights (to filter out low-volume routes in speed chart)

---

## Existing Analyses Mapped to Dashboard

| Notebook Task | What it does | Dashboard Page | Plotly Equivalent |
|---|---|---|---|
| Task 1 — Filter JFK delays > 60 | SQL filter + sort | Page 3 | Interactive histogram with threshold line |
| Task 2 — Flights per carrier | GROUP BY + COUNT | Page 2 | Horizontal bar chart |
| Task 3 — Time made up in air | Computed column | Page 3 | Scatter plot (dep vs arr delay) |
| Task 4 — Flights with airline names | JOIN flights-airlines | Page 2 | Used in all carrier charts |
| Task 5 — Flight speed | JOIN + computed speed | Page 4 | Bar chart + box plot |
| Task 6 — Airline delay summary | GROUP BY + AVG | Page 2 | Grouped bar + scatter |
| *New* — Route map | Not in notebook | Page 1 | Scattergeo with arcs |
| *New* — Delay heatmap | Not in notebook | Page 3 | Heatmap (month × hour) |

---

## File Structure

```
HW3/
├── nycflights23/            # existing data folder
│   ├── flights.csv
│   ├── airlines.csv
│   ├── airports.csv
│   └── planes.csv
├── app.py                   # main Dash app (multi-page layout, navbar, callbacks)
├── requirements.txt         # dash, plotly, pandas, gunicorn
└── action_plan.md           # this file
```

Single-file `app.py` approach — keeps it simple for a homework project and easy to deploy on Render.

---

## Tech Choices

- **Dash** with `dash-bootstrap-components` for clean layout and responsive grid
- **Plotly Express** for charts, **Plotly Graph Objects** for the map (more control over arcs/markers)
- Dark/aviation-themed styling using a Bootstrap dark theme (e.g., `DARKLY` or `CYBORG`)
- Airplane emoji/icons in the navbar and KPI cards for the aviation theme
- All data loaded once at startup from local CSVs (no SQL at runtime)

---

## Waiting for your approval before writing any code.
