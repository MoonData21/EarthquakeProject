import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
from datetime import datetime

# -------------------------------
# 1. Streamlit Page Setup
# -------------------------------
st.set_page_config(page_title="USGS Earthquake Dashboard", layout="wide")
st.title("🌎 Real-Time Earthquake Dashboard")

st.markdown(
    """
This dashboard visualizes recent global earthquake activity using **USGS real-time data**.  

> **Note:** All earthquake times are displayed in **UTC**,  
> and all depths are in **kilometers (km)**.
"""
)

# -------------------------------
# 2. Sidebar Controls
# -------------------------------
st.sidebar.header("⚙️ Controls")

# Timeframe selection
timeframe = st.sidebar.selectbox(
    "Select timeframe:",
    ["Past Hour", "Past Day", "Past 7 Days", "Past 30 Days"]
)

timeframe_urls = {
    "Past Hour": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "Past Day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "Past 7 Days": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "Past 30 Days": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson",
}

url = timeframe_urls[timeframe]

# -------------------------------
# 3. Fetch Data from USGS API
# -------------------------------
@st.cache_data(ttl=600)
def load_data(url):
    """Fetch and process earthquake data."""
    try:
        response = requests.get(url)
        data = response.json()
        features = data["features"]

        df = pd.json_normalize(features)
        df = df[[
            "properties.place",
            "properties.mag",
            "properties.time",
            "geometry.coordinates"
        ]]
        df.columns = ["place", "mag", "time", "coordinates"]

        # Split coordinates into lon, lat, depth
        df["lon"] = df["coordinates"].apply(lambda x: x[0])
        df["lat"] = df["coordinates"].apply(lambda x: x[1])
        df["depth"] = df["coordinates"].apply(lambda x: x[2])

        # Convert time from ms since epoch to readable UTC datetime
        df["date"] = pd.to_datetime(df["time"], unit="ms")

        # Filter invalid magnitudes
        df = df[df["mag"].notnull()]
        df = df[df["mag"] > 0]

        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

df = load_data(url)

# -------------------------------
# 4. Magnitude Filter
# -------------------------------
if not df.empty:
    min_mag = float(df["mag"].min())
    max_mag = float(df["mag"].max())

    mag_filter = st.sidebar.slider(
        "Minimum magnitude:",
        min_value=round(min_mag, 1),
        max_value=round(max_mag, 1),
        value=2.5,
        step=0.1,
    )

    df = df[df["mag"] >= mag_filter]
    st.sidebar.write(f"Showing earthquakes with magnitude ≥ {mag_filter}")
    st.sidebar.write(f"🧾 Total earthquakes: {len(df)}")

# -------------------------------
# 5. Display Table of Recent Earthquakes
# -------------------------------
if not df.empty:
    st.write("### Recent Earthquakes")
    st.dataframe(
        df[["date", "place", "mag", "depth"]]
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
        .head(20)
    )

# -------------------------------
# 6. Pydeck Map (3D Column Layer)
# -------------------------------
if not df.empty:
    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["lon", "lat"],
        get_elevation="mag * 10000",  # exaggerate for visual clarity
        elevation_scale=100,
        radius=20000,
        get_fill_color="[255, 140, 0, 160]",  # orange
        pickable=True,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        latitude=df["lat"].mean(),
        longitude=df["lon"].mean(),
        zoom=1.5,
        pitch=45,
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_provider="osm",
        map_style=None,  # disables Mapbox styles
        tooltip={
            "html": "<b>{place}</b><br/>"
                    "Magnitude: {mag}<br/>"
                    "Depth: {depth} km<br/>"
                    "Date (UTC): {date}",
            "style": {"backgroundColor": "steelblue", "color": "white"}
        },
    )

    st.pydeck_chart(r)
else:
    st.warning("No earthquake data found for the selected timeframe or magnitude range.")

# -------------------------------
# 7. Footer / Data Source Note
# -------------------------------
st.markdown(
    """
---
**Data source:** USGS Earthquake Hazards Program  
**Libraries used:** Streamlit, Pydeck, Pandas, Requests
"""
)