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

CHANNEL_ID = "3593878"                      # the number shown on your ThingSpeak channel page
READ_API_KEY = ""                           # only needed if your channel is private
DRY_SOIL_LEVEL = 30                         # same number as in the ESP32 code
TIMEZONE = "Australia/Adelaide"
CHART_HEIGHT = 200                          # how tall each little chart is (pixels)


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
        "field1": "Temperature (C)",
        "field2": "Humidity (%)",
        "field3": "Soil moisture (%)",
        "field4": "Pump",
    })

    # Turn the text into proper numbers and times
    for column in ["Temperature (C)", "Humidity (%)", "Soil moisture (%)", "Pump"]:
        readings[column] = pd.to_numeric(readings[column], errors="coerce")
    readings["Time"] = pd.to_datetime(readings["created_at"]).dt.tz_convert(TIMEZONE)

    return readings


# ---------- One card per reading ----------

def reading_card(title, column, unit, decimals, readings):
    """A boxed card for one reading: the value now, the change, its own chart and a quick summary."""
    latest = readings[column].iloc[-1]
    previous = readings[column].iloc[-2] if len(readings) > 1 else latest

    with st.container(border=True):
        st.subheader(title)
        st.metric("Right now", f"{latest:.{decimals}f} {unit}",
                  f"{latest - previous:+.{decimals}f} {unit} since last reading")
        st.line_chart(readings.set_index("Time")[column], height=CHART_HEIGHT)
        st.caption(
            f"Lowest {readings[column].min():.{decimals}f} {unit} | "
            f"Average {readings[column].mean():.{decimals}f} {unit} | "
            f"Highest {readings[column].max():.{decimals}f} {unit}"
        )


def pump_card(readings):
    """The pump gets its own card too: is it on, when did it run, and for how long."""
    pump_now = readings["Pump"].iloc[-1] == 1

    # How long the pump ran: add up the gap after every reading where the pump was on
    gaps = readings["Time"].diff().shift(-1).dt.total_seconds()
    gaps = gaps.fillna(gaps.median() if gaps.notna().any() else 0)
    pump_minutes = (gaps * readings["Pump"]).sum() / 60

    # Count how many times it switched on (an off to on change)
    times_started = int(((readings["Pump"] == 1) & (readings["Pump"].shift(1, fill_value=0) == 0)).sum())

    with st.container(border=True):
        st.subheader("Pump")
        st.metric("Right now", "ON - watering" if pump_now else "Off")
        st.area_chart(readings.set_index("Time")["Pump"], height=CHART_HEIGHT)
        st.caption(f"Switched on {times_started} times | ran for about {pump_minutes:.0f} minutes in total")


# ---------- The page ----------

st.set_page_config(page_title="Smart Farm Monitor", layout="wide")
st.title("Smart Farm Monitor")
st.caption("ESP32 sensors > ThingSpeak cloud > this dashboard")


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

    # A friendly status line - says what the soil and the pump are actually doing right now
    soil_now = readings["Soil moisture (%)"].iloc[-1]
    if readings["Pump"].iloc[-1] == 1:
        st.info(f"Watering now - soil is at {soil_now:.1f}% and the pump is running.")
    elif soil_now < DRY_SOIL_LEVEL:
        st.warning(f"Soil is dry ({soil_now:.1f}%) - the pump should switch on with the next reading.")
    else:
        st.success(f"Soil moisture is healthy ({soil_now:.1f}%).")

    # Four cards, two per row - one for each reading
    top_left, top_right = st.columns(2)
    with top_left:
        reading_card("Temperature", "Temperature (C)", "C", 1, readings)
    with top_right:
        reading_card("Humidity", "Humidity (%)", "%", 1, readings)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        reading_card("Soil moisture", "Soil moisture (%)", "%", 1, readings)
    with bottom_right:
        pump_card(readings)

    # The raw numbers, newest first, plus a download button
    st.subheader("Latest readings")
    table = readings[["Time", "Temperature (C)", "Humidity (%)", "Soil moisture (%)", "Pump"]]
    st.dataframe(table.iloc[::-1].head(15), hide_index=True, use_container_width=True)
    st.download_button("Download all readings (CSV)", table.to_csv(index=False), "farm_readings.csv")

    st.caption(f"{len(readings)} readings since {readings['Time'].iloc[0]:%d %b %H:%M} | "
               f"last one at {readings['Time'].iloc[-1]:%H:%M:%S} | refreshes every 20 seconds")


show_dashboard()