import streamlit as st
import pandas as pd
import plotly.graph_objects as go

@st.cache_data
def load_data():
    predictions = pd.read_csv('data/processed/instacart/predictions/baseline_model_predictions_full.csv')
    shap_values = pd.read_csv('data/processed/instacart/shap/xgboost_baseline_shap_values_full.csv')
    orders_clean = pd.read_csv('orders_clean.csv')
    return predictions, shap_values, orders_clean

def get_intervention_tag(top_driver):
    mapping = {
        'base_avg_days_between_orders': 'Re-engagement reminder — gap has grown beyond their normal rhythm',
        'base_avg_reorder_ratio_to_date': 'Bundle / cart-building incentive — declining habitual repurchase',
        'base_avg_basket_size_to_date': 'Cross-sell offer — shrinking basket size',
        'base_user_tenure_days': 'Monitor — tenure-related risk, lower urgency',
        'base_total_orders_to_date': 'Monitor — order frequency pattern shift',
        'base_order_dow': 'No action — timing pattern, low signal',
        'base_order_hour': 'No action — timing pattern, low signal',
    }
    return mapping.get(top_driver, 'Monitor')

def render(customer_id):
    predictions, shap_values, orders_clean = load_data()

    customer_preds = predictions[predictions['user_id'] == customer_id].sort_values('order_id')
    customer_shap = shap_values[shap_values['user_id'] == customer_id]
    customer_orders = orders_clean[orders_clean['user_id'] == customer_id].sort_values('order_number')

    if customer_preds.empty:
        st.warning(f"Customer {customer_id} does not have enough order history (minimum 3 orders required) to generate a risk prediction.")
        return
    if customer_orders.empty:
        st.warning(f"No order history found for customer {customer_id}")
        return

    st.header(f"Customer {customer_id} — Risk Detail")

    latest_risk = float(customer_preds['risk_score_xgboost'].iloc[-1])
    st.metric("Current Risk Score (XGBoost)", f"{latest_risk:.2%}")

    st.subheader("Risk Trend")
    fig_risk = go.Figure(go.Scatter(
        x=list(range(len(customer_preds))),
        y=customer_preds['risk_score_xgboost'].astype(float),
        mode='lines+markers',
        name='Risk score'
    ))
    fig_risk.update_layout(xaxis_title="Snapshot", yaxis_title="Risk Score", height=300)
    st.plotly_chart(fig_risk, use_container_width=True)

    st.subheader("Purchase History")
    fig_timeline = go.Figure(go.Scatter(
        x=customer_orders['order_number'],
        y=customer_orders['days_since_prior_order'],
        mode='lines+markers',
        name='Days since prior order'
    ))
    fig_timeline.update_layout(xaxis_title="Order Number", yaxis_title="Days Since Prior Order", height=350)
    st.plotly_chart(fig_timeline, use_container_width=True)

    st.subheader("Top Risk Drivers")
    if not customer_shap.empty:
        latest_shap = customer_shap.iloc[-1]
        shap_cols = [c for c in customer_shap.columns if c.startswith('shap_')]
        driver_values = latest_shap[shap_cols].sort_values(ascending=False).head(5)
        readable_names = {c: c.replace('shap_base_', '').replace('_', ' ').title() for c in shap_cols}

        fig_shap = go.Figure(go.Bar(
            x=driver_values.values,
            y=[readable_names[c] for c in driver_values.index],
            orientation='h'
        ))
        fig_shap.update_layout(xaxis_title="Impact on Risk Score", height=300)
        st.plotly_chart(fig_shap, use_container_width=True)

        top_driver = latest_shap['top_risk_driver']
        st.subheader("Recommended Action")
        st.info(get_intervention_tag(top_driver))
    else:
        st.warning("No SHAP data found for this customer")

if __name__ == "__main__":
    render(customer_id=13)

