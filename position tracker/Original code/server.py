from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import time
from datetime import datetime
import requests 

app = Flask(__name__)
app.secret_key = "supersecretkey"  # ต้อง fix ไว้ ไม่งั้น session จะ reset ทุกครั้ง

DB_NAME = "tracker.db"

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_name TEXT,
        latitude REAL,
        longitude REAL,
        address TEXT,
        timestamp INTEGER
    )
    """)
    conn.commit()
    conn.close()

def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "gps-tracker-demo/1.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("display_name", "Unknown location")
    except Exception as e:
        print("Reverse geocode error:", e)
    return "Unknown location"

# ---------- Routes ----------
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("map_view"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session["username"] = username
            return redirect(url_for("map_view"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/map")
def map_view():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("map.html")

@app.route("/update", methods=["POST"])
def update():
    data = request.json
    device_name = data.get("device_name", "ESP32-GPS")
    lat = data.get("latitude")
    lon = data.get("longitude")

    # 🟢 บังคับใช้ reverse geocode ทุกครั้ง
    address = reverse_geocode(lat, lon)

    timestamp = int(time.time())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO locations (device_name, latitude, longitude, address, timestamp) VALUES (?, ?, ?, ?, ?)",
              (device_name, lat, lon, address, timestamp))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "address": address})


@app.route("/latest")
def latest():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM locations ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({
            "device_name": row[1],
            "latitude": row[2],
            "longitude": row[3],
            "address": row[4],
            "timestamp": row[5]
        })
    return jsonify({"status": "no_data"})

@app.route("/history")
def history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM locations ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    history_data = [
        {
            "device_name": r[1],
            "latitude": r[2],
            "longitude": r[3],
            "address": r[4],
            "timestamp": r[5]
        } for r in rows
    ]
    return jsonify(history_data)

@app.route("/status")
def status():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp FROM locations ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "offline"})

    last_seen = row[0]
    now = int(time.time())
    if now - last_seen < 30:  # ภายใน 30 วิ ถือว่าออนไลน์
        return jsonify({"status": "online"})
    else:
        return jsonify({"status": "offline"})

if __name__ == "__main__":
    init_db()
    # user default สำหรับทดสอบ
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("admin", "1234"))
    conn.commit()
    conn.close()

    app.run(debug=True)
