"""Retired Streamlit entry point.

The supported dashboard is the React application served with scripts/api_server.py.
The remaining modules in this directory provide artifact-loading and analysis helpers for
the API; they are not a second operator interface.
"""

import streamlit as st


st.set_page_config(page_title="Early Churn Predictor", layout="wide")
st.error("This Streamlit dashboard is retired.")
st.info("Start `py scripts/api_server.py` and `npm run dev`, then open http://127.0.0.1:5173.")
