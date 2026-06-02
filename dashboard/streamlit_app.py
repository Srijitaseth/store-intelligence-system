import time
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
STORE_ID = "STORE_BLR_002"

st.set_page_config(page_title="Store Intelligence Dashboard", layout="wide")

st.title("Store Intelligence Dashboard")

placeholder = st.empty()

while True:
    try:
        metrics = requests.get(f"{API_URL}/stores/{STORE_ID}/metrics", timeout=5).json()
        funnel = requests.get(f"{API_URL}/stores/{STORE_ID}/funnel", timeout=5).json()
        heatmap = requests.get(f"{API_URL}/stores/{STORE_ID}/heatmap", timeout=5).json()
        anomalies = requests.get(f"{API_URL}/stores/{STORE_ID}/anomalies", timeout=5).json()
        health = requests.get(f"{API_URL}/health", timeout=5).json()

        with placeholder.container():
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Unique Visitors", metrics["unique_visitors"])
            col2.metric("Converted Visitors", metrics["converted_visitors"])
            col3.metric("Conversion Rate", f'{metrics["conversion_rate"] * 100:.2f}%')
            col4.metric("Queue Depth", metrics["current_queue_depth"])

            st.subheader("Average Dwell Per Zone")
            st.json(metrics["avg_dwell_per_zone_ms"])

            st.subheader("Funnel")
            st.json(funnel)

            st.subheader("Heatmap")
            st.json(heatmap)

            st.subheader("Anomalies")
            st.json(anomalies)

            st.subheader("Health")
            st.json(health)

    except Exception as error:
        st.error(f"Dashboard error: {error}")

    time.sleep(5)