-- ResQFlow complete Aiven setup SQL
-- Run this in MySQL Workbench connected to Aiven

USE defaultdb;

-- ── CREATE TABLES ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stations (
    station_id         INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    type               ENUM('HOSPITAL','FIRE_STATION','POLICE_STATION') NOT NULL,
    latitude           DECIMAL(10,7) NOT NULL,
    longitude          DECIMAL(10,7) NOT NULL,
    vehicles_available INT DEFAULT 0,
    status             VARCHAR(20) DEFAULT 'AVAILABLE'
);

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id        INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_plate     VARCHAR(20) NOT NULL,
    type              ENUM('AMBULANCE','FIRE_ENGINE','PATROL_CAR') NOT NULL,
    station_id        INT,
    status            VARCHAR(30) DEFAULT 'AVAILABLE',
    last_service_date DATE,
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id    INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50) NOT NULL UNIQUE,
    password   VARCHAR(100) NOT NULL,
    role       ENUM('DISPATCHER','DRIVER','MONITOR') NOT NULL,
    station_id INT DEFAULT NULL,
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

-- ── CLEAR OLD DATA ───────────────────────────────────────────────────────────
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE vehicles;
TRUNCATE TABLE stations;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

-- ── INSERT STATIONS ───────────────────────────────────────────────────────────
INSERT INTO stations (name, type, latitude, longitude, vehicles_available, status) VALUES
-- HOSPITALS
('K.R. Hospital (Government)',         'HOSPITAL',       12.3050, 76.6551, 4, 'AVAILABLE'),
('Cheluvamba Hospital',                 'HOSPITAL',       12.3101, 76.6452, 3, 'AVAILABLE'),
('Columbia Asia Hospital Mysore',       'HOSPITAL',       12.3338, 76.6140, 3, 'AVAILABLE'),
('JSS Hospital',                        'HOSPITAL',       12.3008, 76.5945, 4, 'AVAILABLE'),
('Manipal Hospital Mysore',             'HOSPITAL',       12.3272, 76.6468, 3, 'AVAILABLE'),
('Apollo BGS Hospital',                 'HOSPITAL',       12.2931, 76.6196, 3, 'AVAILABLE'),
('Basappa Memorial Hospital',           'HOSPITAL',       12.3131, 76.6591, 2, 'AVAILABLE'),
('Vikram Hospital',                     'HOSPITAL',       12.3044, 76.6611, 2, 'AVAILABLE'),
('Government Ayurvedic Hospital',       'HOSPITAL',       12.3068, 76.6534, 2, 'AVAILABLE'),
('District Hospital Nanjangud Road',    'HOSPITAL',       12.2749, 76.6450, 3, 'AVAILABLE'),
('Vani Vilas Women & Children Hospital','HOSPITAL',       12.3052, 76.6548, 2, 'AVAILABLE'),
('Narayana Multispeciality Hospital',   'HOSPITAL',       12.3396, 76.6078, 3, 'AVAILABLE'),
-- FIRE STATIONS
('Mysuru Central Fire Station',         'FIRE_STATION',   12.3076, 76.6556, 4, 'AVAILABLE'),
('Vijayanagar Fire Station',            'FIRE_STATION',   12.3323, 76.6063, 3, 'AVAILABLE'),
('Kuvempunagar Fire Station',           'FIRE_STATION',   12.3238, 76.6462, 3, 'AVAILABLE'),
('Bannimantap Fire Station',            'FIRE_STATION',   12.3181, 76.6285, 3, 'AVAILABLE'),
('Hebbal Fire Station',                 'FIRE_STATION',   12.3552, 76.6224, 2, 'AVAILABLE'),
('Hootagalli Fire Station',             'FIRE_STATION',   12.2900, 76.5890, 2, 'AVAILABLE'),
('Nanjangud Road Fire Post',            'FIRE_STATION',   12.2660, 76.6380, 2, 'AVAILABLE'),
-- POLICE STATIONS
('Mysuru City Police Headquarters',     'POLICE_STATION', 12.3062, 76.6553, 5, 'AVAILABLE'),
('Devaraja Police Station',             'POLICE_STATION', 12.3042, 76.6571, 4, 'AVAILABLE'),
('Lakshmipuram Police Station',         'POLICE_STATION', 12.3173, 76.6485, 3, 'AVAILABLE'),
('Kuvempunagar Police Station',         'POLICE_STATION', 12.3249, 76.6449, 3, 'AVAILABLE'),
('Nazarbad Police Station',             'POLICE_STATION', 12.3093, 76.6390, 3, 'AVAILABLE'),
('Jayalakshmipuram Police Station',     'POLICE_STATION', 12.3214, 76.6350, 3, 'AVAILABLE'),
('Vijayanagar Police Station',          'POLICE_STATION', 12.3318, 76.6074, 3, 'AVAILABLE'),
('Hebbal Police Station',               'POLICE_STATION', 12.3582, 76.6231, 3, 'AVAILABLE'),
('Bannimantap Police Station',          'POLICE_STATION', 12.3178, 76.6258, 3, 'AVAILABLE'),
('Bogadi Police Station',               'POLICE_STATION', 12.2931, 76.6086, 3, 'AVAILABLE'),
('Metagalli Police Station',            'POLICE_STATION', 12.3411, 76.5890, 2, 'AVAILABLE'),
('V.V. Mohalla Police Station',         'POLICE_STATION', 12.2986, 76.6567, 3, 'AVAILABLE'),
('Krishnamurthypuram Police Station',   'POLICE_STATION', 12.3135, 76.6596, 3, 'AVAILABLE'),
('Mandi Mohalla Police Station',        'POLICE_STATION', 12.3073, 76.6652, 3, 'AVAILABLE'),
('Saraswathipuram Police Station',      'POLICE_STATION', 12.3268, 76.6579, 3, 'AVAILABLE');

-- ── INSERT VEHICLES ──────────────────────────────────────────────────────────
INSERT INTO vehicles (vehicle_plate, type, station_id, status, last_service_date)
SELECT CONCAT(
    CASE s.type WHEN 'HOSPITAL' THEN 'KA21A' WHEN 'FIRE_STATION' THEN 'KA21F' ELSE 'KA21P' END,
    1000 + ROW_NUMBER() OVER (ORDER BY s.station_id, n.n)
),
CASE s.type WHEN 'HOSPITAL' THEN 'AMBULANCE' WHEN 'FIRE_STATION' THEN 'FIRE_ENGINE' ELSE 'PATROL_CAR' END,
s.station_id, 'AVAILABLE', CURDATE()
FROM stations s
JOIN (SELECT 1 n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) n
  ON n.n <= s.vehicles_available;

-- ── INSERT USERS ─────────────────────────────────────────────────────────────
-- Dispatchers (3)
INSERT IGNORE INTO users (username, password, role, station_id) VALUES
('dispatch_med',  'Med@108',    'DISPATCHER', NULL),
('dispatch_fire', 'Fire@101',   'DISPATCHER', NULL),
('dispatch_pol',  'Police@100', 'DISPATCHER', NULL);

-- Drivers (one per station, numbered 01-34)
INSERT IGNORE INTO users (username, password, role, station_id)
SELECT CONCAT('driver_', LPAD(station_id, 2, '0')),
       CONCAT('Drv@', LPAD(station_id, 2, '0'), 'Mys'),
       'DRIVER', station_id
FROM stations;

-- Monitors (one per station, numbered 01-34)
INSERT IGNORE INTO users (username, password, role, station_id)
SELECT CONCAT('monitor_', LPAD(station_id, 2, '0')),
       CONCAT('Mon@', LPAD(station_id, 2, '0'), 'Mys'),
       'MONITOR', station_id
FROM stations;

-- ── VERIFY ───────────────────────────────────────────────────────────────────
SELECT 'STATIONS' AS tbl, COUNT(*) AS count FROM stations
UNION ALL SELECT 'VEHICLES', COUNT(*) FROM vehicles
UNION ALL SELECT 'USERS',    COUNT(*) FROM users;
