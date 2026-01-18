import requests, time, random

URL = "http://127.0.0.1:5001/update"

# พิกัดจำลอง (กทม.)
points = [
    {"lat": 13.7563, "lon": 100.5018},  # พระบรมมหาราชวัง
    {"lat": 13.7589, "lon": 100.5070},  # เสาชิงช้า
    {"lat": 13.7620, "lon": 100.5350},  # สยาม
    {"lat": 13.7465, "lon": 100.5328},  # อโศก
    {"lat": 13.7393, "lon": 100.5470},  # พร้อมพงษ์
    {"lat": 13.7226, "lon": 100.5850},  # บางนา
    {"lat": 13.7271, "lon": 100.4930},  # สะพานพระราม 8
    {"lat": 13.7563, "lon": 100.5018},  # กลับมาพระบรมมหาราชวัง
]

while True:
    point = random.choice(points)
    point["device_name"] = "ESP-Sim"
    point["ip_address"] = "172.0.0.1"
  #  point["timestamp"] = "11:30:01"

    try:
        r = requests.post(URL, json=point)
        print("Sent:", point, "| Response:", r.json())
    except Exception as e:
        print("Error:", e)

    time.sleep(5)  # ส่งทุก 30 วินาที
