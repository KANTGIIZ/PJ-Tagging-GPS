from flask import Flask, request, jsonify, render_template
from datetime import datetime
import requests

app = Flask(__name__)

latest_location = {}
history = []

# ---- helper function: reverse geocode ----
def reverse_geocode(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1
        }
        headers = {"User-Agent": "ESP32-GPS-Tracker-Demo"}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("display_name", "Unknown location")
    except Exception as e:
        print("Reverse geocode error:", e)
    return "Unknown location"


@app.route('/')
def index():
    return render_template("map-boot.html")


@app.route('/update', methods=['POST'])
def update():
    global latest_location, history
    data = request.get_json()
    if not data or "lat" not in data or "lon" not in data:
        return jsonify({"status": "error", "msg": "invalid data"}), 400

    lat = data["lat"]
    lon = data["lon"]
    timestamp = datetime.utcnow().isoformat()
    address = reverse_geocode(lat, lon)

    latest_location = {
        "lat": lat,
        "lon": lon,
        "timestamp": timestamp,
        "address": address
    }
    history.append(latest_location)

    print("Updated:", latest_location)
    return jsonify({"status": "success", "data": latest_location})


@app.route('/latest')
def get_latest():
    return jsonify(latest_location if latest_location else {})


@app.route('/history')
def get_history():
    return jsonify(history)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)

