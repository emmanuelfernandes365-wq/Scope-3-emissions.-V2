# Maritime Scope 3 Intelligence — Streamlit Demonstration

A synthetic-data demonstration platform: procurement, logistics and
emissions visibility across two maritime hubs (Singapore and Dubai),
illustrating a maritime-specific Scope 3 intelligence product concept.

> **This is not an official Marcura product.** No license, partnership,
> or integration described on the Strategy pages currently exists.

> **Demonstration platform powered entirely by synthetic data.**
> Organizations, transactions, emissions, and operational events shown
> are fictional and created for academic and product-demonstration
> purposes.

## Repository structure

```
maritime-scope3-streamlit/
├── streamlit_app.py       single-file application (all pages + data loading)
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml        dark maritime theme
└── data/
    ├── global/             cross-hub summary, comparison, data-quality JSON
    ├── singapore/           Singapore hub JSON (already dashboard-ready)
    ├── dubai/                Dubai hub JSON (already dashboard-ready)
    └── strategy/             strategy-report-derived JSON (architecture,
                               differentiation, roadmap, source notes)
```

All JSON files under `data/` are pre-processed and dashboard-ready —
already aggregated, minified, and (for large tables) reduced to the
records the app actually displays. No preprocessing, ZIP extraction, or
document parsing happens when the app starts.

## Local installation & run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploying to Streamlit Community Cloud

1. Push this repository to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app.
3. Select this repository and set the main file path to `streamlit_app.py`.
4. Deploy — no secrets or environment variables are required.

## Data folders used

- `data/global/` — `summary.json`, `hub-comparison.json`,
  `data-quality.json` — used by the Global Overview page.
- `data/singapore/`, `data/dubai/` — `summary.json`, `emissions.json`,
  `suppliers.json`, `shipments.json`, `routes.json`, `ai-insights.json`,
  `scenarios.json`, `procurement.json`, `digital-twin.json`,
  `audit-trails.json` — used by the corresponding Hub page.
- `data/strategy/` — `architecture.json`, `differentiation.json`,
  `roadmap.json`, `executive-story.json`, `source-notes.json` — all used
  by the Strategy pages (`executive-story.json` powers the "Executive
  strategic response" section on the Strategy & Product Architecture page).

## Known limitations

- Large tables (shipments, suppliers, AI insights, digital-twin edges)
  are pre-reduced to a display-ready sample; full-dataset totals were
  computed before sampling and are shown accurately in the KPI cards.
- The Shipments & Map tab renders synthetic port locations, and — only
  where origin/destination coordinates exist in the data — straight-line
  "synthetic illustrative routes" between them. This is never real vessel
  geometry or live tracking; the on-screen label always matches what is
  actually plotted. Maps use Plotly's MapLibre-based `Scattermap` traces,
  which require no Mapbox API key or token.
- Not every purchase order in the audit trail links to a tracked
  shipment; this is shown honestly rather than fabricated.
- This is an academic, single-session demonstration — there is no
  backend, database, or write-back capability.
