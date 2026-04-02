# 🚨 ResQFlow — AI-Powered Emergency Response System

ResQFlow is a full-stack web application that simulates an intelligent emergency dispatch system for Mysuru City. It coordinates Medical, Fire, and Police emergency services in real-time using road-following vehicle simulation powered by the OSRM routing engine and a live AI traffic heatmap.

🌐 **Live Demo:** [https://resqflow.onrender.com](https://resqflow.onrender.com)

---

## 📋 Project Overview

| Detail | Info |
|---|---|
| Project Type | Web Application (Flask + MySQL) |
| City | Mysuru, Karnataka, India |
| Services | Medical (108) · Fire (101) · Police (100) |
| Stations | 34 real stations across Mysuru |
| Vehicles | 100 vehicles total |
| User Roles | Dispatcher · Driver · Monitor |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · Flask |
| Database | MySQL 8.x |
| Frontend | HTML5 · CSS3 · JavaScript |
| Maps | Leaflet.js 1.7.1 |
| Road Routing | OSRM Public API (free, no API key needed) |
| Traffic Engine | Custom AI heuristic (time-of-day + zone density) |
| UI Libraries | jQuery 3.6 · Google Fonts (Orbitron, Rajdhani, IBM Plex Mono) |

---

## 🌡️ Live Traffic Heatmap

ResQFlow features a fully animated, multi-zone traffic heatmap across Mysuru city — visible on all three dashboard views (Dispatcher, Driver, Monitor).

### How it works

- **10 named traffic hotspots** are modelled across Mysuru based on real congestion patterns:
  - Palace Rd / City Centre, Sayyaji Rao Rd, KR Hospital Area
  - Bannimantap Junction, Nazarbad Junction, Vijayanagar 4th Stage
  - Hebbal Ring Road, Bogadi Rd Junction, Mysuru–Bengaluru NH, Ooty Rd Junction

- Each zone is rendered as **4 concentric gradient circles** fading from a solid core outward, colour-coded by congestion intensity:

  | Colour | Intensity | Meaning |
  |---|---|---|
  | 🟢 Green | 0–30% | Free-flowing traffic |
  | 🟡 Yellow | 30–60% | Moderate congestion |
  | 🟠 Orange | 60–80% | Heavy traffic |
  | 🔴 Red | 80–100% | Severe / gridlock |

- **Rush hours** (08:00–10:00 and 17:00–20:00) automatically boost hotspot intensity and expand zone radii
- **Night hours** (23:00–06:00) greatly reduce all intensities
- A ±6% random jitter is applied on every 8-second poll so no two refreshes look identical

### Alive / Animated Features

- 🌊 **Breathing animation** — a 20 fps sine-wave oscillator continuously shifts each heat blob's opacity by ±15%, making the map feel alive even between server polls
- 🚗 **Ghost vehicles** — 12 emoji cars and buses (`🚗 🚕 🚙 🛻 🚌 🚐`) move along real Mysuru road segments every 200 ms, slowing down during rush hour to simulate real congestion
- 💥 **Pulse rings** — high-intensity zones (>65%) emit an animated expanding ring

### Traffic Status Bar

Every dashboard header shows a live status pill:

| Pill | Multiplier | Label |
|---|---|---|
| `LIGHT` | < 1.2× | Traffic flowing freely |
| `MODERATE` | 1.2–1.6× | Moderate flow |
| `HEAVY` | 1.6–2.0× | Heavy congestion |
| `SEVERE` | > 2.0× | Rush hour gridlock |

A **heatmap legend panel** in the bottom-right of every map lists all active zones with their live intensity percentages.

---

## 📁 Project Structure

```
ResQFlow/
├── app.py                            ← Main Flask backend
├── ai_traffic.py                     ← AI traffic prediction & heatmap zones
├── seed_db.py                        ← Database seeding script (run once)
├── simulation_status.json            ← Live mission state (create as empty {})
├── README.md
└── templates/
    ├── home.html                     ← Landing page
    ├── dispatcher_select.html        ← Service selection (Medical/Fire/Police)
    ├── login_dispatcher_service.html ← Themed dispatcher login
    ├── login_driver.html             ← Driver login
    ├── login_monitor.html            ← Monitor login
    ├── dispatcher_map.html           ← Dispatch console with heatmap + ghost vehicles
    ├── driver_dashboard.html         ← Driver HUD with live navigation + heatmap
    └── monitor_dashboard.html        ← Station ops center with heatmap
```

---

## ⚙️ Requirements

### System Requirements

- Python 3.10 or higher
- MySQL 8.0 or higher
- MySQL Workbench (for database setup)
- Internet connection (for OSRM road routing API)

### Python Packages

```bash
pip install flask mysql-connector-python
```

---

## 🗄️ Database Setup

### Step 1 — Create the Database and Tables

Open **MySQL Workbench**, connect to your local server, and run:

```sql
CREATE DATABASE resqflow;
USE resqflow;

CREATE TABLE stations (
    station_id         INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    type               ENUM('HOSPITAL','FIRE_STATION','POLICE_STATION') NOT NULL,
    latitude           DECIMAL(10,7) NOT NULL,
    longitude          DECIMAL(10,7) NOT NULL,
    vehicles_available INT DEFAULT 0,
    status             VARCHAR(20) DEFAULT 'AVAILABLE'
);

CREATE TABLE vehicles (
    vehicle_id        INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_plate     VARCHAR(20) NOT NULL,
    type              ENUM('AMBULANCE','FIRE_ENGINE','PATROL_CAR') NOT NULL,
    station_id        INT,
    status            VARCHAR(30) DEFAULT 'AVAILABLE',
    last_service_date DATE,
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

CREATE TABLE users (
    user_id    INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50) NOT NULL UNIQUE,
    password   VARCHAR(100) NOT NULL,
    role       ENUM('DISPATCHER','DRIVER','MONITOR') NOT NULL,
    station_id INT DEFAULT NULL,
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);
```

### Step 2 — Update DB Config in app.py

Open `app.py` and update this section with your MySQL password:

```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_MYSQL_PASSWORD",
    "database": "resqflow"
}
```

### Step 3 — Seed Stations and Vehicles

```bash
python seed_db.py
```

This inserts all **34 real Mysuru stations** and **100 vehicles**.

### Step 4 — Insert User Accounts

Run the following in MySQL Workbench:

```sql
USE resqflow;

-- DISPATCHERS (3 accounts)
INSERT INTO users (username, password, role, station_id) VALUES
  ('dispatch_med',  'Med@108',    'DISPATCHER', NULL),
  ('dispatch_fire', 'Fire@101',   'DISPATCHER', NULL),
  ('dispatch_pol',  'Police@100', 'DISPATCHER', NULL);
```

For all **34 driver accounts** and **34 monitor accounts**, use the SQL from the `SQL_Inserts` sheet in **ResQFlow_Logins.xlsx**.

---

## 🚀 Running the Application

### Step 1 — Create the simulation status file

In the project root folder:

```bash
echo {} > simulation_status.json
```

### Step 2 — Start the Flask server

```bash
python app.py
```

### Step 3 — Open in browser

```
http://127.0.0.1:5000
```

Or visit the live deployment: [https://resqflow.onrender.com](https://resqflow.onrender.com)

---

## 👤 Login Credentials

### Dispatchers

| Service | Username | Password | Hotline |
|---|---|---|---|
| Medical | `dispatch_med` | `Med@108` | 108 |
| Fire | `dispatch_fire` | `Fire@101` | 101 |
| Police | `dispatch_pol` | `Police@100` | 100 |

### Drivers & Monitors

34 accounts each. Pattern:
- **Drivers:** username = `driver_<stationslug>` · password = `Drv@01Mys` to `Drv@34Mys`
- **Monitors:** username = `monitor_<stationslug>` · password = `Mon@01Mys` to `Mon@34Mys`

Full credentials in **ResQFlow_Logins.xlsx**.

---

## 🔄 How to Use the System

### As a Dispatcher

1. Go to the app (local or [live](https://resqflow.onrender.com))
2. Click **DISPATCHER**
3. Choose your service — **Medical**, **Fire**, or **Police**
4. Log in with your dispatcher credentials
5. The map shows all stations with vehicle availability and the **live traffic heatmap**
6. Click anywhere on the map to mark the **incident location**
7. Click **DISPATCH** — the system automatically selects the nearest available station
8. The driver at that station receives an instant notification

### As a Driver

1. Go to the app and click **DRIVER**, then log in
2. Wait on standby — a mission alert appears when dispatched
3. Review the incident details and click **"LEFT THE STATION — CONFIRM"**
4. Your vehicle moves along actual Mysuru roads to the incident location
5. The **live heatmap** shows city congestion zones and ghost vehicle traffic around you
6. Once arrived the status changes to **"AT INCIDENT LOCATION"**
7. Click **"LEAVE THE LOCATION"** when done
8. Your vehicle follows the road back to base automatically
9. Mission completes and vehicle count is restored at your station

### As a Monitor

1. Go to the app and click **MONITOR**, then log in
2. Your dashboard shows the real-time status of your station's unit
3. When a mission is assigned to your station you see:
   - Live vehicle position on the map
   - Speed and leg progress telemetry
   - Current mission phase
   - Activity log with timestamps
   - **Live traffic heatmap** with zone intensity legend
4. All updates refresh every second automatically

---

## 🗺️ Stations Covered

| Service | Stations | Vehicles |
|---|---|---|
| Hospitals (Medical) | 12 | 34 ambulances |
| Fire Stations | 7 | 19 fire engines |
| Police Stations | 15 | 47 patrol cars |
| **TOTAL** | **34** | **100** |

---

## 🔄 Mission Phases

| Phase | Description |
|---|---|
| `PENDING DRIVER` | Mission assigned, awaiting driver confirmation |
| `EN ROUTE TO INCIDENT` | Vehicle moving to incident via real Mysuru roads |
| `AT INCIDENT LOCATION` | Vehicle at scene, driver working — leave button active |
| `RETURNING TO BASE` | Vehicle heading back to station via roads |
| `MISSION COMPLETE` | Vehicle returned, vehicle count restored in DB |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/traffic_zone` | GET | Legacy single-zone traffic state (used for route segment colouring) |
| `/api/traffic_heatmap` | GET | Multi-zone heatmap data — all 10 hotspots with intensity, radius, rush/night flags |
| `/get_status` | GET | Live mission simulation state |
| `/get_route` | GET | Current leg waypoints for map rendering |
| `/dispatch_action` | POST | Dispatcher triggers a new mission |
| `/driver_start_mission` | POST | Driver confirms and starts simulation |
| `/driver_leave_scene` | POST | Driver departs scene, triggers return leg |

---

## 📌 Important Notes

- Road routing uses the **free public OSRM API** — internet connection is required
- If OSRM is unreachable, simulation falls back to straight-line movement automatically
- Only **one active mission** is supported at a time
- Each dispatcher account is locked to their own service type only
- No SUMO or any external simulation software required — fully web-native
- The traffic heatmap is **heuristic-based** (time-of-day + zone density), not live GPS data

---

## 🧑‍💻 Author

Built as a Web Development course project.  
**ResQFlow** — Emergency Response System · Mysuru City  
🌐 [https://resqflow.onrender.com](https://resqflow.onrender.com)
