from flask import Flask, render_template, jsonify, request, redirect, session
import os, json, mysql.connector, math, threading, time
import urllib.request as urlreq
opener = urlreq.build_opener()
opener.addheaders = [('User-Agent', 'ResQFlow-Student-Project/1.0')]
urlreq.install_opener(opener)
app = Flask(__name__)
app.secret_key = 'resqflow_secret_key_999'

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "106975123"),
    "database": os.environ.get("DB_NAME", "resqflow"),
    "port": int(os.environ.get("DB_PORT", 3306))
}
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(BASE_DIR, "simulation_status.json")

# ── THEME MAPS ────────────────────────────────────────────────────────────────
DRIVER_THEMES = {
    "HOSPITAL":      {"accent":"#ff3a3a","accent2":"#ff6b6b","accent_dim":"rgba(255,58,58,0.12)","accent_border":"rgba(255,58,58,0.3)","vehicle_emoji":"🚑","service_label":"AMBULANCE"},
    "FIRE_STATION":  {"accent":"#ff6b00","accent2":"#ffaa44","accent_dim":"rgba(255,107,0,0.12)","accent_border":"rgba(255,107,0,0.3)","vehicle_emoji":"🚒","service_label":"FIRE ENGINE"},
    "POLICE_STATION":{"accent":"#3a8eff","accent2":"#78b4ff","accent_dim":"rgba(58,142,255,0.12)","accent_border":"rgba(58,142,255,0.3)","vehicle_emoji":"🚓","service_label":"PATROL CAR"},
}
MONITOR_THEMES = {
    "HOSPITAL":      {"accent":"#00e5b0","accent2":"#00ff88","accent_dim":"rgba(0,229,176,0.1)","accent_border":"rgba(0,229,176,0.25)","bg":"#050f0c","surface":"#081812","station_label":"HOSPITAL MONITOR","station_icon":"🏥"},
    "FIRE_STATION":  {"accent":"#ff6b00","accent2":"#ffaa44","accent_dim":"rgba(255,107,0,0.1)","accent_border":"rgba(255,107,0,0.25)","bg":"#100800","surface":"#180c00","station_label":"FIRE STATION MONITOR","station_icon":"🔥"},
    "POLICE_STATION":{"accent":"#6699ff","accent2":"#99bbff","accent_dim":"rgba(102,153,255,0.1)","accent_border":"rgba(102,153,255,0.25)","bg":"#040814","surface":"#080c1a","station_label":"POLICE STATION MONITOR","station_icon":"🚔"},
}

# On-scene work duration and status messages per service type
ONSCENE = {
    "HOSPITAL":       {"status": "AT INCIDENT LOCATION", "label": "🏥 Loading patient into ambulance…"},
    "FIRE_STATION":   {"status": "AT INCIDENT LOCATION", "label": "🔥 Extinguishing fire at scene…"},
    "POLICE_STATION": {"status": "AT INCIDENT LOCATION", "label": "🚔 Resolving incident at scene…"},
}

# Driver clicks "Leave the Location" → sets this event → return leg starts
leave_scene_event = threading.Event()

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def get_station_type(station_id):
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT type FROM stations WHERE station_id=%s", (station_id,))
        row = cur.fetchone(); conn.close()
        return row['type'] if row else 'HOSPITAL'
    except:
        return 'HOSPITAL'

def restore_vehicle_to_station(station_id):
    """Increment vehicles_available when unit returns to base."""
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "UPDATE stations SET vehicles_available=vehicles_available+1 WHERE station_id=%s",
            (station_id,)
        )
        conn.commit(); conn.close()
        print(f"[DB] Vehicle returned to station {station_id}. Count restored.")
    except Exception as e:
        print(f"[DB] Error restoring vehicle: {e}")

# ── OSRM ROAD ROUTING ─────────────────────────────────────────────────────────
def get_road_waypoints(start_lat, start_lon, dest_lat, dest_lon):
    try:
        url = (
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{dest_lon},{dest_lat}"
            f"?overview=full&geometries=geojson&steps=false"
        )
        req = urlreq.Request(url, headers={"User-Agent":"ResQFlow/2.0"})
        with urlreq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        coords = data["routes"][0]["geometry"]["coordinates"]
        return [[c[1], c[0]] for c in coords]
    except Exception as e:
        print(f"[OSRM] Failed: {e} → straight-line fallback")
        return [
            [start_lat+(dest_lat-start_lat)*i/19,
             start_lon+(dest_lon-start_lon)*i/19]
            for i in range(20)
        ]

def write_status(data):
    try:
        with open(STATUS_FILE,'w') as f:
            json.dump(data, f)
    except:
        pass

def animate_leg(waypoints, steps, speed_kmh, phase, base_data):
    """
    Animate movement along a list of waypoints over `steps` ticks.
    base_data: dict of fixed fields to include in every status update.
    """
    n = len(waypoints)
    for step in range(steps + 1):
        t      = step / steps
        t_ease = t * t * (3 - 2 * t)
        idx_f  = t_ease * (n - 1)
        idx_lo = int(idx_f)
        idx_hi = min(idx_lo + 1, n - 1)
        frac   = idx_f - idx_lo

        lat = waypoints[idx_lo][0] + (waypoints[idx_hi][0] - waypoints[idx_lo][0]) * frac
        lon = waypoints[idx_lo][1] + (waypoints[idx_hi][1] - waypoints[idx_lo][1]) * frac

        if t < 0.1:
            speed = speed_kmh * (t / 0.1)
        elif t > 0.85:
            speed = speed_kmh * ((1 - t) / 0.15)
        else:
            speed = speed_kmh + math.sin(t * math.pi * 3) * 6

        write_status({**base_data,
            "phase":           phase,
            "ambulance_status": phase,
            "ambulance_speed": round(speed, 1),
            "ambulance_active": True,
            "lat": lat, "lon": lon,
            "progress_pct":    round(t * 100, 1),
            "step":            step,
        })
        time.sleep(1)

# ── FULL ROUND-TRIP SIMULATION ────────────────────────────────────────────────
def simulate_vehicle(start_lat, start_lon, dest_lat, dest_lon,
                     station_id, station_name, station_type):
    STEPS_OUTBOUND = 60
    STEPS_RETURN   = 50
    SPEED_KMH      = 60.0

    onscene     = ONSCENE.get(station_type, ONSCENE["HOSPITAL"])
    work_status = onscene["status"]

    base = {
        "station_id":   station_id,
        "station_name": station_name,
        "start_lat":    start_lat,  "start_lon": start_lon,
        "dest_lat":     dest_lat,   "dest_lon":  dest_lon,
    }

    # ── LEG 1: Station → Incident ────────────────────────────────────────────
    print("[SIM] LEG 1: Fetching outbound route…")
    outbound = get_road_waypoints(start_lat, start_lon, dest_lat, dest_lon)
    print(f"[SIM] LEG 1: {len(outbound)} waypoints. Animating outbound…")
    animate_leg(outbound, STEPS_OUTBOUND, SPEED_KMH, "EN ROUTE TO INCIDENT", base)

    # ── PHASE 2: AT INCIDENT LOCATION — wait for driver to click Leave ────────
    print("[SIM] PHASE 2: Arrived. Waiting for driver to click Leave…")
    leave_scene_event.clear()   # reset in case it was set before
    tick = 0
    while not leave_scene_event.is_set():
        write_status({**base,
            "phase":            "AT INCIDENT LOCATION",
            "ambulance_status": "AT INCIDENT LOCATION",
            "ambulance_speed":  0,
            "ambulance_active": True,
            "awaiting_leave":   True,          # tells frontend to show button
            "lat": dest_lat, "lon": dest_lon,
            "progress_pct":     0,
            "step":             tick,
            "onscene_label":    onscene["label"],
        })
        tick += 1
        time.sleep(1)

    print("[SIM] Driver clicked Leave. Starting return leg…")

    # ── LEG 3: Incident → Station (return) ───────────────────────────────────
    print("[SIM] LEG 3: Fetching return route…")
    return_route = get_road_waypoints(dest_lat, dest_lon, start_lat, start_lon)
    print(f"[SIM] LEG 3: {len(return_route)} waypoints. Animating return…")
    animate_leg(return_route, STEPS_RETURN, SPEED_KMH, "RETURNING TO BASE", base)

    # ── MISSION COMPLETE ─────────────────────────────────────────────────────
    write_status({**base,
        "phase":            "MISSION COMPLETE",
        "ambulance_status": "MISSION COMPLETE",
        "ambulance_speed":  0,
        "ambulance_active": False,
        "lat": start_lat, "lon": start_lon,
        "progress_pct":     100.0,
        "step":             0,
    })
    restore_vehicle_to_station(station_id)
    print("[SIM] Mission COMPLETE. Vehicle returned to base.")

# ── HOME ──────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

# ── DISPATCHER ────────────────────────────────────────────────────────────────

# Theme data for each service type dispatcher login page
DISPATCHER_LOGIN_THEMES = {
    "medical": {
        "accent":        "#ff3a3a",
        "accent2":       "#ff6b6b",
        "accent_dim":    "rgba(255,58,58,0.1)",
        "accent_border": "rgba(255,58,58,0.3)",
        "icon":          "🚑",
        "hotline":       "108",
        "tagline":       "Ambulance Dispatch Console",
        "stat1":         "12 hospitals across Mysuru city",
        "stat2":         "34 ambulances ready to deploy",
        "stat3":         "Nearest unit auto-selected by AI",
    },
    "fire": {
        "accent":        "#ff6b00",
        "accent2":       "#ffaa44",
        "accent_dim":    "rgba(255,107,0,0.1)",
        "accent_border": "rgba(255,107,0,0.3)",
        "icon":          "🚒",
        "hotline":       "101",
        "tagline":       "Fire Engine Dispatch Console",
        "stat1":         "7 fire stations across Mysuru city",
        "stat2":         "19 fire engines ready to deploy",
        "stat3":         "Real-time road routing via OSRM",
    },
    "police": {
        "accent":        "#3a8eff",
        "accent2":       "#78b4ff",
        "accent_dim":    "rgba(58,142,255,0.1)",
        "accent_border": "rgba(58,142,255,0.3)",
        "icon":          "🚓",
        "hotline":       "100",
        "tagline":       "Patrol Car Dispatch Console",
        "stat1":         "15 police stations across Mysuru city",
        "stat2":         "47 patrol cars ready to deploy",
        "stat3":         "Live unit tracking for all monitors",
    },
}

SERVICE_LABELS = {"medical": "Medical", "fire": "Fire", "police": "Police"}

# Credential mapping — each dispatcher account only works for its service
SERVICE_CREDENTIALS = {
    "medical": "dispatch_med",
    "fire":    "dispatch_fire",
    "police":  "dispatch_pol",
}

@app.route('/dispatcher_select')
def dispatcher_select():
    return render_template('dispatcher_select.html')

@app.route('/login/dispatcher/<service_type>', methods=['GET','POST'])
def login_dispatcher_service(service_type):
    if service_type not in DISPATCHER_LOGIN_THEMES:
        return redirect('/dispatcher_select')

    theme        = DISPATCHER_LOGIN_THEMES[service_type]
    service_label = SERVICE_LABELS[service_type]

    if request.method == 'POST':
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s AND role='DISPATCHER'",
            (request.form['username'], request.form['password'])
        )
        user = cur.fetchone(); conn.close()

        # Only allow the correct dispatcher for this service type
        expected_user = SERVICE_CREDENTIALS[service_type]
        if user and user['username'] == expected_user:
            session['dispatcher_user']   = user['username']
            session['dispatcher_service'] = service_type
            return redirect(f'/dispatcher/{service_type}')

        return render_template('login_dispatcher_service.html',
                               service_type=service_type,
                               service_label=service_label,
                               theme=theme,
                               error="Invalid credentials for this service.")

    return render_template('login_dispatcher_service.html',
                           service_type=service_type,
                           service_label=service_label,
                           theme=theme,
                           error=None)

# Keep old route as fallback redirect
@app.route('/login/dispatcher', methods=['GET','POST'])
def login_dispatcher():
    return redirect('/dispatcher_select')

@app.route('/dispatcher_hub')
def dispatcher_hub():
    return redirect('/dispatcher_select')

@app.route('/dispatcher/<service_type>')
def dispatcher_view(service_type):
    if 'dispatcher_user' not in session: return redirect('/dispatcher_select')
    # Ensure dispatcher only accesses their own service
    if session.get('dispatcher_service') != service_type:
        return redirect(f"/dispatcher_select")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    db_type = {'medical':'HOSPITAL','fire':'FIRE_STATION','police':'POLICE_STATION'}.get(service_type)
    cur.execute("SELECT * FROM stations WHERE type=%s ORDER BY name", (db_type,))
    stations = cur.fetchall(); conn.close()
    return render_template('dispatcher_map.html', service_type=service_type, stations=stations)

@app.route('/dispatch_action', methods=['POST'])
def dispatch_action():
    if 'dispatcher_user' not in session:
        return jsonify({"status":"error","message":"Unauthorized"})
    
    data = request.json
    lat, lon = data['lat'], data['lon']
    service_type = data.get('type','medical')
    type_map = {'medical':'HOSPITAL','fire':'FIRE_STATION','police':'POLICE_STATION'}

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM stations WHERE type=%s AND vehicles_available>0",
                (type_map.get(service_type),))
    stations = cur.fetchall()
    
    if not stations:
        conn.close()
        return jsonify({"status":"error","message":"No vehicles available at any station!"})

    # Find the nearest station
    station = min(stations, key=lambda s: math.sqrt(
        (s['latitude']-lat)**2 + (s['longitude']-lon)**2))

    # FIXED: Changed 'WHERE station_id=%s' to 'WHERE id=%s' 
    # and changed station['station_id'] to station['id']
    cur.execute("UPDATE stations SET vehicles_available=vehicles_available-1 WHERE id=%s",
                (station['id'],))
    conn.commit()
    conn.close()

    # FIXED: Changed station['station_id'] to station['id'] in the JSON output
    write_status({
        "status":           "PENDING_DRIVER",
        "station_id":       station['id'],
        "station_name":     station['name'],
        "station_type":     station['type'],
        "start_lat":        station['latitude'],
        "start_lon":        station['longitude'],
        "dest_lat":         lat,
        "dest_lon":         lon,
        "ambulance_active": False,
        "phase":            "PENDING_DRIVER",
    })
    
    return jsonify({"status":"success","message":f"Mission dispatched to {station['name']}!"})
# ── DRIVER ────────────────────────────────────────────────────────────────────
@app.route('/login/driver', methods=['GET','POST'])
def login_driver():
    if request.method == 'POST':
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s AND role='DRIVER'",
                    (request.form['username'], request.form['password']))
        user = cur.fetchone(); conn.close()
        if user:
            session['driver_user']         = user['username']
            session['driver_station_id']   = user['station_id']
            session['driver_station_type'] = get_station_type(user['station_id'])
            return redirect('/driver_dashboard')
        return render_template('login_driver.html', error="Invalid driver credentials")
    return render_template('login_driver.html')

@app.route('/driver_dashboard')
def driver_dashboard():
    if 'driver_user' not in session: return redirect('/login/driver')
    stype = session.get('driver_station_type','HOSPITAL')
    return render_template('driver_dashboard.html',
        station_id=session['driver_station_id'],
        station_type=stype,
        theme=DRIVER_THEMES.get(stype, DRIVER_THEMES['HOSPITAL']))

@app.route('/driver_start_mission', methods=['POST'])
def driver_start_mission():
    if 'driver_user' not in session:
        return jsonify({"status":"error","message":"Unauthorized"})
    if not os.path.exists(STATUS_FILE):
        return jsonify({"status":"error","message":"No active mission found"})
    with open(STATUS_FILE,'r') as f:
        mission = json.load(f)
    if not all(k in mission for k in ['start_lat','start_lon','dest_lat','dest_lon']):
        return jsonify({"status":"error","message":"Mission data incomplete"})

    stype = mission.get('station_type', get_station_type(mission['station_id']))

    threading.Thread(
        target=simulate_vehicle,
        args=(mission['start_lat'], mission['start_lon'],
              mission['dest_lat'],  mission['dest_lon'],
              mission['station_id'], mission.get('station_name','Station'), stype),
        daemon=True
    ).start()
    return jsonify({"status":"started"})

@app.route('/driver_leave_scene', methods=['POST'])
def driver_leave_scene():
    """Driver clicked 'Leave the Location' — triggers the return leg."""
    if 'driver_user' not in session:
        return jsonify({"status":"error","message":"Unauthorized"})
    leave_scene_event.set()
    print("[SIM] leave_scene_event SET by driver.")
    return jsonify({"status":"leaving"})

# ── MONITOR ───────────────────────────────────────────────────────────────────
@app.route('/login/monitor', methods=['GET','POST'])
def login_monitor():
    if request.method == 'POST':
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s AND role='MONITOR'",
                    (request.form['username'], request.form['password']))
        user = cur.fetchone(); conn.close()
        if user:
            session['monitor_user']         = user['username']
            session['monitor_station_id']   = user['station_id']
            session['monitor_station_type'] = get_station_type(user['station_id'])
            return redirect('/monitor_dashboard')
        return render_template('login_monitor.html', error="Invalid monitor credentials")
    return render_template('login_monitor.html')

@app.route('/monitor_dashboard')
def monitor_dashboard():
    if 'monitor_user' not in session: return redirect('/login/monitor')
    stype = session.get('monitor_station_type','HOSPITAL')
    return render_template('monitor_dashboard.html',
        station_id=session['monitor_station_id'],
        station_type=stype,
        theme=MONITOR_THEMES.get(stype, MONITOR_THEMES['HOSPITAL']))

# ── SHARED API ────────────────────────────────────────────────────────────────
@app.route('/get_route')
def get_route():
    """Returns road waypoints for the CURRENT leg being driven."""
    try:
        with open(STATUS_FILE,'r') as f:
            m = json.load(f)
        phase = m.get('phase','')
        if 'RETURN' in phase:
            # Return leg: incident → station
            wps = get_road_waypoints(m['dest_lat'], m['dest_lon'],
                                      m['start_lat'], m['start_lon'])
        else:
            # Outbound leg: station → incident
            wps = get_road_waypoints(m['start_lat'], m['start_lon'],
                                      m['dest_lat'],  m['dest_lon'])
        return jsonify({"waypoints": wps, "phase": phase})
    except:
        return jsonify({"waypoints":[], "phase":""})

@app.route('/get_status')
def get_status():
    try:
        with open(STATUS_FILE,'r') as f: return jsonify(json.load(f))
    except:
        return jsonify({})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
    #last