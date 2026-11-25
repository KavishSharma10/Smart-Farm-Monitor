# Smart Farm Dashboard
#
# This pulls the latest readings our ESP32 sent to ThingSpeak and shows them
# as live cards and charts. It refreshes by itself every 20 seconds.
#
# Run it with:   streamlit run dashboard/app.py

import pandas as pd
import requests
import streamlit as st


# ---------- Settings you can change ----------

CHANNEL_ID = "3593878"   # the number shown on your ThingSpeak channel page
READ_API_KEY = ""                           # only needed if your channel is private
DRY_SOIL_LEVEL = 30                         # same number as in the ESP32 code
TIMEZONE = "Australia/Adelaide"


# ---------- Getting the data ----------

def get_readings(how_many=200):
    """Ask ThingSpeak for the latest readings and tidy them into a table."""
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    settings = {"results": how_many}
    if READ_API_KEY:
        settings["api_key"] = READ_API_KEY

    reply = requests.get(url, params=settings, timeout=10)
    reply.raise_for_status()
    readings = pd.DataFrame(reply.json()["feeds"])

    if readings.empty:
        return readings

    # Give the ThingSpeak fields friendly names
    readings = readings.rename(columns={
        "field1": "Temperature (°C)",
        "field2": "Humidity (%)",
        "field3": "Soil moisture (%)",
        "field4": "Pump",
    })

    # Turn the text into proper numbers and times
    for column in ["Temperature (°C)", "Humidity (%)", "Soil moisture (%)", "Pump"]:
        readings[column] = pd.to_numeric(readings[column], errors="coerce")
    readings["Time"] = pd.to_datetime(readings["created_at"]).dt.tz_convert(TIMEZONE)

    return readings


# ---------- The page ----------

st.set_page_config(page_title="Smart Farm Monitor", page_icon="🌱", layout="wide")
st.title("🌱 Smart Farm Monitor")
st.caption("ESP32 sensors → ThingSpeak cloud → this dashboard")


@st.fragment(run_every="20s")          # re-runs just this part every 20 seconds
def show_dashboard():
    try:
        readings = get_readings()
    except Exception as error:
        st.error(f"Couldn't get data from ThingSpeak: {error}")
        return

    if readings.empty:
        st.info("No readings yet - start the ESP32 in Wokwi and wait about 20 seconds.")
        return

    latest = readings.iloc[-1]
    previous = readings.iloc[-2] if len(readings) > 1 else latest

    # Big number cards along the top, each showing the change since the last reading
    card1, card2, card3, card4 = st.columns(4)
    card1.metric("Temperature", f"{latest['Temperature (°C)']:.1f} °C",
                 f"{latest['Temperature (°C)'] - previous['Temperature (°C)']:+.1f}")
    card2.metric("Humidity", f"{latest['Humidity (%)']:.0f} %",
                 f"{latest['Humidity (%)'] - previous['Humidity (%)']:+.0f}")
    card3.metric("Soil moisture", f"{latest['Soil moisture (%)']:.0f} %",
                 f"{latest['Soil moisture (%)'] - previous['Soil moisture (%)']:+.0f}")
    card4.metric("Pump", "ON 💧" if latest["Pump"] == 1 else "Off")

    # A friendly warning when the soil is dry
    if latest["Soil moisture (%)"] < DRY_SOIL_LEVEL:
        st.warning(f"Soil is dry ({latest['Soil moisture (%)']:.0f}%) - the pump has been switched on.")
    else:
        st.success("Soil moisture is healthy.")

    # Charts over time
    chart_data = readings.set_index("Time")
    left, right = st.columns(2)
    with left:
        st.subheader("Soil moisture")
        st.line_chart(chart_data["Soil moisture (%)"])
    with right:
        st.subheader("Temperature and humidity")
        st.line_chart(chart_data[["Temperature (°C)", "Humidity (%)"]])

    # A few simple facts about the data we have
    st.subheader("Summary")
    pump_minutes = readings["Pump"].sum() * 20 / 60          # each reading covers about 20 seconds
    st.write(
        f"**{len(readings)}** readings since {readings['Time'].iloc[0]:%d %b %H:%M}. "
        f"Average soil moisture **{readings['Soil moisture (%)'].mean():.0f}%**, "
        f"highest temperature **{readings['Temperature (°C)'].max():.1f} °C**, "
        f"pump ran for about **{pump_minutes:.0f} minutes**."
    )

    # The raw numbers, newest first, plus a download button
    st.subheader("Latest readings")
    table = readings[["Time", "Temperature (°C)", "Humidity (%)", "Soil moisture (%)", "Pump"]]
    st.dataframe(table.iloc[::-1].head(15), hide_index=True, use_container_width=True)
    st.download_button("Download all readings (CSV)", table.to_csv(index=False), "farm_readings.csv")

    st.caption(f"Last updated {latest['Time']:%H:%M:%S} · refreshes every 20 seconds")


show_dashboard()
