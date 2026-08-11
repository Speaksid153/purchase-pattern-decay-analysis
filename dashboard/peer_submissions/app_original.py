import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(__file__))

import screen2_customer_detail

st.set_page_config(page_title="Churn Risk Dashboard", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Risk Table", "Customer Detail", "Model Comparison"])

if page == "Risk Table":
    st.title("Risk Table")
    st.info("Screen 1 — not yet integrated")
    # screen1_risk_table.render()  

elif page == "Customer Detail":
    customer_id = st.sidebar.number_input("Customer ID", min_value=1, value=13, step=1)
    screen2_customer_detail.render(int(customer_id))

elif page == "Model Comparison":
    st.title("Model Comparison")
    st.info("Screen 3  — not yet integrated")
    # screen3_comparison.render()  
    
def render(customer_id):
    predictions, shap_values, orders_clean = load_data()

    # TEMPORARY DEBUG - remove after fixing
    st.write("DEBUG: total prediction rows loaded:", len(predictions))
    st.write("DEBUG: does user_id 1 exist in predictions?", (predictions['user_id'] == 1).any())
    st.write("DEBUG: customer_id received:", customer_id, type(customer_id))

    customer_preds = predictions[predictions['user_id'] == customer_id].sort_values('order_id')
    ...