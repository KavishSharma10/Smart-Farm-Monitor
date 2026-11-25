# Smart Farm Monitor - ESP32 code (MicroPython)
#
# What this does:
#   1. Connects to Wi-Fi.
#   2. Every 20 seconds it checks the soil moisture, temperature and humidity.
#   3. If the soil is too dry, it switches the "pump" light on (like starting irrigation).
#   4. Sends all the readings to ThingSpeak so we can see them online and in our dashboard.

import time
import random
import network
import urequests
import dht
from machine import Pin, ADC


# ---------- Settings you can change ----------

WIFI_NAME = "Wokwi-GUEST"        # Wokwi gives us this free pretend Wi-Fi network
WIFI_PASSWORD = ""               # no password

THINGSPEAK_WRITE_KEY = "PASTE_YOUR_WRITE_API_KEY_HERE"   # from ThingSpeak API Key

DRY_SOIL_LEVEL = 30              # below 30% moisture, the plants need water
WET_SOIL_LEVEL = 40              # once watering starts, keep going until the soil reaches this (%)
SEND_EVERY_SECONDS = 20          

# Natural changes - Wokwi's sensors sit still, so these make the readings behave like a real field.
# Set NATURAL_CHANGES to False on a real ESP32 and it will report the sensors exactly as they are.
NATURAL_CHANGES = True
TEMP_STEP = 0.08                 # most the temperature can move between two readings (°C)
HUMIDITY_STEP = 0.25             # most the humidity can move between two readings (%)
HUMIDITY_PER_DEGREE = 1.5        # air gets about this much drier (%) for every 1 °C warmer
SETTLE = 0.03                    # how strongly readings drift back towards what the sensor says
SOIL_DRYING = 0.15               # how much the soil dries out between readings when the pump is off (%)
SOIL_WATERING = 0.6              # how much one round of pumping wets the soil (%)
KNOB_MOVED = 5                   # if the soil knob moves more than this (%), follow the knob


# ---------- Setting up the parts on the board ----------

temp_sensor = dht.DHT22(Pin(15))          # DHT22 sensor on pin 15 (temperature + humidity)

soil_sensor = ADC(Pin(34))                # the soil sensor (a knob in Wokwi) on pin 34
soil_sensor.atten(ADC.ATTN_11DB)          # lets this pin read the full 0-3.3 V range

pump_light = Pin(26, Pin.OUT)             # LED on pin 26, it lights up when the pump runs


# ---------- Small helper functions ----------

def connect_to_wifi():
    """Join the Wi-Fi network, waiting until we're connected."""
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(WIFI_NAME, WIFI_PASSWORD)

    print("Connecting to Wi-Fi", end="")
    while not wifi.isconnected():
        print(".", end="")
        time.sleep(0.5)
    print("\nConnected! My IP address is", wifi.ifconfig()[0])


def read_soil_moisture():
    """Turn the soil sensor's raw number (0 to 4095) into a percentage (0 to 100)."""
    raw_value = soil_sensor.read()
    return round(raw_value / 4095 * 100)


def drift(current, sensor_value, biggest_step):
    """Nudge a reading by a small random step, gently pulled back towards what the sensor says."""
    random_step = random.uniform(-biggest_step, biggest_step)
    pull_back = (sensor_value - current) * SETTLE
    return current + random_step + pull_back


def keep_between_0_and_100(value):
    """Percentages can't go below 0 or above 100."""
    return max(0, min(100, value))


def send_to_thingspeak(temperature, humidity, soil, pump_on):
    """Send one set of readings to ThingSpeak. Each reading goes into its own field."""
    url = (
        "http://api.thingspeak.com/update"
        "?api_key=" + THINGSPEAK_WRITE_KEY
        + "&field1=" + str(temperature)
        + "&field2=" + str(humidity)
        + "&field3=" + str(soil)
        + "&field4=" + str(pump_on)
    )
    response = urequests.get(url)
    entry_number = response.text
    response.close()

    # ThingSpeak replies with the entry number it saved, or "0" if it said no
    if entry_number == "0":
        print("ThingSpeak didn't accept that one - check your Write API Key.")
    else:
        print("Saved on ThingSpeak as entry #" + entry_number)


# ---------- The main program ----------

connect_to_wifi()

# The "living" values we keep between rounds. They start from the real sensors on the first reading.
field_temp = None
field_humidity = None
field_soil = None
last_knob = None
pump_on = 0                      # the pump starts off

while True:
    # Take the readings
    temp_sensor.measure()
    temperature = temp_sensor.temperature()
    humidity = temp_sensor.humidity()
    soil = read_soil_moisture()

    if NATURAL_CHANGES:
        # First time round, start exactly where the sensors are
        if field_temp is None:
            field_temp, field_humidity, field_soil, last_knob = temperature, humidity, soil, soil

        # If someone turned the soil knob, jump to the new value
        if abs(soil - last_knob) > KNOB_MOVED:
            field_soil = soil
        last_knob = soil

        # Temperature wanders a little; humidity leans the opposite way (warmer air feels drier)
        field_temp = drift(field_temp, temperature, TEMP_STEP)
        humidity_target = humidity - (field_temp - temperature) * HUMIDITY_PER_DEGREE
        field_humidity = keep_between_0_and_100(drift(field_humidity, humidity_target, HUMIDITY_STEP))

        temperature = round(field_temp, 1)
        humidity = round(field_humidity, 1)
        soil = round(field_soil, 1)

    # Decide if the plants need water
    # Start below the dry level, stop once the soil is properly wet, and in between keep doing
    # whatever we were doing - so the pump runs steadily instead of flicking on and off.
    if soil < DRY_SOIL_LEVEL:
        pump_on = 1
    elif soil >= WET_SOIL_LEVEL:
        pump_on = 0
    pump_light.value(pump_on)

    if NATURAL_CHANGES:
        # Sun and plants slowly dry the soil; when the pump runs, the soil soaks up water
        if pump_on:
            field_soil += SOIL_WATERING * random.uniform(0.8, 1.2)
        else:
            field_soil -= SOIL_DRYING * random.uniform(0.5, 1.5)
        field_soil = keep_between_0_and_100(field_soil)

    print("Temp:", temperature, "C | Humidity:", humidity, "% | Soil:", soil, "% | Pump:", "ON" if pump_on else "off")

    # Send to the cloud. If the internet hiccups, we just try again next round.
    try:
        send_to_thingspeak(temperature, humidity, soil, pump_on)
    except Exception as error:
        print("Couldn't reach ThingSpeak this time:", error)

    time.sleep(SEND_EVERY_SECONDS)