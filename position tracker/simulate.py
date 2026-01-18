import requests, time, random

URL = "https://projectmyluggie.pythonanywhere.com/update"
DEVICE_NAME = "Device-01-Luggie"
IP_ADDRESS = "192.168.1.100"

points = [
    (7.8804, 98.3923),
    (7.8894, 98.3980),
    (7.8926, 98.2966),
    (7.8341, 98.3006),
    (7.8086, 98.2969),
    (7.9519, 98.3381),
    (8.0177, 98.3339),
    (7.7466, 98.3723),
    (7.8877, 98.2856),
    (7.9846, 98.3611),
]

print("📡 Phuket fixed-point simulator started")

while True:
    lat, lon = random.choice(points)
    sat = random.randint(5, 12)

    data = {
        "device_name": DEVICE_NAME,
        "ip_address": IP_ADDRESS,
        "lat": lat,
        "lon": lon,
        "satellites": sat
    }

    try:
        r = requests.post(URL, json=data, timeout=10)
        print("Sent:", data, "| Status:", r.status_code)
    except Exception as e:
        print("❌ Error:", e)

    time.sleep(10)
