
"""ProbeNet dashboard powered by FastAPI and Streamlit."""

import os

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "PROBENET_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="ProbeNet | Network Observability",
    page_icon="🌐",
    layout="wide",
)

st.title("🌐 ProbeNet")
st.caption("Real-time network observability using RIPE Atlas")

st.markdown(
    "Explore latency, packet loss, and network measurements "
    "collected from distributed RIPE Atlas probes."
)


# ---------------------------------------------------------
# API communication
# ---------------------------------------------------------


def fetch_data(endpoint: str):
    """Fetch JSON data from the ProbeNet API."""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()

    except requests.RequestException as exc:
        st.error(f"Unable to retrieve data from the API: {exc}")
        st.info(
            "Ensure PostgreSQL and FastAPI are running. "
            f"API address: {API_BASE_URL}"
        )
        st.stop()


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:
    st.header("Dashboard Controls")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

    st.divider()

    st.caption(f"API: {API_BASE_URL}")
    st.caption(
        "Charts reflect stored observations. "
        "They are not automatically live."
    )


# ---------------------------------------------------------
# Measurement selection
# ---------------------------------------------------------

measurements = fetch_data("/measurements")

if not measurements:
    st.warning("No measurement metadata found in PostgreSQL.")
    st.stop()

measurement_lookup = {
    item["measurement_id"]: item
    for item in measurements
}

measurement_id = st.selectbox(
    "Select a RIPE Atlas measurement",
    options=list(measurement_lookup),
    format_func=lambda mid: (
        f"{mid} — {measurement_lookup[mid]['target']}"
    ),
)

selected = measurement_lookup[measurement_id]

st.caption(
    f"Target: {selected['target']} | "
    f"Type: {selected['measurement_type']} | "
    f"Status: {selected['status']}"
)


# ---------------------------------------------------------
# Data freshness and collection continuity
# ---------------------------------------------------------

monitoring = fetch_data(
    f"/measurements/{measurement_id}/monitoring"
)

st.subheader("Data Collection Health")

freshness = monitoring["freshness_status"]
continuity = monitoring["continuity_status"]

freshness_labels = {
    "fresh": "Fresh",
    "delayed": "Delayed",
    "stale": "Stale",
    "no_data": "No data",
    "clock_skew": "Clock skew",
}

health_col1, health_col2, health_col3 = st.columns(3)

age_seconds = monitoring["age_seconds"]

with health_col1:
    st.metric(
        "Data Freshness",
        freshness_labels.get(freshness, freshness),
    )

    if age_seconds is not None and age_seconds >= 0:
        st.caption(
            f"Last observation received "
            f"{age_seconds / 60:.1f} minutes ago"
        )

with health_col2:
    st.metric(
        "Observations (Last Hour)",
        f"{monitoring['recent_observation_count']:,}",
    )

with health_col3:
    st.metric(
        "Collection Continuity",
        f"{monitoring['continuity_percent']:.1f}%",
    )

    st.caption(
        f"{monitoring['active_five_minute_buckets']} of "
        f"{monitoring['total_five_minute_buckets']} "
        "recent five-minute intervals contain observations"
    )

if freshness == "stale":
    st.error(
        "Data is stale. ProbeNet has not received a new "
        "stored observation for over 15 minutes."
    )
elif freshness == "delayed":
    st.warning(
        "Data collection appears delayed. The latest "
        "stored observation is over 5 minutes old."
    )
elif freshness == "no_data":
    st.warning(
        "No observations have been stored for this measurement."
    )
elif freshness == "clock_skew":
    st.warning(
        "Stored receipt timestamps appear to be in the future. "
        "Check the collector and database clocks."
    )

if continuity == "no_recent_data":
    st.warning(
        "No observations were received in the recent "
        "five-minute monitoring buckets."
    )
elif continuity == "intermittent":
    st.warning(
        "Recent collection appears intermittent. Fewer "
        "than half of the monitoring buckets contain data."
    )

st.caption(
    "Collection continuity is a five-minute bucket activity "
    "indicator, not a measure of participating probe coverage. "
    "Refresh the dashboard to recalculate these values."
)

st.divider()


# ---------------------------------------------------------
# Fetch analytics and recent observations
# ---------------------------------------------------------

hourly = fetch_data(
    f"/measurements/{measurement_id}/hourly?limit=168"
)

pings = fetch_data(
    f"/measurements/{measurement_id}/pings?limit=100"
)


# ---------------------------------------------------------
# Analytics
# ---------------------------------------------------------

st.subheader("Network Performance Overview")

if not hourly:
    st.warning(
        "No stored ping observations exist for this measurement."
    )
    st.stop()

hourly_df = pd.DataFrame(hourly)

hourly_df["hour_utc"] = pd.to_datetime(
    hourly_df["hour_utc"],
    utc=True,
)

hourly_df = hourly_df.sort_values("hour_utc")

# Aggregate across the returned stored hourly buckets.
total_observations = int(
    hourly_df["observation_count"].sum()
)

total_sent = int(
    hourly_df["total_packets_sent"].sum()
)

total_lost = int(
    hourly_df["total_packets_lost"].sum()
)

total_with_rtt = int(
    hourly_df["observations_with_rtt"].sum()
)

# Weight hourly mean RTT by the number of observations
# contributing a valid RTT to each hourly mean.
rtt_values = hourly_df["average_rtt_ms"].fillna(0)

if total_with_rtt > 0:
    average_rtt = (
        rtt_values
        * hourly_df["observations_with_rtt"]
    ).sum() / total_with_rtt
else:
    average_rtt = None

packet_loss_percent = (
    (total_lost / total_sent) * 100
    if total_sent > 0
    else None
)

latest_event_hour = hourly_df["hour_utc"].max()

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Average RTT",
    f"{average_rtt:.2f} ms"
    if average_rtt is not None
    else "N/A",
)

col2.metric(
    "Packet Loss",
    f"{packet_loss_percent:.2f}%"
    if packet_loss_percent is not None
    else "N/A",
)

col3.metric(
    "Observations",
    f"{total_observations:,}",
)

col4.metric(
    "RTT Samples",
    f"{total_with_rtt:,}",
)

st.caption(
    "Summary metrics aggregate the returned stored hourly "
    "buckets, not necessarily a continuous seven-day window. "
    "RTT is an observation-weighted average of rounded hourly "
    "means."
)

st.caption(
    "Latest stored event hour (UTC): "
    f"{latest_event_hour.strftime('%Y-%m-%d %H:%M')}"
)


# ---------------------------------------------------------
# Latency and packet loss charts
# ---------------------------------------------------------

st.divider()
st.subheader("Hourly Network Trends")

latency_tab, loss_tab = st.tabs(
    ["Latency", "Packet Loss"]
)

with latency_tab:
    st.line_chart(
        hourly_df.set_index("hour_utc")[
            ["average_rtt_ms"]
        ],
        y_label="Average RTT (ms)",
        x_label="Hour (UTC)",
    )

    st.caption(
        "Hours without valid RTT measurements appear "
        "without an RTT value."
    )

with loss_tab:
    loss_chart = hourly_df.copy()

    loss_chart["packet_loss_percent"] = (
        loss_chart["packet_loss_ratio"] * 100
    )

    st.line_chart(
        loss_chart.set_index("hour_utc")[
            ["packet_loss_percent"]
        ],
        y_label="Packet Loss (%)",
        x_label="Hour (UTC)",
    )


# ---------------------------------------------------------
# Hourly analytics table
# ---------------------------------------------------------

st.divider()
st.subheader("Hourly Measurement Details")

display_hourly = hourly_df[
    [
        "hour_utc",
        "observation_count",
        "observations_with_rtt",
        "unique_probes",
        "total_packets_sent",
        "total_packets_lost",
        "average_rtt_ms",
        "packet_loss_ratio",
    ]
].copy()

display_hourly["packet_loss_percent"] = (
    display_hourly["packet_loss_ratio"] * 100
)

display_hourly = display_hourly.drop(
    columns=["packet_loss_ratio"]
)

st.dataframe(
    display_hourly.sort_values(
        "hour_utc",
        ascending=False,
    ),
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# Recent observations
# ---------------------------------------------------------

st.divider()
st.subheader("Recent Ping Observations")

if pings:
    pings_df = pd.DataFrame(pings)

    pings_df["event_time"] = pd.to_datetime(
        pings_df["event_time"],
        utc=True,
    )

    pings_df["received_at"] = pd.to_datetime(
        pings_df["received_at"],
        utc=True,
    )

    st.dataframe(
        pings_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Showing up to 100 recent stored observations "
        f"for measurement {measurement_id}."
    )

else:
    st.info("No recent observations found.")


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()
st.caption(
    "ProbeNet | RIPE Atlas Network Observability "
    "| Data Engineering Project"
)
