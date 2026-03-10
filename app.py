"""
NYC Flights 2023 — Interactive Dashboard
=========================================
Dash + Plotly dashboard analysing 435K+ flights from JFK, EWR & LGA in 2023.
Based on the SQL analysis in Santiago_Giorgini_HW3.ipynb.
"""

from pathlib import Path
import dash
from dash import dcc, html, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ================================================================
# DATA LOADING
# ================================================================

DATA_DIR = Path(__file__).parent / "nycflights23"

flights = pd.read_csv(DATA_DIR / "flights.csv")
airlines = pd.read_csv(DATA_DIR / "airlines.csv")
airports = pd.read_csv(DATA_DIR / "airports.csv")
planes = pd.read_csv(DATA_DIR / "planes.csv")

# ================================================================
# PREPROCESSING
# ================================================================

# Merge airline names into flights
flights = flights.merge(airlines, on="carrier", how="left")
flights.rename(columns={"name": "airline_name"}, inplace=True)

# Computed columns
flights["speed_mph"] = (flights["distance"] / flights["air_time"] * 60).round(1)
flights["time_made_up"] = flights["dep_delay"] - flights["arr_delay"]

MONTH_NAMES = {
    i: n
    for i, n in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1,
    )
}
flights["month_name"] = flights["month"].map(MONTH_NAMES)

# --- Route-level aggregations (for map) -------------------------
routes_agg = (
    flights.groupby(["origin", "dest"])
    .agg(
        flight_count=("flight", "count"),
        avg_dep_delay=("dep_delay", "mean"),
        avg_arr_delay=("arr_delay", "mean"),
        avg_speed=("speed_mph", "mean"),
        avg_distance=("distance", "mean"),
    )
    .reset_index()
)

# Merge origin / destination coordinates
origin_coords = airports[["faa", "name", "lat", "lon"]].rename(
    columns={"faa": "origin", "name": "origin_name",
             "lat": "lat_origin", "lon": "lon_origin"}
)
dest_coords = airports[["faa", "name", "lat", "lon"]].rename(
    columns={"faa": "dest", "name": "dest_name",
             "lat": "lat_dest", "lon": "lon_dest"}
)
routes_agg = (
    routes_agg
    .merge(origin_coords, on="origin", how="left")
    .merge(dest_coords, on="dest", how="left")
    .dropna(subset=["lat_origin", "lon_origin", "lat_dest", "lon_dest"])
)

# Per-carrier route aggregations (used when a specific carrier is selected)
routes_by_carrier = (
    flights.groupby(["origin", "dest", "carrier", "airline_name"])
    .agg(
        flight_count=("flight", "count"),
        avg_dep_delay=("dep_delay", "mean"),
        avg_arr_delay=("arr_delay", "mean"),
        avg_speed=("speed_mph", "mean"),
        avg_distance=("distance", "mean"),
    )
    .reset_index()
    .merge(origin_coords, on="origin", how="left")
    .merge(dest_coords, on="dest", how="left")
    .dropna(subset=["lat_origin", "lon_origin", "lat_dest", "lon_dest"])
)

# --- Flights + planes merge (for Fleet page) -------------------
flights_planes = flights.merge(
    planes[["tailnum", "year", "type", "manufacturer", "model",
            "seats", "engines", "engine"]],
    on="tailnum", how="left", suffixes=("", "_plane"),
)
flights_planes.rename(columns={"year_plane": "plane_year"}, inplace=True)

# ================================================================
# DROPDOWN OPTIONS
# ================================================================

carrier_pairs = (
    flights[["carrier", "airline_name"]]
    .drop_duplicates()
    .sort_values("airline_name")
    .values.tolist()
)
carrier_options = [{"label": "All Airlines", "value": "ALL"}] + [
    {"label": name, "value": code} for code, name in carrier_pairs
]

origin_options = [
    {"label": "All Airports", "value": "ALL"},
    {"label": "JFK — John F. Kennedy", "value": "JFK"},
    {"label": "EWR — Newark Liberty", "value": "EWR"},
    {"label": "LGA — LaGuardia", "value": "LGA"},
]

top_manufacturers = (
    flights_planes.dropna(subset=["manufacturer"])
    .groupby("manufacturer")["flight"].count()
    .nlargest(10).index.tolist()
)
manufacturer_options = [{"label": "All Manufacturers", "value": "ALL"}] + [
    {"label": m, "value": m} for m in sorted(top_manufacturers)
]

# ================================================================
# COLOURS & THEME
# ================================================================

ACCENT = "#00d4ff"

AIRLINE_COLORS = {
    "United Air Lines Inc.": "#005DAA",
    "Delta Air Lines Inc.": "#E01933",
    "American Airlines Inc.": "#0078D2",
    "JetBlue Airways": "#003876",
    "Southwest Airlines Co.": "#F9A01B",
    "Alaska Airlines Inc.": "#01426A",
    "Spirit Air Lines": "#FFE600",
    "Frontier Airlines Inc.": "#007B3E",
    "Republic Airline": "#6B7B8D",
    "Endeavor Air Inc.": "#4A5568",
    "Envoy Air": "#718096",
    "SkyWest Airlines Inc.": "#A0AEC0",
    "Hawaiian Airlines Inc.": "#7B2D8E",
    "Allegiant Air": "#F7941D",
    "PSA Airlines Inc.": "#5A7DA0",
}

CARD_STYLE = {
    "backgroundColor": "var(--bg-card, #12122a)",
    "border": "1px solid var(--border-dim, #1e1e3a)",
    "borderRadius": "14px",
}

# ================================================================
# APP INITIALISATION
# ================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=DM+Sans:ital,wght@0,400;0,500;0,700;1,400&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport",
                "content": "width=device-width, initial-scale=1"}],
)
app.title = "NYC Flights 2023"
server = app.server  # exposed for gunicorn

# ── Custom CSS injected via index_string ──────────────────────────
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
        /* ═══════════════════════════════════════════════════
           ROOT & TYPOGRAPHY
           ═══════════════════════════════════════════════════ */
        :root {
            --bg-deep: #060611;
            --bg-surface: #0d0d1a;
            --bg-card: #12122a;
            --bg-card-hover: #181840;
            --border-dim: #1e1e3a;
            --border-glow: #00d4ff22;
            --accent: #00d4ff;
            --accent-dim: #00d4ff44;
            --accent-glow: #00d4ff18;
            --text-primary: #e8eaf0;
            --text-muted: #7a7f9a;
            --gradient-accent: linear-gradient(135deg, #00d4ff 0%, #0088cc 100%);
        }

        body {
            font-family: 'DM Sans', -apple-system, sans-serif !important;
            background: var(--bg-deep) !important;
            color: var(--text-primary);
            -webkit-font-smoothing: antialiased;
        }

        h1, h2, h3, h4, h5, h6,
        .navbar-brand, .nav-link, .kpi-value {
            font-family: 'Sora', sans-serif !important;
        }

        /* ═══════════════════════════════════════════════════
           NAVBAR — cockpit instrument bar
           ═══════════════════════════════════════════════════ */
        .navbar {
            background: linear-gradient(180deg, #0a0a1e 0%, #060611 100%) !important;
            border-bottom: 1px solid var(--border-dim) !important;
            padding: 0.8rem 0 !important;
            position: relative;
        }
        .navbar::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: var(--gradient-accent);
            opacity: 0.7;
        }
        .navbar-brand {
            letter-spacing: 0.03em;
            font-weight: 700 !important;
        }

        /* ═══════════════════════════════════════════════════
           TABS — illuminated selector strip
           ═══════════════════════════════════════════════════ */
        .nav-tabs {
            border-bottom: 1px solid var(--border-dim) !important;
            gap: 4px;
        }
        .nav-tabs .nav-link {
            font-family: 'Sora', sans-serif !important;
            font-size: 0.85rem !important;
            font-weight: 500;
            color: var(--text-muted) !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 8px 8px 0 0 !important;
            padding: 0.65rem 1.2rem !important;
            transition: all 0.25s ease;
            letter-spacing: 0.02em;
        }
        .nav-tabs .nav-link:hover {
            color: var(--text-primary) !important;
            background: var(--accent-glow) !important;
            border-color: var(--border-dim) !important;
        }
        .nav-tabs .nav-link.active {
            color: var(--accent) !important;
            font-weight: 700 !important;
            background: var(--bg-card) !important;
            border-color: var(--border-dim) var(--border-dim) var(--bg-card) !important;
            box-shadow: 0 -2px 12px var(--accent-dim);
        }

        /* ═══════════════════════════════════════════════════
           CARDS — glass-panel instrument readouts
           ═══════════════════════════════════════════════════ */
        .dash-card {
            background: var(--bg-card) !important;
            border: 1px solid var(--border-dim) !important;
            border-radius: 14px !important;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }
        .dash-card:hover {
            border-color: var(--accent-dim) !important;
            box-shadow: 0 4px 24px rgba(0, 212, 255, 0.06);
        }

        /* KPI cards */
        .kpi-card {
            background: linear-gradient(145deg, #12122a 0%, #0e0e24 100%) !important;
            border: 1px solid var(--border-dim) !important;
            border-radius: 14px !important;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--gradient-accent);
            opacity: 0.5;
            transition: opacity 0.3s ease;
        }
        .kpi-card:hover {
            border-color: var(--accent-dim) !important;
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 212, 255, 0.08);
        }
        .kpi-card:hover::before {
            opacity: 1;
        }
        .kpi-label {
            font-family: 'DM Sans', sans-serif;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .kpi-value {
            font-family: 'Sora', sans-serif !important;
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--accent);
            line-height: 1.1;
        }
        .kpi-icon {
            font-size: 1.4rem;
            margin-right: 6px;
            opacity: 0.85;
        }

        /* ═══════════════════════════════════════════════════
           DROPDOWNS — Dash 4.x dark overrides
           ═══════════════════════════════════════════════════ */
        /* Trigger / closed state */
        .dash-dropdown-grid-container {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-dim) !important;
            border-radius: 10px !important;
            color: var(--text-primary) !important;
            transition: border-color 0.2s ease;
        }
        .dash-dropdown-grid-container:hover,
        .dash-dropdown-grid-container:focus-within {
            border-color: var(--accent-dim) !important;
        }
        .dash-dropdown-value,
        .dash-dropdown-value-item,
        .dash-dropdown input {
            color: var(--text-primary) !important;
        }
        .dash-dropdown input::placeholder {
            color: var(--text-muted) !important;
        }
        /* Clear & arrow icons */
        .dash-dropdown-clear svg,
        .dash-dropdown-trigger svg {
            fill: var(--text-muted) !important;
        }
        /* Open menu / listbox */
        .dash-dropdown-listbox,
        [role="listbox"] {
            background-color: #14143a !important;
            border: 1px solid var(--border-dim) !important;
            border-radius: 0 0 10px 10px !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
        }
        .dash-dropdown-option,
        [role="option"] {
            background-color: #14143a !important;
            color: var(--text-primary) !important;
            transition: background-color 0.15s ease;
        }
        .dash-dropdown-option:hover,
        .dash-dropdown-option[aria-selected="true"],
        [role="option"]:hover {
            background-color: #1e1e4a !important;
        }
        /* Multi-select chips */
        .dash-dropdown-chip {
            background-color: var(--accent-dim) !important;
            border: 1px solid var(--accent) !important;
            color: var(--text-primary) !important;
            border-radius: 6px !important;
        }
        .dash-dropdown-chip-remove svg {
            fill: var(--accent) !important;
        }

        /* Search box inside dropdown */
        .dash-dropdown-search-container {
            background-color: var(--bg-card) !important;
            border-color: var(--border-dim) !important;
        }
        .dash-dropdown-search {
            background-color: var(--bg-card) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-dim) !important;
            border-radius: 8px !important;
            caret-color: var(--accent);
        }
        .dash-dropdown-search::placeholder {
            color: var(--text-muted) !important;
        }

        /* Legacy React-Select fallback (older Dash) */
        .Select-control {
            background-color: var(--bg-card) !important;
            border-color: var(--border-dim) !important;
            color: var(--text-primary) !important;
        }
        .Select-menu-outer {
            background-color: #14143a !important;
            border: 1px solid var(--border-dim) !important;
        }
        .Select-value-label,
        .Select-placeholder,
        .Select-input > input {
            color: var(--text-primary) !important;
        }
        .Select-placeholder { color: var(--text-muted) !important; }
        .VirtualizedSelectOption { background-color: #14143a !important; color: var(--text-primary) !important; }
        .VirtualizedSelectFocusedOption { background-color: #1e1e4a !important; }

        /* ═══════════════════════════════════════════════════
           SLIDERS & RANGE SLIDERS — readable marks
           ═══════════════════════════════════════════════════ */
        .rc-slider-mark-text {
            color: var(--text-muted) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.72rem !important;
            font-weight: 500 !important;
        }
        .rc-slider-mark-text-active {
            color: var(--text-primary) !important;
        }
        .rc-slider-rail {
            background-color: var(--border-dim) !important;
            height: 4px !important;
        }
        .rc-slider-track {
            background: var(--gradient-accent) !important;
            height: 4px !important;
        }
        .rc-slider-handle {
            border-color: var(--accent) !important;
            background-color: var(--bg-card) !important;
            width: 16px !important;
            height: 16px !important;
            margin-top: -6px !important;
            box-shadow: 0 0 8px var(--accent-dim) !important;
            opacity: 1 !important;
        }
        .rc-slider-handle:hover,
        .rc-slider-handle:active,
        .rc-slider-handle-dragging {
            border-color: var(--accent) !important;
            box-shadow: 0 0 14px var(--accent-dim) !important;
        }
        .rc-slider-dot {
            border-color: var(--border-dim) !important;
            background-color: var(--bg-surface) !important;
        }
        .rc-slider-dot-active {
            border-color: var(--accent) !important;
        }

        /* ═══════════════════════════════════════════════════
           FILTER LABELS
           ═══════════════════════════════════════════════════ */
        .filter-label {
            font-family: 'Sora', sans-serif;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 6px;
        }

        /* ═══════════════════════════════════════════════════
           FOOTER
           ═══════════════════════════════════════════════════ */
        .site-footer {
            border-top: 1px solid var(--border-dim);
            padding: 1.2rem 0;
            margin-top: 2rem;
        }
        .site-footer p {
            font-family: 'DM Sans', sans-serif;
            font-size: 0.75rem;
            letter-spacing: 0.06em;
            color: var(--text-muted);
        }
        .site-footer .accent-dot {
            display: inline-block;
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: var(--accent);
            margin: 0 10px;
            vertical-align: middle;
            opacity: 0.6;
        }

        /* ═══════════════════════════════════════════════════
           PLOTLY CHART CONTAINERS
           ═══════════════════════════════════════════════════ */
        .js-plotly-plot .plotly .modebar {
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .js-plotly-plot:hover .plotly .modebar {
            opacity: 0.7;
        }

        /* ═══════════════════════════════════════════════════
           SCROLLBAR (webkit)
           ═══════════════════════════════════════════════════ */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-deep); }
        ::-webkit-scrollbar-thumb {
            background: var(--border-dim);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-dim);
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def kpi_card(title, value, icon=""):
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="kpi-label mb-0"),
            html.Div([
                html.Span(icon, className="kpi-icon") if icon else None,
                html.Span(value, className="kpi-value"),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={"padding": "1rem 1.2rem"}),
        className="kpi-card",
    )


def apply_dark_layout(fig, title="", height=450):
    """Apply consistent dark styling to any Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,30,47,0.8)",
        title=dict(text=title, font=dict(size=16, color="white")),
        margin=dict(l=40, r=20, t=50, b=40),
        height=height,
        font=dict(color="#ccc"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ================================================================
# PAGE LAYOUTS
# ================================================================

# ---------- PAGE 1: FLIGHT ROUTES MAP --------------------------

page1 = dbc.Container([
    dbc.Row(id="map-kpis", className="g-3 mb-3"),
    dbc.Row([
        dbc.Col([
            html.Label("Origin Airport", className="filter-label"),
            dcc.Dropdown(id="map-origin", options=origin_options, value="ALL",
                         className="dash-dropdown"),
        ], md=3),
        dbc.Col([
            html.Label("Airline", className="filter-label"),
            dcc.Dropdown(id="map-carrier", options=carrier_options, value="ALL",
                         className="dash-dropdown"),
        ], md=3),
        dbc.Col([
            html.Label("Color Destinations By", className="filter-label"),
            dcc.Dropdown(
                id="map-color-by",
                options=[
                    {"label": "Flight Count", "value": "flight_count"},
                    {"label": "Avg Departure Delay", "value": "avg_dep_delay"},
                    {"label": "Avg Arrival Delay", "value": "avg_arr_delay"},
                    {"label": "Avg Speed (mph)", "value": "avg_speed"},
                ],
                value="flight_count", className="dash-dropdown",
            ),
        ], md=3),
    ], className="mb-3"),
    dbc.Card(
        dcc.Graph(id="route-map", style={"height": "600px"}),
        className="dash-card p-2",
    ),
], fluid=True)


# ---------- PAGE 2: AIRLINE PERFORMANCE ------------------------

page2 = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Sort Airlines By", className="filter-label"),
            dcc.Dropdown(
                id="perf-sort",
                options=[
                    {"label": "Total Flights", "value": "total_flights"},
                    {"label": "Avg Departure Delay", "value": "avg_dep_delay"},
                    {"label": "Avg Arrival Delay", "value": "avg_arr_delay"},
                    {"label": "Avg Distance", "value": "avg_distance"},
                ],
                value="total_flights", className="dash-dropdown",
            ),
        ], md=3),
        dbc.Col([
            html.Label("Month Range", className="filter-label"),
            dcc.RangeSlider(
                id="perf-months", min=1, max=12, step=1, value=[1, 12],
                marks={i: MONTH_NAMES[i] for i in range(1, 13)},
                className="mt-2",
            ),
        ], md=9),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="perf-flights-bar"),
                         className="dash-card p-2"), md=6),
        dbc.Col(dbc.Card(dcc.Graph(id="perf-delay-bar"),
                         className="dash-card p-2"), md=6),
    ], className="g-3 mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="perf-scatter"),
                         className="dash-card p-2"), md=12),
    ], className="g-3"),
], fluid=True)


# ---------- PAGE 3: DELAY DEEP DIVE ---------------------------

page3 = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Origin", className="filter-label"),
            dcc.Dropdown(id="delay-origin", options=origin_options,
                         value="ALL", className="dash-dropdown"),
        ], md=2),
        dbc.Col([
            html.Label("Airlines", className="filter-label"),
            dcc.Dropdown(
                id="delay-carriers",
                options=[{"label": name, "value": code}
                         for code, name in carrier_pairs],
                value=[], multi=True, className="dash-dropdown",
                placeholder="All airlines",
            ),
        ], md=4),
        dbc.Col([
            html.Label("Month Range", className="filter-label"),
            dcc.RangeSlider(
                id="delay-months", min=1, max=12, step=1, value=[1, 12],
                marks={i: MONTH_NAMES[i] for i in range(1, 13)},
                className="mt-2",
            ),
        ], md=4),
        dbc.Col([
            html.Label("Min Delay (min)", className="filter-label"),
            dcc.Slider(
                id="delay-threshold", min=0, max=120, step=15, value=0,
                marks={0: "0", 30: "30", 60: "60", 90: "90", 120: "120+"},
            ),
        ], md=2),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="delay-histogram"),
                         className="dash-card p-2"), md=6),
        dbc.Col(dbc.Card(dcc.Graph(id="delay-scatter"),
                         className="dash-card p-2"), md=6),
    ], className="g-3 mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="delay-heatmap"),
                         className="dash-card p-2"), md=12),
    ], className="g-3"),
], fluid=True)


# ---------- PAGE 4: FLEET & SPEED ------------------------------

page4 = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Origin", className="filter-label"),
            dcc.Dropdown(id="speed-origin", options=origin_options,
                         value="ALL", className="dash-dropdown"),
        ], md=3),
        dbc.Col([
            html.Label("Manufacturer", className="filter-label"),
            dcc.Dropdown(id="speed-manufacturer",
                         options=manufacturer_options, value="ALL",
                         className="dash-dropdown"),
        ], md=3),
        dbc.Col([
            html.Label("Min Flights per Route", className="filter-label"),
            dcc.Slider(
                id="speed-min-flights", min=10, max=500, step=10, value=50,
                marks={10: "10", 100: "100", 250: "250", 500: "500"},
            ),
        ], md=6),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="speed-top-routes"),
                         className="dash-card p-2"), md=6),
        dbc.Col(dbc.Card(dcc.Graph(id="speed-box"),
                         className="dash-card p-2"), md=6),
    ], className="g-3 mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="speed-age-scatter"),
                         className="dash-card p-2"), md=12),
    ], className="g-3"),
], fluid=True)


# ================================================================
# MAIN LAYOUT
# ================================================================

app.layout = html.Div([
    # --- Navbar ---
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand(
                [html.Span("\u2708\uFE0F",
                           style={"fontSize": "1.6rem", "marginRight": "12px",
                                  "filter": "drop-shadow(0 0 6px rgba(0,212,255,0.4))"}),
                 html.Span("NYC FLIGHTS", style={"fontWeight": "800",
                                                  "letterSpacing": "0.06em"}),
                 html.Span(" 2023", style={"fontWeight": "300",
                                            "color": ACCENT,
                                            "marginLeft": "6px"})],
                style={"fontSize": "1.3rem", "display": "flex",
                        "alignItems": "center"},
            ),
            html.Span([
                html.Span("435K+ flights",
                           style={"color": "#e8eaf0", "fontWeight": "600"}),
                html.Span(" from JFK, EWR & LGA",
                           style={"color": "#7a7f9a"}),
            ], className="d-none d-md-inline",
               style={"fontFamily": "'DM Sans', sans-serif",
                       "fontSize": "0.85rem"}),
        ], fluid=True),
        dark=True, className="mb-3",
    ),

    # --- Tabs ---
    dbc.Container([
        dbc.Tabs([
            dbc.Tab(page1, label="\U0001F5FA Route Map", tab_id="tab-map"),
            dbc.Tab(page2, label="\U0001F4CA Airline Performance",
                    tab_id="tab-perf"),
            dbc.Tab(page3, label="\u23F1 Delay Deep Dive",
                    tab_id="tab-delay"),
            dbc.Tab(page4, label="\U0001F6E9 Fleet & Speed",
                    tab_id="tab-speed"),
        ], id="tabs", active_tab="tab-map", className="mb-3"),
    ], fluid=True),

    # --- Footer ---
    html.Footer(
        html.P([
            "Santiago Giorgini",
            html.Span(className="accent-dot"),
            "Data Science with Python",
            html.Span(className="accent-dot"),
            "HW3",
        ], className="text-center mb-0"),
        className="site-footer",
    ),
], style={"backgroundColor": "var(--bg-deep, #060611)", "minHeight": "100vh"})


# ================================================================
# CALLBACKS — PAGE 1: ROUTE MAP
# ================================================================

@callback(
    Output("map-kpis", "children"),
    Output("route-map", "figure"),
    Input("map-origin", "value"),
    Input("map-carrier", "value"),
    Input("map-color-by", "value"),
)
def update_map(origin, carrier, color_by):
    # ---- pick the right pre-aggregated routes -------------------
    if carrier == "ALL":
        df = routes_agg.copy()
    else:
        df = (
            routes_by_carrier[routes_by_carrier["carrier"] == carrier]
            .groupby(["origin", "dest", "origin_name", "dest_name",
                      "lat_origin", "lon_origin", "lat_dest", "lon_dest"])
            .agg(
                flight_count=("flight_count", "sum"),
                avg_dep_delay=("avg_dep_delay", "mean"),
                avg_arr_delay=("avg_arr_delay", "mean"),
                avg_speed=("avg_speed", "mean"),
                avg_distance=("avg_distance", "mean"),
            )
            .reset_index()
        )

    if origin != "ALL":
        df = df[df["origin"] == origin]

    # ---- KPI cards (from raw flights for accuracy) -------------
    flt = flights.copy()
    if origin != "ALL":
        flt = flt[flt["origin"] == origin]
    if carrier != "ALL":
        flt = flt[flt["carrier"] == carrier]

    kpis = [
        dbc.Col(kpi_card("Total Flights", f"{len(flt):,}", "\u2708"), md=3),
        dbc.Col(kpi_card("Destinations", f"{flt['dest'].nunique()}", "\U0001F4CD"), md=3),
        dbc.Col(kpi_card("Avg Dep Delay",
                         f"{flt['dep_delay'].mean():.1f} min", "\u23F1"), md=3),
        dbc.Col(kpi_card("Avg Speed",
                         f"{flt['speed_mph'].mean():.0f} mph", "\U0001F4A8"), md=3),
    ]

    # ---- build the map -----------------------------------------
    fig = go.Figure()

    if len(df) > 0:
        color_labels = {
            "flight_count": "Flights",
            "avg_dep_delay": "Avg Dep Delay (min)",
            "avg_arr_delay": "Avg Arr Delay (min)",
            "avg_speed": "Avg Speed (mph)",
        }
        color_scales = {
            "flight_count": "Blues",
            "avg_dep_delay": "RdYlGn_r",
            "avg_arr_delay": "RdYlGn_r",
            "avg_speed": "Viridis",
        }

        # Route arc lines — single trace, uniform styling
        lons, lats = [], []
        for _, row in df.iterrows():
            lons.extend([row["lon_origin"], row["lon_dest"], None])
            lats.extend([row["lat_origin"], row["lat_dest"], None])

        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, mode="lines",
            line=dict(width=0.8, color="rgba(0,212,255,0.25)"),
            hoverinfo="skip", showlegend=False,
        ))

        # Destination markers — coloured by metric
        fig.add_trace(go.Scattergeo(
            lon=df["lon_dest"], lat=df["lat_dest"], mode="markers",
            marker=dict(
                size=6 + (df["flight_count"] / df["flight_count"].max() * 14),
                color=df[color_by],
                colorscale=color_scales[color_by],
                colorbar=dict(title=color_labels[color_by], x=1.02),
                line=dict(width=0.5, color="white"),
                opacity=0.85,
            ),
            text=df["dest_name"],
            customdata=df[["dest", "flight_count", "avg_dep_delay",
                           "avg_arr_delay", "avg_speed"]].values,
            hovertemplate=(
                "<b>%{text}</b> (%{customdata[0]})<br>"
                "Flights: %{customdata[1]:,}<br>"
                "Avg Dep Delay: %{customdata[2]:.1f} min<br>"
                "Avg Arr Delay: %{customdata[3]:.1f} min<br>"
                "Avg Speed: %{customdata[4]:.0f} mph"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # NYC origin airports (always visible)
    nyc = airports[airports["faa"].isin(["JFK", "EWR", "LGA"])]
    fig.add_trace(go.Scattergeo(
        lon=nyc["lon"], lat=nyc["lat"],
        mode="markers+text",
        marker=dict(size=14, color=ACCENT, symbol="star",
                    line=dict(width=1, color="white")),
        text=nyc["faa"],
        textposition="top center",
        textfont=dict(size=12, color="white", family="Arial Black"),
        hovertext=nyc["name"], hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            scope="north america",
            bgcolor="rgba(13,13,26,1)",
            lakecolor="rgba(13,13,26,1)",
            landcolor="rgba(30,30,47,1)",
            coastlinecolor="#2d2d44",
            countrycolor="#2d2d44",
            subunitcolor="#2d2d44",
            showlakes=True, showcountries=True,
            showcoastlines=True, showsubunits=True,
            lonaxis=dict(range=[-130, -60]),
            lataxis=dict(range=[22, 52]),
        ),
        height=600,
        margin=dict(l=0, r=0, t=10, b=0),
    )

    return kpis, fig


# ================================================================
# CALLBACKS — PAGE 2: AIRLINE PERFORMANCE
# ================================================================

@callback(
    Output("perf-flights-bar", "figure"),
    Output("perf-delay-bar", "figure"),
    Output("perf-scatter", "figure"),
    Input("perf-sort", "value"),
    Input("perf-months", "value"),
)
def update_performance(sort_by, month_range):
    flt = flights[
        (flights["month"] >= month_range[0])
        & (flights["month"] <= month_range[1])
    ]

    summary = (
        flt.dropna(subset=["dep_delay", "arr_delay"])
        .groupby(["carrier", "airline_name"])
        .agg(
            total_flights=("flight", "count"),
            avg_dep_delay=("dep_delay", "mean"),
            avg_arr_delay=("arr_delay", "mean"),
            avg_distance=("distance", "mean"),
        )
        .reset_index()
        .sort_values(sort_by, ascending=(sort_by == "total_flights"))
    )

    # -- Flights per airline (horizontal bar) --------------------
    fig1 = px.bar(
        summary.sort_values("total_flights"),
        x="total_flights", y="airline_name", orientation="h",
        color="airline_name", color_discrete_map=AIRLINE_COLORS,
    )
    apply_dark_layout(fig1, "Flights per Airline")
    fig1.update_layout(showlegend=False, yaxis_title="")

    # -- Avg dep vs arr delay (grouped bar) ----------------------
    delay_melted = summary.melt(
        id_vars=["airline_name"],
        value_vars=["avg_dep_delay", "avg_arr_delay"],
        var_name="type", value_name="minutes",
    )
    delay_melted["type"] = delay_melted["type"].map(
        {"avg_dep_delay": "Departure", "avg_arr_delay": "Arrival"}
    )
    fig2 = px.bar(
        delay_melted, x="airline_name", y="minutes",
        color="type", barmode="group",
        color_discrete_map={"Departure": "#ff6b6b", "Arrival": "#ffd93d"},
    )
    apply_dark_layout(fig2, "Avg Delay by Airline (minutes)")
    fig2.update_layout(xaxis_tickangle=-45, xaxis_title="", legend_title="")

    # -- Distance vs delay scatter (bubble) ----------------------
    fig3 = px.scatter(
        summary, x="avg_distance", y="avg_dep_delay",
        size="total_flights", color="airline_name",
        color_discrete_map=AIRLINE_COLORS,
        hover_data=["total_flights", "avg_arr_delay"],
        size_max=50,
    )
    apply_dark_layout(fig3, "Distance vs Departure Delay (bubble = flights)",
                      height=400)
    fig3.update_layout(
        xaxis_title="Avg Distance (miles)",
        yaxis_title="Avg Dep Delay (min)",
        legend_title="",
    )

    return fig1, fig2, fig3


# ================================================================
# CALLBACKS — PAGE 3: DELAY DEEP DIVE
# ================================================================

@callback(
    Output("delay-histogram", "figure"),
    Output("delay-scatter", "figure"),
    Output("delay-heatmap", "figure"),
    Input("delay-origin", "value"),
    Input("delay-carriers", "value"),
    Input("delay-months", "value"),
    Input("delay-threshold", "value"),
)
def update_delays(origin, carriers, month_range, threshold):
    flt = flights.dropna(subset=["dep_delay", "arr_delay"]).copy()

    if origin != "ALL":
        flt = flt[flt["origin"] == origin]
    if carriers:
        flt = flt[flt["carrier"].isin(carriers)]
    flt = flt[
        (flt["month"] >= month_range[0]) & (flt["month"] <= month_range[1])
    ]
    delayed = flt[flt["dep_delay"] >= threshold]

    # -- Histogram -----------------------------------------------
    hist_data = delayed[delayed["dep_delay"] <= 300]
    fig1 = px.histogram(
        hist_data, x="dep_delay", nbins=60,
        color="origin" if origin == "ALL" else None,
        color_discrete_map={"JFK": "#00d4ff", "EWR": "#ff6b6b",
                            "LGA": "#51cf66"},
        opacity=0.75,
    )
    fig1.add_vline(x=60, line_dash="dash", line_color="#ff6b6b",
                   annotation_text="60 min",
                   annotation_font_color="#ff6b6b")
    apply_dark_layout(fig1, f"Departure Delay Distribution (\u2265 {threshold} min)")
    fig1.update_layout(xaxis_title="Dep Delay (min)", yaxis_title="Flights",
                       legend_title="")

    # -- Scatter: dep vs arr delay (Task 3 — time made up) -------
    sample = (delayed.sample(min(5000, len(delayed)), random_state=42)
              if len(delayed) > 5000 else delayed)
    fig2 = px.scatter(
        sample, x="dep_delay", y="arr_delay",
        color="airline_name", color_discrete_map=AIRLINE_COLORS,
        opacity=0.4, render_mode="webgl",
    )
    max_val = max(
        sample["dep_delay"].max() if len(sample) else 100,
        sample["arr_delay"].max() if len(sample) else 100,
        100,
    )
    fig2.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                   line=dict(color="white", width=1, dash="dash"))
    fig2.add_annotation(
        x=max_val * 0.7, y=max_val * 0.45,
        text="Below line = time made up \u2708",
        font=dict(color="#51cf66", size=11), showarrow=False,
    )
    apply_dark_layout(fig2, "Departure vs Arrival Delay")
    fig2.update_layout(
        xaxis_title="Dep Delay (min)", yaxis_title="Arr Delay (min)",
        legend_title="", legend=dict(font=dict(size=9)),
    )

    # -- Heatmap: avg delay by month x hour ----------------------
    heat = (
        flt.groupby(["month", "hour"])["dep_delay"]
        .mean().reset_index()
        .pivot(index="hour", columns="month", values="dep_delay")
    )
    heat.columns = [MONTH_NAMES.get(c, c) for c in heat.columns]
    fig3 = px.imshow(
        heat, aspect="auto", color_continuous_scale="RdYlGn_r",
        labels=dict(x="Month", y="Hour of Day", color="Avg Delay (min)"),
    )
    apply_dark_layout(fig3, "Avg Departure Delay by Month & Hour", height=400)

    return fig1, fig2, fig3


# ================================================================
# CALLBACKS — PAGE 4: FLEET & SPEED
# ================================================================

@callback(
    Output("speed-top-routes", "figure"),
    Output("speed-box", "figure"),
    Output("speed-age-scatter", "figure"),
    Input("speed-origin", "value"),
    Input("speed-manufacturer", "value"),
    Input("speed-min-flights", "value"),
)
def update_speed(origin, manufacturer, min_flights):
    flt = flights_planes.dropna(subset=["speed_mph", "air_time"]).copy()

    if origin != "ALL":
        flt = flt[flt["origin"] == origin]
    if manufacturer != "ALL":
        flt = flt[flt["manufacturer"] == manufacturer]

    # -- Top 20 fastest routes (Task 5) --------------------------
    route_speed = (
        flt.groupby(["origin", "dest"])
        .agg(avg_speed=("speed_mph", "mean"),
             flight_count=("flight", "count"))
        .reset_index()
    )
    route_speed = route_speed[route_speed["flight_count"] >= min_flights]
    route_speed = route_speed.merge(
        airports[["faa", "name"]].rename(
            columns={"faa": "dest", "name": "dest_name"}),
        on="dest", how="left",
    )
    route_speed["route"] = (
        route_speed["origin"] + " \u2192 "
        + route_speed["dest"] + " ("
        + route_speed["dest_name"].fillna("") + ")"
    )
    top20 = route_speed.nlargest(20, "avg_speed")

    fig1 = px.bar(
        top20.sort_values("avg_speed"),
        x="avg_speed", y="route", orientation="h",
        color="avg_speed", color_continuous_scale="Viridis",
    )
    apply_dark_layout(fig1, "Top 20 Fastest Routes (avg mph)")
    fig1.update_layout(yaxis_title="", xaxis_title="Avg Speed (mph)",
                       coloraxis_showscale=False)

    # -- Speed distribution by carrier (box plot) ----------------
    box_sample = flt.sample(min(20000, len(flt)), random_state=42)
    fig2 = px.box(
        box_sample, x="airline_name", y="speed_mph",
        color="airline_name", color_discrete_map=AIRLINE_COLORS,
    )
    apply_dark_layout(fig2, "Speed Distribution by Airline")
    fig2.update_layout(xaxis_tickangle=-45, xaxis_title="",
                       yaxis_title="Speed (mph)", showlegend=False)

    # -- Aircraft age vs speed -----------------------------------
    age = flt.dropna(subset=["plane_year"]).copy()
    age["plane_age"] = 2023 - age["plane_year"]
    age = age[age["plane_age"].between(0, 50)]

    age_summary = (
        age.groupby(["plane_age", "airline_name"])
        .agg(avg_speed=("speed_mph", "mean"),
             num_flights=("flight", "count"))
        .reset_index()
    )
    age_summary = age_summary[age_summary["num_flights"] >= 20]

    fig3 = px.scatter(
        age_summary, x="plane_age", y="avg_speed",
        size="num_flights", color="airline_name",
        color_discrete_map=AIRLINE_COLORS,
        size_max=30, hover_data=["num_flights"],
    )
    apply_dark_layout(fig3, "Aircraft Age vs Average Speed", height=400)
    fig3.update_layout(xaxis_title="Aircraft Age (years)",
                       yaxis_title="Avg Speed (mph)", legend_title="")

    return fig1, fig2, fig3


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
