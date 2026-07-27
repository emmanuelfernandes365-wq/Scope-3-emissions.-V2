"""
Maritime Scope 3 Intelligence — Streamlit demonstration app.

A single-file Streamlit dashboard reading pre-processed, dashboard-ready
JSON from ./data/. No preprocessing, ZIP extraction, or DOCX parsing
happens at runtime — every figure shown here was computed once, offline,
from the underlying synthetic datasets.

Run locally:
    streamlit run streamlit_app.py

Deploy on Streamlit Community Cloud by pointing the app at this file.
"""
import json
import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Maritime Scope 3 Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .kpi-card {
        background: #102638;
        border: 1px solid #1c3a54;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 6px;
    }
    .kpi-label {
        color: #8fa9bd;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }
    .kpi-value {
        color: #F5F7FA;
        font-size: 1.5rem;
        font-weight: 700;
    }
    .kpi-sub {
        color: #6b8598;
        font-size: 0.72rem;
    }
    .inferred-badge {
        display: inline-block;
        background: rgba(230, 168, 23, 0.15);
        border: 1px solid rgba(230, 168, 23, 0.4);
        color: #e6c257;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.72rem;
        margin-left: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Cached data loading + safe-access helpers
# ----------------------------------------------------------------------
@st.cache_data
def load_json(relative_path: str):
    """Loads a JSON file from ./data/<relative_path>. Returns None (no UI
    noise) if the file is missing, unreadable, or not valid JSON — the
    one-time startup check below is responsible for surfacing a genuine
    deployment problem; individual page sections degrade quietly."""
    path = DATA_DIR / relative_path
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj


def safe_get(d, key, default=None):
    """dict.get() that also treats None/NaN as 'missing' so downstream
    formatting never has to special-case both at once."""
    if not isinstance(d, dict):
        return default
    v = d.get(key, default)
    if v is None:
        return default
    if isinstance(v, float) and math.isnan(v):
        return default
    return v


def safe_float(value, default=None):
    """Convert a value to a finite float; return default on invalid input."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def numeric_series(series):
    """Coerce a pandas Series to numeric values, replacing invalid values with NaN."""
    return pd.to_numeric(series, errors="coerce")


def safe_list(obj, key):
    """Returns obj[key] if it's a non-empty list, else []."""
    if not isinstance(obj, dict):
        return []
    v = obj.get(key)
    return v if isinstance(v, list) else []


def safe_df(records, columns=None):
    """Builds a DataFrame from a list of dict records, dropping records
    that aren't dicts, and guaranteeing the requested columns exist
    (filled with None) so downstream .head()/column selection never
    raises a KeyError on a malformed or partially-missing record."""
    if not isinstance(records, list):
        return pd.DataFrame(columns=columns or [])
    clean = [r for r in records if isinstance(r, dict)]
    skipped = len(records) - len(clean)
    if skipped > 0:
        st.caption(f"⚠️ Skipped {skipped} malformed record(s) in this dataset.")
    df = pd.DataFrame(clean)
    if columns:
        for c in columns:
            if c not in df.columns:
                df[c] = None
    return df


def has_columns(df, columns):
    return isinstance(df, pd.DataFrame) and not df.empty and all(c in df.columns for c in columns)


def kpi_card(col, label, value, sub=None):
    with col:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
            </div>""",
            unsafe_allow_html=True,
        )


def fmt_tonnes(n):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "—"
    try:
        return f"{float(n):,.0f} tCO2e"
    except (TypeError, ValueError):
        return "—"


def fmt_usd(n):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if n >= 1_000_000:
        return f"${n/1_000_000:,.1f}M"
    if n >= 1_000:
        return f"${n/1_000:,.0f}K"
    return f"${n:,.0f}"


def fmt_num(n):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "—"
    try:
        return f"{float(n):,.0f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(n):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "—"
    try:
        return f"{float(n):.1f}%"
    except (TypeError, ValueError):
        return "—"


CHART_TEMPLATE = "plotly_dark"
COLOR_SEQ = px.colors.qualitative.Set2


def demo_badge():
    """Small, restrained badge — not styled as a warning or alert."""
    st.markdown(
        '<span style="display:inline-block;background:#1c3a54;color:#8fa9bd;'
        'border-radius:999px;padding:2px 12px;font-size:0.72rem;margin-bottom:0.75rem;">'
        '🔹 Demo environment · Representative data</span>',
        unsafe_allow_html=True,
    )


def inferred_badge():
    st.markdown('<span class="inferred-badge">Inferred — not explicitly stated in the source report</span>', unsafe_allow_html=True)


def empty_state(message="Not available."):
    st.caption(message)


# ----------------------------------------------------------------------
# One-time startup data check. If deployment paths are broken, this shows
# a single concise message (with technical detail in an expander) and
# stops — rather than letting every page fail separately with repeated
# "not found" banners.
# ----------------------------------------------------------------------
REQUIRED_FILES = [
    "global/summary.json",
    "global/hub-comparison.json",
    "global/data-quality.json",
    "singapore/summary.json",
    "singapore/emissions.json",
    "singapore/suppliers.json",
    "singapore/shipments.json",
    "singapore/routes.json",
    "singapore/procurement.json",
    "singapore/ai-insights.json",
    "singapore/scenarios.json",
    "singapore/digital-twin.json",
    "singapore/audit-trails.json",
    "dubai/summary.json",
    "dubai/emissions.json",
    "dubai/suppliers.json",
    "dubai/shipments.json",
    "dubai/routes.json",
    "dubai/procurement.json",
    "dubai/ai-insights.json",
    "dubai/scenarios.json",
    "dubai/digital-twin.json",
    "dubai/audit-trails.json",
    "strategy/architecture.json",
    "strategy/differentiation.json",
    "strategy/roadmap.json",
    "strategy/executive-story.json",
    "strategy/source-notes.json",
]


def check_deployment():
    """Return missing or invalid required JSON files."""
    problems = []
    for relative in REQUIRED_FILES:
        path = DATA_DIR / relative
        if not path.is_file():
            problems.append((relative, "missing"))
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            problems.append((relative, "invalid JSON"))
    return problems


_deployment_problems = check_deployment()
if _deployment_problems:
    st.error("Dashboard data is unavailable because required application files are missing or invalid.")
    with st.expander("Technical details"):
        st.write("The following required data files could not be loaded:")
        for relative, reason in _deployment_problems:
            st.code(f"data/{relative} — {reason}", language="text")
    st.stop()

# ----------------------------------------------------------------------
# Sidebar navigation
# ----------------------------------------------------------------------
st.sidebar.title("🌊 Maritime Scope 3 Intelligence")
st.sidebar.caption("Procurement, logistics and emissions visibility across global maritime hubs")

PAGES = [
    "Global Overview",
    "Singapore Hub",
    "Dubai Hub",
    "Strategy & Product Architecture",
    "Competitive Differentiation",
    "Product Roadmap",
    "Data & Methodology",
]
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.caption("🔹 Demo environment · Representative data")


# ----------------------------------------------------------------------
# Shared hub-page renderer (Singapore and Dubai use the identical layout,
# parameterized by hub key — this is why there's one function, not two)
# ----------------------------------------------------------------------
def render_hub_page(hub_key: str, hub_label: str):
    summary = load_json(f"{hub_key}/summary.json")
    if not isinstance(summary, dict):
        st.error("Hub summary data is unavailable — the rest of this page cannot render.")
        return

    st.title(f"{hub_label} Hub")
    st.caption(
        "Container transshipment, port operations, ASEAN distribution, and electronics/semiconductor supply chains."
        if hub_key == "singapore"
        else "Maritime procurement, supplier ESG, purchase-order-to-emissions traceability, and GCC regional distribution."
    )
    demo_badge()

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Scope 3 Emissions", fmt_tonnes(safe_get(summary, "total_co2e_tonnes")),
              f"{fmt_tonnes(safe_get(summary, 'maritime_procurement_co2e_tonnes'))} maritime procurement")
    kpi_card(c2, "Procurement Spend", fmt_usd(safe_get(summary, "total_procurement_spend_usd")))
    kpi_card(c3, "Active Suppliers", fmt_num(safe_get(summary, "active_suppliers")),
              f"{fmt_num(safe_get(summary, 'high_risk_suppliers'))} high-risk")
    kpi_card(c4, "Shipments Monitored", fmt_num(safe_get(summary, "shipments_monitored")),
              f"{fmt_num(safe_get(summary, 'shipment_legs'))} legs")

    c5, c6, c7, c8 = st.columns(4)
    kpi_card(c5, "Delayed Shipments", fmt_num(safe_get(summary, "delayed_shipments")))
    kpi_card(c6, "Reduction Opportunities", fmt_num(safe_get(summary, "reduction_opportunities_count")))
    kpi_card(c7, "Open High-Priority AI Insights", fmt_num(safe_get(summary, "open_ai_insights_high_priority")))
    kpi_card(c8, "Assurance Coverage", fmt_pct(safe_get(summary, "assurance_coverage_pct")))

    st.markdown("")
    tabs = st.tabs([
        "📊 Emissions", "🚢 Shipments & Map", "🏭 Suppliers", "🧾 Procurement",
        "🤖 AI Insights", "🎬 Scenarios", "🕸️ Digital Twin", "🔍 Audit Trail",
    ])

    # ---- Emissions ----
    with tabs[0]:
        em = load_json(f"{hub_key}/emissions.json")
        if not isinstance(em, dict):
            empty_state("Emissions data is unavailable for this hub.")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                trend_df = safe_df(safe_list(em, "kpi_trend"), columns=["period", "total_co2e_tonnes", "maritime_co2e_tonnes"])
                if has_columns(trend_df, ["period", "total_co2e_tonnes", "maritime_co2e_tonnes"]):
                    fig = px.line(trend_df, x="period", y=["total_co2e_tonnes", "maritime_co2e_tonnes"],
                                  template=CHART_TEMPLATE, color_discrete_sequence=COLOR_SEQ,
                                  labels={"value": "tCO2e", "period": "Month", "variable": ""})
                    fig.update_layout(height=320, legend=dict(orientation="h", y=-0.25))
                    st.plotly_chart(fig, width="stretch")
                else:
                    empty_state("No emissions trend data available.")
            with col_b:
                mode_df = safe_df(safe_list(em, "by_mode"), columns=["mode", "co2e_tonnes"])
                if has_columns(mode_df, ["mode", "co2e_tonnes"]):
                    fig = px.bar(mode_df, x="mode", y="co2e_tonnes", template=CHART_TEMPLATE,
                                 color="mode", color_discrete_sequence=COLOR_SEQ,
                                 labels={"co2e_tonnes": "tCO2e", "mode": "Transport mode"})
                    fig.update_layout(height=320, showlegend=False)
                    st.plotly_chart(fig, width="stretch")
                else:
                    empty_state("No emissions-by-mode data available.")

            cat_df = safe_df(safe_list(em, "by_category"), columns=["category_name", "co2e_tonnes"])
            if has_columns(cat_df, ["category_name", "co2e_tonnes"]):
                fig = px.bar(cat_df, x="category_name", y="co2e_tonnes", template=CHART_TEMPLATE,
                             color="category_name", color_discrete_sequence=COLOR_SEQ,
                             labels={"co2e_tonnes": "tCO2e", "category_name": "Scope 3 category"})
                fig.update_layout(height=380, showlegend=False, xaxis_tickangle=-30)
                st.plotly_chart(fig, width="stretch")
            else:
                empty_state("No Scope 3 category breakdown available.")

            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("**Top vessels by emissions**")
                vdf = safe_df(safe_list(em, "by_vessel_top20"))
                if not vdf.empty:
                    st.dataframe(vdf.head(10), width="stretch", hide_index=True)
                else:
                    empty_state("No vessel emissions data available.")
            with col_d:
                st.markdown("**Emissions by port**")
                pdf = safe_df(safe_list(em, "by_port"), columns=["co2e_tonnes"])
                if has_columns(pdf, ["co2e_tonnes"]):
                    pdf = pdf.sort_values("co2e_tonnes", ascending=False).head(10)
                    st.dataframe(pdf, width="stretch", hide_index=True)
                else:
                    empty_state("No port emissions data available.")

    # ---- Shipments & Map ----
    with tabs[1]:
        routes = load_json(f"{hub_key}/routes.json")
        ships = load_json(f"{hub_key}/shipments.json")

        ports_df = safe_df(safe_list(routes, "ports"), columns=["port_id", "port_name", "lat", "lon", "is_major_hub", "country", "port_type"]) if routes else pd.DataFrame()
        if not ports_df.empty:
            ports_df["lat"] = numeric_series(ports_df["lat"])
            ports_df["lon"] = numeric_series(ports_df["lon"])
            ports_df = ports_df[
                ports_df["lat"].between(-90, 90, inclusive="both")
                & ports_df["lon"].between(-180, 180, inclusive="both")
            ].copy()
        route_records = [r for r in safe_list(routes, "routes") if isinstance(r, dict)] if routes else []
        # Only keep routes where both origin and destination have valid numeric coordinates
        valid_routes = []
        for r in route_records:
            o, d = r.get("origin") or {}, r.get("destination") or {}
            try:
                olat, olon, dlat, dlon = float(o.get("lat")), float(o.get("lon")), float(d.get("lat")), float(d.get("lon"))
            except (TypeError, ValueError):
                continue
            if not all(-90 <= v <= 90 for v in (olat, dlat)) or not all(-180 <= v <= 180 for v in (olon, dlon)):
                continue
            valid_routes.append((olat, olon, dlat, dlon, o.get("name", "Origin"), d.get("name", "Destination")))

        ports_ok = has_columns(ports_df, ["lat", "lon"])

        if ports_ok:
            if valid_routes:
                st.markdown("**Port network & synthetic illustrative routes** — straight-line connections between synthetic port coordinates, NOT live vessel tracking")
            else:
                st.markdown("**Port network** — synthetic coordinates only; no route geometry is available for this hub, so only port locations are shown")

            fig = go.Figure()

            if valid_routes:
                # Draw all route segments as a single trace, separated by
                # None so Plotly renders them as disconnected line segments
                # rather than one continuous path through every port.
                lats, lons = [], []
                for olat, olon, dlat, dlon, _, _ in valid_routes:
                    lats += [olat, dlat, None]
                    lons += [olon, dlon, None]
                fig.add_trace(go.Scattermap(
                    lat=lats, lon=lons, mode="lines",
                    line=dict(width=1, color="#2dd4bf"),
                    opacity=0.35, name="Synthetic illustrative routes",
                    hoverinfo="skip",
                ))

            major = ports_df[ports_df.get("is_major_hub", False) == True] if "is_major_hub" in ports_df.columns else ports_df.iloc[0:0]
            minor = ports_df[ports_df.get("is_major_hub", False) != True] if "is_major_hub" in ports_df.columns else ports_df

            for subset, color, size, label in [(minor, "#2F80ED", 8, "Port"), (major, "#e6c257", 12, "Major hub")]:
                if subset.empty:
                    continue
                fig.add_trace(go.Scattermap(
                    lat=subset["lat"], lon=subset["lon"], mode="markers",
                    marker=dict(size=size, color=color),
                    text=subset.get("port_name", ""), name=label,
                    hovertemplate="%{text}<extra></extra>",
                ))

            center_lat = ports_df["lat"].mean()
            center_lon = ports_df["lon"].mean()
            fig.update_layout(
                map=dict(style="carto-darkmatter", center=dict(lat=center_lat, lon=center_lon), zoom=3),
                height=420, margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(orientation="h", y=-0.05, bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig, width="stretch")
            if valid_routes:
                st.caption(f"{len(valid_routes)} synthetic illustrative route(s) shown — straight-line connections, not real vessel geometry or live tracking.")
            else:
                st.caption("Only port locations are shown; route geometry is not present in this dataset.")
        else:
            empty_state("No valid port coordinates available for this hub — the map cannot be rendered.")

        if isinstance(ships, dict):
            ship_list = [s for s in safe_list(ships, "list") if isinstance(s, dict)]
            total_count = safe_get(ships, "total_count", len(ship_list))
            st.markdown(f"**Shipments** — showing a sample ({fmt_num(total_count)} total in dataset)")
            modes_available = sorted({s.get("mode", "Unknown") for s in ship_list}) if ship_list else []
            if modes_available:
                mode_filter = st.multiselect("Filter by mode", options=modes_available, default=[], key=f"{hub_key}_mode_filter")
                rows = [s for s in ship_list if not mode_filter or s.get("mode") in mode_filter]
            else:
                rows = ship_list
            sdf = safe_df(rows[:30], columns=["shipment_id", "origin_port_name", "destination_port_name", "mode",
                                                "weight_tonnes", "co2e_tonnes", "status", "shipment_date"])
            if not sdf.empty:
                st.dataframe(
                    sdf[["shipment_id", "origin_port_name", "destination_port_name", "mode",
                          "weight_tonnes", "co2e_tonnes", "status", "shipment_date"]],
                    width="stretch", hide_index=True,
                )
            else:
                empty_state("No shipments match the selected filter.")
        else:
            empty_state("Shipment data is unavailable for this hub.")

    # ---- Suppliers ----
    with tabs[2]:
        sup = load_json(f"{hub_key}/suppliers.json")
        if not isinstance(sup, dict):
            empty_state("Supplier data is unavailable for this hub.")
        else:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                esg_dist = sup.get("esg_rating_distribution")
                if isinstance(esg_dist, dict) and esg_dist:
                    fig = px.pie(names=list(esg_dist.keys()), values=list(esg_dist.values()),
                                 template=CHART_TEMPLATE, color_discrete_sequence=COLOR_SEQ,
                                 title="ESG rating distribution")
                    fig.update_layout(height=320)
                    st.plotly_chart(fig, width="stretch")
                else:
                    empty_state("No ESG rating distribution available.")
            with col_b:
                st.markdown(f"**Top suppliers by annual spend** ({fmt_num(safe_get(sup, 'total_count', 0))} total suppliers)")
                sdf = safe_df(safe_list(sup, "list")[:15], columns=["supplier_name", "country", "annual_spend_usd",
                                                                      "carbon_intensity_score", "esg_rating", "supplier_risk"])
                if not sdf.empty:
                    st.dataframe(
                        sdf[["supplier_name", "country", "annual_spend_usd", "carbon_intensity_score",
                              "esg_rating", "supplier_risk"]],
                        width="stretch", hide_index=True,
                    )
                else:
                    empty_state("No supplier records available.")

    # ---- Procurement ----
    with tabs[3]:
        proc = load_json(f"{hub_key}/procurement.json")
        if not isinstance(proc, dict):
            empty_state("Procurement data is unavailable for this hub.")
        else:
            cat_df = safe_df(safe_list(proc, "by_category"), columns=["category_name", "spend_usd"])
            if has_columns(cat_df, ["category_name", "spend_usd"]):
                fig = px.bar(cat_df.sort_values("spend_usd", ascending=True), x="spend_usd", y="category_name",
                             orientation="h", template=CHART_TEMPLATE, color="category_name",
                             color_discrete_sequence=COLOR_SEQ, labels={"spend_usd": "Spend (USD)", "category_name": ""})
                fig.update_layout(height=420, showlegend=False)
                st.plotly_chart(fig, width="stretch")
            else:
                empty_state("No procurement spend-by-category data available.")

            st.markdown("**Carbon reduction opportunities**")
            rdf = safe_df(safe_list(proc, "reduction_opportunities"),
                           columns=["opportunity_type", "target_entity_type", "potential_co2e_reduction_tonnes",
                                     "estimated_cost_usd", "implementation_difficulty", "status"])
            if not rdf.empty:
                st.dataframe(
                    rdf[["opportunity_type", "target_entity_type", "potential_co2e_reduction_tonnes",
                          "estimated_cost_usd", "implementation_difficulty", "status"]],
                    width="stretch", hide_index=True,
                )
            else:
                empty_state("No reduction opportunities available.")

    # ---- AI Insights ----
    with tabs[4]:
        ai = load_json(f"{hub_key}/ai-insights.json")
        if not isinstance(ai, dict):
            empty_state("AI insights are unavailable for this hub.")
        else:
            type_counts = ai.get("type_counts")
            if isinstance(type_counts, dict) and type_counts:
                st.markdown(" · ".join(f"**{k}** ({v})" for k, v in type_counts.items()))
            insights = [i for i in safe_list(ai, "list") if isinstance(i, dict)]
            if not insights:
                empty_state("No AI insights available for this hub.")
            for insight in insights[:10]:
                priority = safe_get(insight, "priority", "Medium")
                icon = {"High": "🔴", "Medium": "🟡", "Low": "⚪"}.get(priority, "⚪")
                title = safe_get(insight, "title", "Untitled insight")
                itype = safe_get(insight, "insight_type", "Insight")
                with st.expander(f"{icon} [{itype}] {title}"):
                    st.write(safe_get(insight, "finding", "No finding recorded."))
                    st.caption(f"Evidence: {safe_get(insight, 'supporting_evidence', 'Not available.')}")
                    st.write(f"**Recommended action:** {safe_get(insight, 'recommended_action', 'Not available.')}")
                    cols = st.columns(4)
                    conf = safe_float(safe_get(insight, "confidence_score"))
                    cols[0].metric("Confidence", f"{conf*100:.0f}%" if conf is not None else "—")
                    cost = safe_get(insight, "estimated_cost_impact_usd")
                    if cost:
                        cols[1].metric("Cost impact", fmt_usd(cost))
                    co2 = safe_float(safe_get(insight, "estimated_co2e_impact_tonnes"))
                    if co2 is not None:
                        cols[2].metric("CO2e impact", f"{co2:.1f} t")
                    cols[3].metric("Status", safe_get(insight, "status", "—"))

    # ---- Scenarios ----
    with tabs[5]:
        scn = load_json(f"{hub_key}/scenarios.json")
        if not isinstance(scn, dict):
            empty_state("Scenario data is unavailable for this hub.")
        else:
            scenario_list = [s for s in safe_list(scn, "list") if isinstance(s, dict)]
            if not scenario_list:
                empty_state("No scenarios available for this hub.")
            for s in scenario_list:
                with st.container():
                    st.subheader(safe_get(s, "journey_name", "Untitled scenario"))
                    st.write(safe_get(s, "narrative", ""))
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Primary mode", safe_get(s, "primary_mode", "—"))
                    leg_ids = [l for l in safe_get(s, "leg_ids", []) or [] if l]
                    c2.metric("Legs", len(leg_ids) if leg_ids else "—")
                    total_co2e = safe_float(safe_get(s, "total_co2e_tonnes"))
                    c3.metric("Total emissions", f"{total_co2e:.2f} tCO2e" if total_co2e is not None else "—")
                    st.info(f"**Demonstrates:** {safe_get(s, 'demonstrates', 'Not documented.')}")
                    st.markdown("---")

    # ---- Digital Twin ----
    with tabs[6]:
        twin = load_json(f"{hub_key}/digital-twin.json")
        if not isinstance(twin, dict):
            empty_state("Digital twin data is unavailable for this hub.")
        else:
            edges = [e for e in safe_list(twin, "edges") if isinstance(e, dict)]
            total_edges = safe_get(twin, "total_edges_in_dataset", len(edges))
            st.caption(f"Sampled {len(edges)} of {fmt_num(total_edges)} total relationship edges.")
            if edges:
                relationships = [e.get("relationship") for e in edges if e.get("relationship")]
                if relationships:
                    rel_counts = pd.Series(relationships).value_counts()
                    fig = px.bar(x=rel_counts.index, y=rel_counts.values, template=CHART_TEMPLATE,
                                 labels={"x": "Relationship", "y": "Count"}, color=rel_counts.index,
                                 color_discrete_sequence=COLOR_SEQ)
                    fig.update_layout(height=320, showlegend=False, xaxis_tickangle=-30)
                    st.plotly_chart(fig, width="stretch")
                edf = safe_df(edges[:20])
                if not edf.empty:
                    st.dataframe(edf, width="stretch", hide_index=True)
            else:
                empty_state("No digital twin relationships available for this hub.")

    # ---- Audit Trail ----
    with tabs[7]:
        audit = load_json(f"{hub_key}/audit-trails.json")
        if not isinstance(audit, dict):
            empty_state("Audit trail data is unavailable for this hub.")
        else:
            chains = [c for c in safe_list(audit, "chains") if isinstance(c, dict)]
            if not chains:
                empty_state("No audit trail chains available for this hub.")
            else:
                st.caption("Supplier → Purchase Order → PO Line → Invoice → Shipment → Shipment Leg → Emission Event → AI Insight, sampled from fulfilled purchase orders.")
            for c in chains[:6]:
                po_id = safe_get(c, "po_id", "Unknown PO")
                supplier_name = safe_get(c, "supplier_name", "Unknown supplier")
                amount = safe_get(c, "amount_usd")
                with st.expander(f"{po_id} — {supplier_name} ({fmt_usd(amount)})"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        po_lines = [l for l in safe_get(c, "po_lines", []) or [] if isinstance(l, dict)]
                        st.markdown(f"**PO Lines ({len(po_lines)})**")
                        for l in po_lines:
                            st.write(f"- {safe_get(l, 'item_description', 'Item')} — {fmt_usd(safe_get(l, 'total_line_value_usd'))}")
                        invoices = [iv for iv in safe_get(c, "invoices", []) or [] if isinstance(iv, dict)]
                        st.markdown(f"**Invoices ({len(invoices)})**")
                        for iv in invoices:
                            st.write(f"- {safe_get(iv, 'invoice_id', 'Invoice')} — {fmt_usd(safe_get(iv, 'invoice_total_usd'))} ({safe_get(iv, 'payment_status', '—')})")
                    with col_b:
                        if safe_get(c, "has_shipment_link"):
                            st.success(f"Linked shipment: {safe_get(c, 'linked_shipment_id', '—')}")
                            legs = [l for l in safe_get(c, "shipment_legs", []) or [] if isinstance(l, dict)]
                            if safe_get(c, "has_leg_and_emission_data") and legs:
                                st.markdown(f"**Shipment legs ({len(legs)})**")
                                for leg in legs:
                                    co2e_kg = safe_get(leg, "co2e_kg", 0) or 0
                                    st.write(f"- {safe_get(leg, 'leg_id', '—')} · {safe_get(leg, 'mode', '—')} · {co2e_kg/1000:.2f} t CO2e")
                            else:
                                st.caption("No leg data available for this shipment.")
                        else:
                            st.caption("No shipment link (by design — not every PO generates a tracked shipment).")
                        insights = [a for a in safe_get(c, "matched_ai_insights", []) or [] if isinstance(a, dict)]
                        if safe_get(c, "has_ai_insight_link") and insights:
                            st.markdown("**Linked AI insights**")
                            for a in insights:
                                st.write(f"- {safe_get(a, 'insight_type', '—')}: {safe_get(a, 'title', '—')}")
                        else:
                            st.caption("No AI insight linked to this chain.")


# ----------------------------------------------------------------------
# Global Overview
# ----------------------------------------------------------------------
def render_global_overview():
    st.title("Maritime Scope 3 Intelligence")
    st.caption("Procurement, logistics and emissions visibility across global maritime hubs — a proposed strategic product concept.")
    demo_badge()

    summary = load_json("global/summary.json")
    comparison = load_json("global/hub-comparison.json")
    quality = load_json("global/data-quality.json")
    if not isinstance(summary, dict) or not isinstance(comparison, dict):
        st.error("Global summary data is unavailable.")
        return

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Combined Scope 3 Emissions", fmt_tonnes(safe_get(summary, "combined_co2e_tonnes")))
    kpi_card(c2, "Combined Procurement Spend", fmt_usd(safe_get(summary, "combined_procurement_spend_usd")))
    kpi_card(c3, "Active Suppliers", fmt_num(safe_get(summary, "combined_suppliers")))
    kpi_card(c4, "Shipments Monitored", fmt_num(safe_get(summary, "combined_shipments")))

    st.markdown("")
    hubs = [h for h in safe_list(comparison, "hubs") if isinstance(h, dict)]
    if not hubs:
        empty_state("No hub comparison data available.")
        return
    hub_names = [safe_get(h, "hub_name", "Hub") for h in hubs]

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure()
        fig.add_bar(name="Total Scope 3 (tCO2e)", x=hub_names, y=[safe_get(h, "total_co2e_tonnes", 0) for h in hubs], marker_color="#2F80ED")
        fig.add_bar(name="Maritime Procurement (tCO2e)", x=hub_names, y=[safe_get(h, "maritime_procurement_co2e_tonnes", 0) for h in hubs], marker_color="#e6c257")
        fig.update_layout(template=CHART_TEMPLATE, height=340, barmode="group", title="Scope 3 emissions by hub",
                           legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    with col_b:
        fig = px.bar(x=hub_names, y=[safe_get(h, "total_procurement_spend_usd", 0) for h in hubs], template=CHART_TEMPLATE,
                     labels={"x": "Hub", "y": "USD"}, color=hub_names, color_discrete_sequence=COLOR_SEQ,
                     title="Procurement spend by hub")
        fig.update_layout(height=340, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Hub comparison")
    compare_fields = [
        ("Scope 3 emissions", "total_co2e_tonnes", fmt_tonnes),
        ("Procurement spend", "total_procurement_spend_usd", fmt_usd),
        ("Active suppliers", "active_suppliers", fmt_num),
        ("High-risk suppliers", "high_risk_suppliers", fmt_num),
        ("Shipments monitored", "shipments_monitored", fmt_num),
        ("Shipment legs", "shipment_legs", fmt_num),
        ("Reduction opportunities", "reduction_opportunities_count", fmt_num),
        ("Open high-priority AI insights", "open_ai_insights_high_priority", fmt_num),
        ("Assurance coverage", "assurance_coverage_pct", fmt_pct),
        ("Procurement categories", "procurement_categories_count", fmt_num),
        ("Scope 3 categories", "scope3_categories_count", fmt_num),
    ]
    table = {"Metric": [f[0] for f in compare_fields]}
    for h in hubs:
        table[safe_get(h, "hub_name", "Hub")] = [f[2](safe_get(h, f[1])) for f in compare_fields]
    st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)

    if isinstance(quality, dict):
        sg_q, dx_q = quality.get("singapore") or {}, quality.get("dubai") or {}
        st.caption(
            f"Data quality — Singapore: {safe_get(sg_q, 'avg_data_quality_score', '—')} avg score, "
            f"{fmt_pct(safe_get(sg_q, 'assurance_coverage_pct'))} assured · "
            f"Dubai: {safe_get(dx_q, 'avg_data_quality_score', '—')} avg score, "
            f"{fmt_pct(safe_get(dx_q, 'assurance_coverage_pct'))} assured"
        )


# ----------------------------------------------------------------------
# Strategy pages
# ----------------------------------------------------------------------
def render_strategy_architecture():
    st.title("Strategy & Product Architecture")
    st.caption("Recommended strategic operating model — an academic consulting recommendation, not a statement of existing licenses or partnerships.")
    demo_badge()

    arch = load_json("strategy/architecture.json")
    if not isinstance(arch, dict):
        st.error("Strategy architecture data is unavailable.")
        return

    summary_text = safe_get(arch, "summary")
    if summary_text:
        st.info(f"**Report's central recommendation:** *{summary_text}*")

    col1, col2, col3 = st.columns(3)
    for col, key, icon in [(col1, "license_buy", "🔒"), (col2, "partner", "🤝"), (col3, "build", "🔨")]:
        block = arch.get(key) or {}
        with col:
            st.subheader(f"{icon} {safe_get(block, 'label', key.replace('_', ' ').title())}")
            items = safe_get(block, "items", []) or []
            for item in items:
                st.markdown(f"- {item}")
            st.caption(safe_get(block, "note", ""))

    st.markdown("### Implementation priorities")
    st.write(safe_get(arch, "implementation_priorities", "Not documented."))

    story = load_json("strategy/executive-story.json")
    if isinstance(story, dict):
        st.markdown("### Executive strategic response")
        st.markdown(f"**Problem:** {safe_get(story, 'problem', '—')}")
        st.markdown(f"**Opportunity:** {safe_get(story, 'opportunity', '—')}")
        st.markdown(f"**Strategic response:** {safe_get(story, 'strategic_response', '—')}")
        st.markdown(f"**Outcome:** {safe_get(story, 'outcome', '—')}")

    st.caption("Strategic recommendation only — no license, partnership, or integration currently exists.")


def render_differentiation():
    st.title("Competitive Differentiation")
    st.caption("Summarised in original language from the strategy report's positioning, feature comparison, and value proposition sections.")
    demo_badge()

    diff = load_json("strategy/differentiation.json")
    if not isinstance(diff, dict):
        st.error("Differentiation data is unavailable.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Competitive positioning")
        st.write(safe_get(diff, "positioning_summary", "Not documented."))
    with col2:
        st.subheader("Feature comparison takeaway")
        st.write(safe_get(diff, "feature_comparison_summary", "Not documented."))

    st.subheader("Customer value proposition")
    st.write(safe_get(diff, "customer_value_proposition", "Not documented."))

    st.subheader("Where this concept differentiates")
    points = safe_get(diff, "differentiation_points", []) or []
    if points:
        cols = st.columns(2)
        for i, point in enumerate(points):
            with cols[i % 2]:
                st.markdown(f"✅ {point}")
    else:
        empty_state("No differentiation points documented.")


def render_roadmap():
    st.title("Product Roadmap")
    st.caption("Phases 1–3 map directly to the strategy report's stated implementation priorities. Phase 4 is a clearly labelled inference.")
    demo_badge()

    roadmap = load_json("strategy/roadmap.json")
    if not isinstance(roadmap, dict):
        st.error("Roadmap data is unavailable.")
        return

    source = safe_get(roadmap, "source")
    if source:
        st.caption(f"Implementation basis: {source}. Content below is paraphrased for the demonstration interface.")

    phases = [p for p in safe_list(roadmap, "phases") if isinstance(p, dict)]
    if not phases:
        empty_state("No roadmap phases documented.")
        return

    for i, phase in enumerate(phases, start=1):
        st.subheader(f"{i}. {safe_get(phase, 'phase', f'Phase {i}')}")
        if safe_get(phase, "is_inference"):
            inferred_badge()
        items = safe_get(phase, "items", []) or []
        if items:
            st.markdown(" &nbsp; ".join(f"`{item}`" for item in items), unsafe_allow_html=True)
        st.caption(safe_get(phase, "note", ""))
        st.markdown("---")


# ----------------------------------------------------------------------
# Data & Methodology
# ----------------------------------------------------------------------
def render_methodology():
    st.title("Data & Methodology")
    st.caption("How every figure on this platform is sourced, calculated, and audited.")
    demo_badge()

    st.info(
        "This platform uses synthetic data created for academic analysis and product "
        "demonstration. It does not represent actual Marcura customers, suppliers, "
        "transactions, vessels, or emissions records. Strategy content reflects a proposed "
        "product concept, not an existing Marcura offering."
    )

    quality = load_json("global/data-quality.json")
    source_notes = load_json("strategy/source-notes.json")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Canonical emissions source")
        st.write(
            "Dashboard emissions figures were derived during offline preprocessing from each hub's "
            "designated `emissions_ledger`, as identified in the source dataset documentation. "
            "This deployment contains the resulting dashboard-ready aggregates rather than the raw ledger."
        )
        st.subheader("Calculation formula")
        st.code("total_co2e_kg = activity_value × factor_value\n(or) co2_kg + ch4_kg×27 + n2o_kg×273", language="text")
        st.caption("Every emission event carries a factor source, factor version, and validity dates for full reproducibility.")

    with col2:
        st.subheader("Assurance & data quality")
        if isinstance(quality, dict):
            sg_q, dx_q = quality.get("singapore") or {}, quality.get("dubai") or {}
            m1, m2 = st.columns(2)
            m1.metric("Singapore assurance coverage", fmt_pct(safe_get(sg_q, "assurance_coverage_pct")))
            m2.metric("Dubai assurance coverage", fmt_pct(safe_get(dx_q, "assurance_coverage_pct")))
        else:
            empty_state("Data quality figures are unavailable.")
        st.caption("Assurance status is one of Unassured / Self-Assured / Third-Party Reviewed, recorded per emission event. Every record also carries a 0–1 data-quality score.")

        st.subheader("Record classification")
        st.write(
            "Operational records carry a `record_status` of Historical, Current, Planned, or "
            "Forecast, distinguishing settled history from in-flight or projected records."
        )

    st.subheader("Known limitations")
    st.markdown(
        "- All company, supplier, vessel, and shipment data is synthetic and fictional.\n"
        "- The port map shows synthetic coordinates connected by straight illustrative lines where route "
        "data exists, or ports only where it does not — never real vessel geometry or live tracking.\n"
        "- Large tables are sampled for this dashboard; full totals were computed from the complete underlying tables before sampling.\n"
        "- Not every purchase order links to a tracked shipment — the audit trail shows this honestly rather than fabricating a connection.\n"
        "- This is an academic, product-demonstration platform, not a real deployment."
    )

    if isinstance(source_notes, dict):
        st.subheader("Strategy content source notes")
        st.write(safe_get(source_notes, "note", ""))
        sections = safe_get(source_notes, "sections_reviewed", []) or []
        if sections:
            st.caption("Sections reviewed: " + " · ".join(sections))


# ----------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------
if page == "Global Overview":
    render_global_overview()
elif page == "Singapore Hub":
    render_hub_page("singapore", "Singapore")
elif page == "Dubai Hub":
    render_hub_page("dubai", "Dubai")
elif page == "Strategy & Product Architecture":
    render_strategy_architecture()
elif page == "Competitive Differentiation":
    render_differentiation()
elif page == "Product Roadmap":
    render_roadmap()
elif page == "Data & Methodology":
    render_methodology()
