from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = "super-secret-key-1234"  # เปลี่ยนเป็น key ของคุณเอง

DB_NAME = "tracker.db"

# -------------------------
# Database setup
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    # locations table
    c.execute('''CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_name TEXT,
        ip_address TEXT,
        lat REAL,
        lon REAL,
        address TEXT,
        timestamp TEXT
    )''')

    # default admin user
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  ("admin", generate_password_hash("1234")))

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("map_page"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("map_page"))
        else:
            return "❌ Invalid login", 401

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/map")
def map_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("map-boot.html")

# -------------------------
# API
# -------------------------
@app.route("/update", methods=["POST"])
def update():
    """รับข้อมูลจาก ESP / simulate"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "no data"}), 400

    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        return jsonify({"status": "error", "msg": "invalid lat/lon"}), 400

    device_name = data.get("device_name", "ESP-Sim")
    ip_address = data.get("ip_address", "127.0.0.1")

    # -------------------------
    # Reverse Geocoding (Nominatim)
    # -------------------------
    address = "Unknown"
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2"},
            headers={"User-Agent": "GPS-Tracker-App"}
        )
        if resp.status_code == 200:
            data_osm = resp.json()
            address = data_osm.get("display_name", "Unknown")
    except Exception as e:
        print("Reverse geocoding error:", e)

    timestamp = datetime.utcnow().isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO locations (device_name, ip_address, lat, lon, address, timestamp) VALUES (?,?,?,?,?,?)",
        (device_name, ip_address, lat, lon, address, timestamp)
    )
    conn.commit()
    conn.close()

    print(f"[UPDATE] {device_name} @ {lat},{lon} - {address}")
    return jsonify({"status": "success", "data": {
        "device_name": device_name,
        "ip_address": ip_address,
        "lat": lat,
        "lon": lon,
        "address": address,
        "timestamp": timestamp
    }})

@app.route("/latest")
def latest():
    """คืนค่าพิกัดล่าสุด"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM locations ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"status": "empty"})

@app.route("/history")
def history():
    """คืนค่าพิกัดย้อนหลัง (10 รายการล่าสุด)"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM locations ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/status")
def status():
    """ตรวจสอบ device connected หรือ offline"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM locations ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if row:
        last_ts = datetime.fromisoformat(row["timestamp"])
        now = datetime.utcnow()
        connected = (now - last_ts) < timedelta(seconds=90)  # <= 90 วินาที

        return jsonify({
            "connected": connected,
            "device": {
                "name": row["device_name"],
                "ip": row["ip_address"],
                "lat": row["lat"],
                "lon": row["lon"],
                "address": row["address"],
                "timestamp": row["timestamp"]
            }
        })
    else:
        return jsonify({"connected": False, "device": None})

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
