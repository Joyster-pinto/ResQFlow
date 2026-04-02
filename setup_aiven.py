"""
ResQFlow — One-shot Aiven setup script.
Creates all tables and seeds all stations, vehicles, and user accounts.
Run once: python setup_aiven.py
"""
import mysql.connector

AIVEN = {
    "host":               "mysql-6d28c4a-joysterpinto2006-e0e1.e.aivencloud.com",
    "user":               "avnadmin",
    "password":           "AVNS_7fy1STtHEisONfFxDs_",
    "database":           "defaultdb",
    "port":               16149,
    "ssl_disabled":       False,
    "connection_timeout": 15,
}

# ── STATIONS (34 real Mysuru locations) ───────────────────────────────────────
STATIONS = [
    ("K.R. Hospital (Government)",          "HOSPITAL",       12.3050, 76.6551, 4),
    ("Cheluvamba Hospital",                  "HOSPITAL",       12.3101, 76.6452, 3),
    ("Columbia Asia Hospital Mysore",        "HOSPITAL",       12.3338, 76.6140, 3),
    ("JSS Hospital",                         "HOSPITAL",       12.3008, 76.5945, 4),
    ("Manipal Hospital Mysore",              "HOSPITAL",       12.3272, 76.6468, 3),
    ("Apollo BGS Hospital",                  "HOSPITAL",       12.2931, 76.6196, 3),
    ("Basappa Memorial Hospital",            "HOSPITAL",       12.3131, 76.6591, 2),
    ("Vikram Hospital",                      "HOSPITAL",       12.3044, 76.6611, 2),
    ("Government Ayurvedic Hospital",        "HOSPITAL",       12.3068, 76.6534, 2),
    ("District Hospital Nanjangud Road",     "HOSPITAL",       12.2749, 76.6450, 3),
    ("Vani Vilas Women & Children Hospital", "HOSPITAL",       12.3052, 76.6548, 2),
    ("Narayana Multispeciality Hospital",    "HOSPITAL",       12.3396, 76.6078, 3),
    ("Mysuru Central Fire Station",          "FIRE_STATION",   12.3076, 76.6556, 4),
    ("Vijayanagar Fire Station",             "FIRE_STATION",   12.3323, 76.6063, 3),
    ("Kuvempunagar Fire Station",            "FIRE_STATION",   12.3238, 76.6462, 3),
    ("Bannimantap Fire Station",             "FIRE_STATION",   12.3181, 76.6285, 3),
    ("Hebbal Fire Station",                  "FIRE_STATION",   12.3552, 76.6224, 2),
    ("Hootagalli Fire Station",              "FIRE_STATION",   12.2900, 76.5890, 2),
    ("Nanjangud Road Fire Post",             "FIRE_STATION",   12.2660, 76.6380, 2),
    ("Mysuru City Police Headquarters",      "POLICE_STATION", 12.3062, 76.6553, 5),
    ("Devaraja Police Station",              "POLICE_STATION", 12.3042, 76.6571, 4),
    ("Lakshmipuram Police Station",          "POLICE_STATION", 12.3173, 76.6485, 3),
    ("Kuvempunagar Police Station",          "POLICE_STATION", 12.3249, 76.6449, 3),
    ("Nazarbad Police Station",              "POLICE_STATION", 12.3093, 76.6390, 3),
    ("Jayalakshmipuram Police Station",      "POLICE_STATION", 12.3214, 76.6350, 3),
    ("Vijayanagar Police Station",           "POLICE_STATION", 12.3318, 76.6074, 3),
    ("Hebbal Police Station",                "POLICE_STATION", 12.3582, 76.6231, 3),
    ("Bannimantap Police Station",           "POLICE_STATION", 12.3178, 76.6258, 3),
    ("Bogadi Police Station",                "POLICE_STATION", 12.2931, 76.6086, 3),
    ("Metagalli Police Station",             "POLICE_STATION", 12.3411, 76.5890, 2),
    ("V.V. Mohalla Police Station",          "POLICE_STATION", 12.2986, 76.6567, 3),
    ("Krishnamurthypuram Police Station",    "POLICE_STATION", 12.3135, 76.6596, 3),
    ("Mandi Mohalla Police Station",         "POLICE_STATION", 12.3073, 76.6652, 3),
    ("Saraswathipuram Police Station",       "POLICE_STATION", 12.3268, 76.6579, 3),
]

VEHICLE_TYPES  = {"HOSPITAL": "AMBULANCE", "FIRE_STATION": "FIRE_ENGINE", "POLICE_STATION": "PATROL_CAR"}
VEHICLE_PREFIX = {"HOSPITAL": "KA21A",     "FIRE_STATION": "KA21F",       "POLICE_STATION": "KA21P"}

def run():
    print("Connecting to Aiven MySQL...")
    conn = mysql.connector.connect(**AIVEN)
    cur  = conn.cursor()
    print("Connected OK.\n")

    # ── CREATE TABLES ────────────────────────────────────────────────────────
    print("Creating tables...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            station_id         INT AUTO_INCREMENT PRIMARY KEY,
            name               VARCHAR(100) NOT NULL,
            type               ENUM('HOSPITAL','FIRE_STATION','POLICE_STATION') NOT NULL,
            latitude           DECIMAL(10,7) NOT NULL,
            longitude          DECIMAL(10,7) NOT NULL,
            vehicles_available INT DEFAULT 0,
            status             VARCHAR(20) DEFAULT 'AVAILABLE'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id        INT AUTO_INCREMENT PRIMARY KEY,
            vehicle_plate     VARCHAR(20) NOT NULL,
            type              ENUM('AMBULANCE','FIRE_ENGINE','PATROL_CAR') NOT NULL,
            station_id        INT,
            status            VARCHAR(30) DEFAULT 'AVAILABLE',
            last_service_date DATE,
            FOREIGN KEY (station_id) REFERENCES stations(station_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INT AUTO_INCREMENT PRIMARY KEY,
            username   VARCHAR(50) NOT NULL UNIQUE,
            password   VARCHAR(100) NOT NULL,
            role       ENUM('DISPATCHER','DRIVER','MONITOR') NOT NULL,
            station_id INT DEFAULT NULL,
            FOREIGN KEY (station_id) REFERENCES stations(station_id)
        )
    """)
    conn.commit()
    print("Tables ready.\n")

    # ── CLEAR OLD DATA ───────────────────────────────────────────────────────
    print("Clearing old data...")
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("TRUNCATE TABLE vehicles")
    cur.execute("TRUNCATE TABLE stations")
    cur.execute("TRUNCATE TABLE users")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()

    # ── INSERT STATIONS + VEHICLES ───────────────────────────────────────────
    print(f"Inserting {len(STATIONS)} stations and vehicles...")
    serial  = 1000
    drv_num = 1
    mon_num = 1
    user_rows = []

    for (name, stype, lat, lon, count) in STATIONS:
        cur.execute(
            "INSERT INTO stations (name,type,latitude,longitude,vehicles_available,status) VALUES (%s,%s,%s,%s,%s,'AVAILABLE')",
            (name, stype, lat, lon, count)
        )
        sid    = cur.lastrowid
        prefix = VEHICLE_PREFIX[stype]
        vtype  = VEHICLE_TYPES[stype]
        for _ in range(count):
            cur.execute(
                "INSERT INTO vehicles (vehicle_plate,type,station_id,status,last_service_date) VALUES (%s,%s,%s,'AVAILABLE',CURDATE())",
                (f"{prefix}{serial}", vtype, sid)
            )
            serial += 1

        # Build driver + monitor accounts for this station
        slug = name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "").replace("&","and")[:20]
        drv_pwd = f"Drv@{drv_num:02d}Mys"
        mon_pwd = f"Mon@{mon_num:02d}Mys"
        user_rows.append((f"driver_{slug}",  drv_pwd, "DRIVER",   sid))
        user_rows.append((f"monitor_{slug}", mon_pwd, "MONITOR",  sid))
        drv_num += 1
        mon_num += 1

    conn.commit()

    # ── INSERT USERS ─────────────────────────────────────────────────────────
    print("Inserting dispatcher/driver/monitor accounts...")
    cur.execute("""
        INSERT IGNORE INTO users (username,password,role,station_id) VALUES
        ('dispatch_med',  'Med@108',    'DISPATCHER', NULL),
        ('dispatch_fire', 'Fire@101',   'DISPATCHER', NULL),
        ('dispatch_pol',  'Police@100', 'DISPATCHER', NULL)
    """)
    cur.executemany(
        "INSERT IGNORE INTO users (username,password,role,station_id) VALUES (%s,%s,%s,%s)",
        user_rows
    )
    conn.commit()

    # ── SUMMARY ──────────────────────────────────────────────────────────────
    cur.execute("SELECT type, COUNT(*), SUM(vehicles_available) FROM stations GROUP BY type")
    print("\n✅ Aiven DB seeded successfully!\n")
    print(f"{'TYPE':<25} {'STATIONS':>8} {'VEHICLES':>9}")
    print("─" * 44)
    for (t, s, v) in cur.fetchall():
        print(f"{t:<25} {s:>8} {v:>9}")
    cur.execute("SELECT COUNT(*) FROM users")
    print(f"\nTotal user accounts: {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    print("\nDone. You can now redeploy on Render and log in.")

if __name__ == "__main__":
    run()
