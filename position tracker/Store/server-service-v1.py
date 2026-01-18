from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = "super-secret-key-1234"
DB_NAME = "tracker.db"

GEOCODE_TTL_SECONDS = 600  # 10 นาที
geocode_cache = {}

# -------------------------
# Database setup
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # users table with role
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )''')

    # devices table
    c.execute('''CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        device_name TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # locations table
    c.execute('''CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        device_name TEXT,
        latitude REAL,
        longitude REAL,
        address TEXT,
        timestamp TEXT,
        FOREIGN KEY(device_id) REFERENCES devices(id)
    )''')

    # default admin
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    admin = c.fetchone()
    if not admin:
        hashed_pw = generate_password_hash("1234")
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", hashed_pw, "admin"))
        admin_id = c.lastrowid
        c.execute("INSERT INTO devices (user_id, device_name) VALUES (?, ?)",
                  (admin_id, "ESP-Sim"))
    else:
        admin_id = admin[0]
        c.execute("SELECT * FROM devices WHERE user_id=?", (admin_id,))
        if not c.fetchone():
            c.execute("INSERT INTO devices (user_id, device_name) VALUES (?, ?)",
                      (admin_id, "ESP-Sim"))

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------
# Helper for admin
# -------------------------
def require_admin():
    if "user_id" not in session:
        return False, "Login required"
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    if not user or user["role"] != "admin":
        return False, "Access denied: Admins only"
    return True, user

# -------------------------
# Admin routes
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    # ถ้า user login แล้วและเป็น admin
    if "user_id" in session and session.get("role") == "admin":
        # แสดง admin dashboard
        return render_template("admin.html")

    # ถ้าเป็น POST (form login)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("admin.html", error="กรุณากรอก username และ password")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            if user["role"] != "admin":
                return render_template("admin.html", error="คุณไม่ใช่ admin")
            # set session
            session["user_id"] = user["id"]
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin.html", error="Username หรือ Password ไม่ถูกต้อง")

    # ถ้า GET และยังไม่ได้ login แสดง form login
    return render_template("admin.html")

@app.route("/admin/data")
def admin_data():
    ok, user_or_msg = require_admin()
    if not ok:
        return jsonify({"status":"error","msg":user_or_msg}), 403

    conn = get_db()
    users = [dict(u) for u in conn.execute("SELECT id, username, role FROM users").fetchall()]
    devices = [dict(d) for d in conn.execute(
        "SELECT d.id, d.device_name, d.user_id, u.username AS owner FROM devices d LEFT JOIN users u ON d.user_id = u.id"
    ).fetchall()]
    conn.close()
    return jsonify({"status":"ok", "users":users, "devices":devices})

@app.route("/admin/check_login", methods=["POST"])
def admin_check_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "msg": "Username/Password required"})

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user["password"], password):
        if user["role"] == "admin":
            session["user_id"] = user["id"]
            session["role"] = "admin"
            return jsonify({"status": "ok"})
        else:
            return jsonify({"status": "error", "msg": "User is not admin"})
    return jsonify({"status": "error", "msg": "Invalid username or password"})

@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    ok, msg = require_admin()
    if not ok:
        return jsonify({"status": "error", "msg": msg}), 403

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "msg": "Missing username/password"}), 400

    hashed = generate_password_hash(password)
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "msg": "Username already exists"}), 400
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/admin/add_device", methods=["POST"])
def admin_add_device():
    ok, msg = require_admin()
    if not ok:
        return jsonify({"status": "error", "msg": msg}), 403

    data = request.get_json()
    device_name = data.get("device_name")
    user_id = data.get("user_id")
    if not device_name or not user_id:
        return jsonify({"status": "error", "msg": "Missing device name or user"}), 400

    conn = get_db()
    try:
        conn.execute("INSERT INTO devices (user_id, device_name) VALUES (?, ?)", (user_id, device_name))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "msg": "Device already exists"}), 400
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/admin/delete_user/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    ok, msg = require_admin()
    if not ok:
        return jsonify({"status": "error", "msg": msg}), 403

    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/admin/delete_device/<int:device_id>", methods=["DELETE"])
def admin_delete_device(device_id):
    ok, msg = require_admin()
    if not ok:
        return jsonify({"status": "error", "msg": msg}), 403

    conn = get_db()
    conn.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})



# -------------------------
# User login/logout and map
# -------------------------
@app.route("/")
def index():
    if "user_id" in session and "device_name" in session:
        return redirect(url_for("map_page"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        device_name = request.form["device_name"]

        conn = get_db()
        try:
            user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if user and check_password_hash(user["password"], password):
                device = conn.execute(
                    "SELECT * FROM devices WHERE user_id=? AND device_name=?",
                    (user["id"], device_name)
                ).fetchone()
                if device:
                    session["user_id"] = user["id"]
                    session["device_name"] = device_name
                    return redirect(url_for("map_page"))
                else:
                    return "❌ Invalid device for this user", 401
            else:
                return "❌ Invalid login", 401
        finally:
            conn.close()
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/map")
def map_page():
    if "user_id" not in session or "device_name" not in session:
        return redirect(url_for("login"))
    return render_template("map-boot.html")

# -------------------------
# Update & API
# -------------------------
@app.route("/update", methods=["POST"])
def update():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "no data"}), 400

    device_name = data.get("device_name", "ESP-Sim")
    latitude = data.get("lat")
    longitude = data.get("lon")
    if latitude is None or longitude is None:
        return jsonify({"status": "error", "msg": "invalid lat/lon"}), 400

    # reverse geocoding with TTL cache
    key = (round(latitude,4), round(longitude,4))
    now = datetime.utcnow()
    if key in geocode_cache:
        address, expire = geocode_cache[key]
        if now > expire:
            del geocode_cache[key]
            address = None
    else:
        address = None

    if not address:
        address = "Unknown"
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": latitude, "lon": longitude, "format": "jsonv2"},
                headers={"User-Agent": "GPS-Tracker-App"},
                timeout=5
            )
            if resp.status_code == 200:
                data_osm = resp.json()
                address = data_osm.get("display_name", "Unknown")
        except Exception as e:
            print("Reverse geocoding error:", e)
        geocode_cache[key] = (address, now + timedelta(seconds=GEOCODE_TTL_SECONDS))

    timestamp = datetime.utcnow().isoformat()

    conn = get_db()
    device_row = conn.execute("SELECT id FROM devices WHERE device_name=?", (device_name,)).fetchone()
    if not device_row:
        conn.close()
        return jsonify({"status": "error", "msg": "device not found"}), 404
    device_id = device_row["id"]

    conn.execute(
        "INSERT INTO locations (device_id, device_name, latitude, longitude, address, timestamp) VALUES (?,?,?,?,?,?)",
        (device_id, device_name, latitude, longitude, address, timestamp)
    )
    conn.commit()
    conn.close()

    print(f"[UPDATE] {device_name} @ {latitude},{longitude} - {address}")
    return jsonify({"status": "success", "data": {"device_name": device_name,"latitude": latitude,"longitude": longitude,"address": address,"timestamp": timestamp}})

@app.route("/latest")
def latest():
    device_name = session.get("device_name")
    if not device_name:
        return jsonify({"status": "error", "msg": "no device in session"}), 403
    conn = get_db()
    row = conn.execute("SELECT * FROM locations WHERE device_name=? ORDER BY id DESC LIMIT 1",(device_name,)).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"status": "empty"})

@app.route("/history")
def history():
    device_name = session.get("device_name")
    if not device_name:
        return jsonify({"status": "ok", "history": {}})

    conn = get_db()
    rows = conn.execute(
        "SELECT latitude, longitude FROM locations WHERE device_name=? ORDER BY id DESC LIMIT 10",
        (device_name,)
    ).fetchall()
    conn.close()

    history_data = {
        device_name: [{"lat": r["latitude"], "lon": r["longitude"]} for r in rows]
    }
    return jsonify({"status": "ok", "history": history_data})

@app.route("/check_geocoding")
def check_geocoding():
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": 13.7563, "lon": 100.5018, "format": "jsonv2"},
            headers={"User-Agent": "GPS-Tracker-App"},
            timeout=5
        )
        if resp.status_code == 200:
            return jsonify({"status": "ok"})
    except Exception as e:
        print("[WARN] Geocoding check failed:", e)
    return jsonify({"status": "down"})

@app.route("/status")
def status():
    device_name = session.get("device_name")
    if not device_name:
        return jsonify({"status": "offline", "devices": []})

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM locations WHERE device_name=? ORDER BY id DESC LIMIT 1",
        (device_name,)
    ).fetchone()
    conn.close()

    if row:
        return jsonify({
            "status": "online",
            "device": {
                "device_name": row["device_name"],
                "lat": row["latitude"],
                "lon": row["longitude"],
                "address": row["address"],
                "timestamp": row["timestamp"]
            }
        })
    else:
        return jsonify({"status": "offline", "devices": []})


    if row:
        last_ts = datetime.fromisoformat(row["timestamp"])
        connected = (datetime.utcnow() - last_ts) < timedelta(seconds=90)

        device_data = {
            "device_name": row["device_name"],
            "lat": row["latitude"],
            "lon": row["longitude"],
            "address": row["address"],
            "timestamp": row["timestamp"],
            "owner": "N/A"  # optional, จะไป join users table ก็ได้
        }
        return jsonify({"status": "ok", "devices": [device_data]})
    else:
        return jsonify({"status": "ok", "devices": []})

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
