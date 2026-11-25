# 🌱 Smart Farm Monitor

**ESP32 → ThingSpeak cloud → Python dashboard**

A small IoT project that keeps an eye on a garden bed. An ESP32 reads the soil moisture, temperature and humidity, switches a pump on when the soil gets dry, and sends everything to the ThingSpeak cloud every 20 seconds. A Python dashboard then pulls the data back down and shows it live.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![MicroPython](https://img.shields.io/badge/MicroPython-ESP32-2B2728?logo=micropython&logoColor=white)
![ThingSpeak](https://img.shields.io/badge/Cloud-ThingSpeak-0076A8)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)

🔗 **Live dashboard:** _add link_ · **Wokwi simulation:** _add link_ · **ThingSpeak channel:** _add link_

![Dashboard](docs/images/dashboard.png)

---

## How it works

```
 ESP32 + sensors (Wokwi)  ──Wi-Fi──►  ThingSpeak (cloud)  ──internet──►  Dashboard (Streamlit)
   reads + runs the pump               stores the readings                cards, charts, CSV
```

1. **The ESP32** reads its sensors every 20 seconds.
2. **It decides about watering by itself:** the pump turns on when the soil drops below **30%** and keeps going until it's back up to **40%**, so it runs steadily instead of flicking on and off. This keeps working even if the internet drops.
3. **ThingSpeak** stores every reading in the cloud.
4. **The dashboard** fetches the latest readings, tidies them up with pandas, and shows live cards, charts, a short summary and a CSV download.

Wokwi's sensors sit still unless you move them, so the code adds small, natural changes (a tenth of a degree here, a little drying there) to make the data behave like a real field. One setting, `NATURAL_CHANGES = False`, switches this off for a real board.

## The circuit

| Part | ESP32 pin | Job |
|---|---|---|
| DHT22 | GPIO 15 | Temperature and humidity |
| Potentiometer (knob) | GPIO 34 | Stands in for the soil moisture sensor |
| Blue LED + 220 Ω resistor | GPIO 26 | Stands in for the pump |

![Circuit](docs/images/wokwi-circuit.png)

## What's in the folder

| File | What it is |
|---|---|
| `wokwi/diagram.json` | The circuit |
| `wokwi/main.py` | The ESP32 code (MicroPython) |
| `dashboard/app.py` | The dashboard |
| `dashboard/send_test_data.py` | Sends 5 test readings, so you can check everything before using Wokwi |
| `Start Dashboard.bat` | Double-click to open the dashboard on Windows |
| `.env.example` | Template for your private keys |

---

## Run it yourself

**1. ThingSpeak:** make a free channel at [thingspeak.mathworks.com](https://thingspeak.mathworks.com) with 4 fields: `Temperature`, `Humidity`, `Soil moisture`, `Pump`. Note your **Channel ID**, **Write API Key** and **Read API Key**.

**2. Your keys:** copy `.env.example` to `.env` and fill it in. This file stays on your computer and never goes to GitHub.

**3. The dashboard:** double-click **`Start Dashboard.bat`**. Or from a terminal:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

**4. The ESP32:** on [wokwi.com](https://wokwi.com), start a **New Project → ESP32 → MicroPython**. Paste in `diagram.json` and `main.py`, add your Write API Key, and press ▶ **Play**. A new reading appears on the dashboard every 20 seconds.

Want to check the cloud side first? Run `python dashboard/send_test_data.py`.

## If something's not working

| What you see | Try this |
|---|---|
| `ThingSpeak didn't accept that one` | Copy the Write API Key again, with no spaces |
| Dashboard says `400 Bad Request` | Add your Read API Key to `.env`, or make the channel public |
| Wokwi stuck on `Connecting to Wi-Fi...` | Your network or antivirus is blocking Wokwi. Try another browser or a phone hotspot |
| `ModuleNotFoundError` | Use `Start Dashboard.bat`, or activate `.venv` first |

## What I'd add next

- Real hardware: a capacitive soil sensor, relay and water pump
- Skip watering when rain is on the way
- Phone alerts when the soil gets too dry

---

Built by **Kavish Sharma** · [GitHub](https://github.com/KavishSharma10) · [LinkedIn](https://www.linkedin.com/in/kavish-sharma-29361b210/) · MIT License
