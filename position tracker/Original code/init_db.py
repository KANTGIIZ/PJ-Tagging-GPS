import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "tracker.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # -------------------------
    # users table
    # -------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)

    # -------------------------
    # devices table
    # -------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        device_name TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # -------------------------
    # locations table
    # -------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        device_name TEXT,
        ip_address TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(device_id) REFERENCES devices(id)
    )
    """)

    # -------------------------
    # default admin user
    # -------------------------
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    admin = c.fetchone()
    if not admin:
        hashed_pw = generate_password_hash("1234")
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", hashed_pw, "admin"))
        admin_id = c.lastrowid
        # add default device for admin
        c.execute("INSERT INTO devices (user_id, device_name) VALUES (?, ?)",
                  (admin_id, "ESP-Sim"))
    else:
        admin_id = admin[0]
        # ensure at least one device exists for admin
        c.execute("SELECT * FROM devices WHERE user_id=?", (admin_id,))
        if not c.fetchone():
            c.execute("INSERT INTO devices (user_id, device_name) VALUES (?, ?)",
                      (admin_id, "ESP-Sim"))

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_db()
