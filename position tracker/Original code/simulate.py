import requests
import time
import random

URL = "http://127.0.0.1:5000/update"

path = [
    (13.7563, 100.5018),  # Bangkok
    (13.75, 100.52),
    (13.74, 100.53),
    (13.73, 100.54),
    (13.72, 100.55),
]

while True:
    lat, lon = random.choice(path)
    data = {
        "device_name": "ESP32-GPS",
        "latitude": lat,
        "longitude": lon,
        
    }
    try:
        r = requests.post(URL, json=data)
        print("Sent:", data, "Response:", r.json())
    except Exception as e:
        print("Error:", e)

    time.sleep(10)
