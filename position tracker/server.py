from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = "b7f8e2c8d76a4b7e8e91d"  # ✅ เปลี่ยนเป็น key ของคุณเอง

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
        satellites INTEGER DEFAULT 0,
        timestamp TEXT
    )''')
    # default user
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
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "no data"}), 400

    lat = float(data.get("lat", 0))
    lon = float(data.get("lon", 0))
    device_name = data.get("device_name", "ESP-Sim")
    ip_address = data.get("ip_address", request.remote_addr)
    satellites = int(data.get("satellites", 0))  # ⭐ ดึงจำนวนดาวเทียม

    # reverse geocode
    address = "Unknown"
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2"},
            headers={"User-Agent": "GPS-Tracker-App"}
        )
        if resp.status_code == 200:
            data_osm = resp.json()
            address = data_osm.get("display_name") or data_osm.get("name") or "Unknown"
    except Exception as e:
        print("Reverse geocoding error:", e)

    timestamp = datetime.utcnow().isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO locations (device_name, ip_address, lat, lon, address, satellites, timestamp) VALUES (?,?,?,?,?,?,?)",
        (device_name, ip_address, lat, lon, address, satellites, timestamp)
    )
    conn.commit()
    conn.close()

    print(f"[UPDATE] {device_name} @ {lat},{lon} - {address} (🛰 {satellites})")
    return jsonify({"status": "success"})


@app.route("/latest")
def latest():
    conn = get_db()
    row = conn.execute("SELECT * FROM locations ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"status": "empty"})


@app.route("/history")
def history():
    """คืนค่าพิกัดย้อนหลัง (10 รายการล่าสุด)"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM locations ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/status")
def status():
    """ตรวจสอบสถานะ Device"""
    conn = get_db()
    row = conn.execute("SELECT timestamp, device_name FROM locations ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return jsonify({"connected": False})
    last_time = datetime.fromisoformat(row["timestamp"])
    now = datetime.utcnow()
    delta = now - last_time
    connected = delta < timedelta(seconds=15)
    return jsonify({
        "connected": connected,
        "device": {"name": row["device_name"], "last_seen": row["timestamp"]}
    })

@app.route("/clear_logs", methods=["POST"])
def clear_logs():
    if "user_id" not in session:
        return jsonify({"status": "error", "msg": "unauthorized"}), 401

    conn = get_db()
    conn.execute("DELETE FROM locations")
    conn.commit()
    conn.close()

    print("🧹 Cleared all tracker logs")
    return jsonify({"status": "success", "msg": "logs cleared"})

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

        # ตรวจสอบรหัสเก่า
        if not check_password_hash(user["password"], old_password):
            conn.close()
            return render_template("change_password.html", error="❌ รหัสผ่านเดิมไม่ถูกต้อง")

        # ตรวจสอบว่ารหัสใหม่ตรงกัน
        if new_password != confirm_password:
            conn.close()
            return render_template("change_password.html", error="❌ รหัสผ่านใหม่ไม่ตรงกัน")

        # อัปเดตรหัสผ่านใหม่
        hashed = generate_password_hash(new_password)
        conn.execute("UPDATE users SET password=? WHERE id=?", (hashed, session["user_id"]))
        conn.commit()
        conn.close()

        return render_template("change_password.html", success="✅ เปลี่ยนรหัสผ่านเรียบร้อยแล้ว!")

    return render_template("change_password.html")


# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
