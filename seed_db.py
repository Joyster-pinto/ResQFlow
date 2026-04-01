"""
ResQFlow — Database Seed Script
================================
Run this ONCE to populate your database with real stations in Mysuru city.
  > python seed_db.py

It will:
  1. Clear old stations and vehicles tables
  2. Insert real hospitals, fire stations, police stations with coordinates
  3. Add vehicles per station based on realistic capacity
  4. Print a summary when done
"""
import os
import mysql.connector

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "106975123"),
    "database": os.environ.get("DB_NAME", "resqflow"),
    "port": int(os.environ.get("DB_PORT", 3306))
}   
# ─────────────────────────────────────────────────────────────────────────────
#  REAL MYSURU STATIONS  (name, type, lat, lon, vehicle_count)
#  Types: HOSPITAL | FIRE_STATION | POLICE_STATION
# ─────────────────────────────────────────────────────────────────────────────

STATIONS = [

    # ── HOSPITALS / MEDICAL ──────────────────────────────────────────────────
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

    # ── FIRE STATIONS ────────────────────────────────────────────────────────
    ("Mysuru Central Fire Station",          "FIRE_STATION",   12.3076, 76.6556, 4),
    ("Vijayanagar Fire Station",             "FIRE_STATION",   12.3323, 76.6063, 3),
    ("Kuvempunagar Fire Station",            "FIRE_STATION",   12.3238, 76.6462, 3),
    ("Bannimantap Fire Station",             "FIRE_STATION",   12.3181, 76.6285, 3),
    ("Hebbal Fire Station",                  "FIRE_STATION",   12.3552, 76.6224, 2),
    ("Hootagalli Fire Station",              "FIRE_STATION",   12.2900, 76.5890, 2),
    ("Nanjangud Road Fire Post",             "FIRE_STATION",   12.2660, 76.6380, 2),

    # ── POLICE STATIONS ──────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
#  VEHICLE TYPES per station type
# ─────────────────────────────────────────────────────────────────────────────

VEHICLE_TYPES = {
    "HOSPITAL":       "AMBULANCE",
    "FIRE_STATION":   "FIRE_ENGINE",
    "POLICE_STATION": "PATROL_CAR",
}

VEHICLE_PREFIX = {
    "HOSPITAL":       "KA21A",
    "FIRE_STATION":   "KA21F",
    "POLICE_STATION": "KA21P",
}

def seed():
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE vehicles")
    cursor.execute("TRUNCATE TABLE stations")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # Fix the ENUM to accept our vehicle type values
    cursor.execute("""
        ALTER TABLE vehicles 
        MODIFY COLUMN type ENUM('AMBULANCE','FIRE_ENGINE','PATROL_CAR') NOT NULL
    """)

    print(f"📍 Inserting {len(STATIONS)} stations…")
    station_sql = """
        INSERT INTO stations (name, type, latitude, longitude, vehicles_available, status)
        VALUES (%s, %s, %s, %s, %s, 'AVAILABLE')
    """
    vehicle_sql = """
        INSERT INTO vehicles (vehicle_plate, type, station_id, status, last_service_date)
        VALUES (%s, %s, %s, 'AVAILABLE', CURDATE())
    """

    vehicle_serial = 1000

    for (name, stype, lat, lon, count) in STATIONS:
        cursor.execute(station_sql, (name, stype, lat, lon, count))
        station_id = cursor.lastrowid

        prefix = VEHICLE_PREFIX[stype]
        vtype  = VEHICLE_TYPES[stype]
        for _ in range(count):
            plate = f"{prefix}{vehicle_serial}"
            cursor.execute(vehicle_sql, (plate, vtype, station_id))
            vehicle_serial += 1

    conn.commit()

    # ── SUMMARY ──
    cursor.execute("SELECT type, COUNT(*) as cnt, SUM(vehicles_available) as veh FROM stations GROUP BY type")
    rows = cursor.fetchall()

    print("\n✅ Database seeded successfully!\n")
    print(f"{'TYPE':<25} {'STATIONS':>8} {'VEHICLES':>9}")
    print("─" * 45)
    total_s, total_v = 0, 0
    for (t, s, v) in rows:
        print(f"{t:<25} {s:>8} {v:>9}")
        total_s += s; total_v += (v or 0)
    print("─" * 45)
    print(f"{'TOTAL':<25} {total_s:>8} {total_v:>9}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed()