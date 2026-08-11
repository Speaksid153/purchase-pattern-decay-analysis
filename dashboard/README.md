# Dashboard support modules

This directory is not an operator-facing Streamlit dashboard. The supported interface is
the React application in `src/`, served by `scripts/api_server.py`.

The Python modules here remain because the API reuses their validated artifact loading,
feature-label, and charting helpers. `dashboard/app.py` intentionally shows a retirement
notice to prevent a second, stale dashboard from presenting incompatible model metrics.
