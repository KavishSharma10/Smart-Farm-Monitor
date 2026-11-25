# Test sender - pretends to be the ESP32.
#
# Use this to check your ThingSpeak channel and the dashboard work BEFORE
# you set up Wokwi. It sends 5 made-up readings, 16 seconds apart.
#
# Run it with:   python dashboard/send_test_data.py

import random
import time

import requests

THINGSPEAK_WRITE_KEY = "BCNWK8DXLPNSDDDH"   # same key as in the ESP32 code

for number in range(1, 6):
    # Make up some believable farm readings
    temperature = round(random.uniform(18, 32), 1)
    humidity = round(random.uniform(30, 70))
    soil = random.randint(15, 60)
    pump_on = 1 if soil < 30 else 0

    reply = requests.get("https://api.thingspeak.com/update", params={
        "api_key": THINGSPEAK_WRITE_KEY,
        "field1": temperature,
        "field2": humidity,
        "field3": soil,
        "field4": pump_on,
    }, timeout=10)

    if reply.text == "0":
        print(f"Reading {number}: ThingSpeak said no - check the Write API Key.")
    else:
        print(f"Reading {number}: saved as entry #{reply.text} "
              f"(temp {temperature} °C, humidity {humidity}%, soil {soil}%, pump {pump_on})")

    if number < 5:
        time.sleep(16)   # the free plan only accepts one update every 15 seconds

print("Done! Open your ThingSpeak channel or the dashboard to see the readings.")
