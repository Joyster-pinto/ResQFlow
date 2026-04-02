import datetime
import math
import random

class AITrafficPredictor:
    """
    Simulates an AI/ML Traffic Prediction Engine pointing at Mysuru.
    Because we don't have access to paid Google Maps Traffic APIs,
    this engine heuristically calculates real-time ETA based on
    bounding boxes for high-traffic zones and the system's actual time of day.
    """
    
    # Bounding box roughly around Mysuru Palace / City Center (High Congestion Zone)
    CITY_CENTER_LAT_MIN = 12.2980
    CITY_CENTER_LAT_MAX = 12.3150
    CITY_CENTER_LON_MIN = 76.6450
    CITY_CENTER_LON_MAX = 76.6650

    # All major traffic hotspot zones in Mysuru
    TRAFFIC_ZONES = [
        {"name": "Palace Rd / City Centre",  "lat": 12.3052, "lon": 76.6552, "base_radius": 650,  "base_intensity": 1.0},
        {"name": "Bannimantap Junction",       "lat": 12.2990, "lon": 76.5900, "base_radius": 420,  "base_intensity": 0.75},
        {"name": "Sayyaji Rao Rd",            "lat": 12.3120, "lon": 76.6490, "base_radius": 350,  "base_intensity": 0.82},
        {"name": "Vijayanagar 4th Stage",     "lat": 12.3320, "lon": 76.5900, "base_radius": 380,  "base_intensity": 0.60},
        {"name": "Nazarbad Junction",         "lat": 12.3010, "lon": 76.6420, "base_radius": 280,  "base_intensity": 0.55},
        {"name": "Hebbal Ring Road",          "lat": 12.3540, "lon": 76.6160, "base_radius": 310,  "base_intensity": 0.50},
        {"name": "Bogadi Rd Junction",        "lat": 12.2850, "lon": 76.6220, "base_radius": 260,  "base_intensity": 0.45},
        {"name": "KR Hospital Area",          "lat": 12.3055, "lon": 76.6520, "base_radius": 300,  "base_intensity": 0.70},
        {"name": "Mysuru-Bengaluru NH",       "lat": 12.3650, "lon": 76.6050, "base_radius": 500,  "base_intensity": 0.65},
        {"name": "Ooty Rd Junction",          "lat": 12.2750, "lon": 76.6600, "base_radius": 340,  "base_intensity": 0.58},
    ]

    @classmethod
    def get_current_traffic_state(cls):
        """Returns the active congestion zone coordinates and current live traffic multiplier."""
        return {
            "zone": {
                "lat_min": cls.CITY_CENTER_LAT_MIN,
                "lat_max": cls.CITY_CENTER_LAT_MAX,
                "lon_min": cls.CITY_CENTER_LON_MIN,
                "lon_max": cls.CITY_CENTER_LON_MAX
            },
            "multiplier": cls.get_time_multiplier()
        }

    @classmethod
    def get_heatmap_zones(cls):
        """
        Returns a list of traffic hotspot zones for heatmap rendering.
        Each zone has a position, radius (metres), intensity (0-1), and a
        small time-jitter so the map feels alive between refreshes.
        """
        mult = cls.get_time_multiplier()
        hour = datetime.datetime.now().hour
        is_rush = (8 <= hour <= 10) or (17 <= hour <= 20)
        is_night = hour >= 23 or hour <= 6

        zones = []
        for z in cls.TRAFFIC_ZONES:
            # Scale intensity by time-of-day multiplier
            intensity = z["base_intensity"] * min(mult, 2.5) / 2.5
            if is_night:
                intensity *= 0.35          # very low at night
            elif is_rush and z["base_intensity"] >= 0.7:
                intensity = min(intensity * 1.4, 1.0)  # boost hotspots at rush hour

            # Small random jitter so the map feels live on each poll
            jitter = (random.random() - 0.5) * 0.06
            intensity = max(0.0, min(1.0, intensity + jitter))

            # Radius expands slightly at rush hour
            radius = z["base_radius"] * (1.0 + (0.3 if is_rush else 0.0))

            zones.append({
                "name":      z["name"],
                "lat":       z["lat"],
                "lon":       z["lon"],
                "radius":    int(radius),
                "intensity": round(intensity, 3),
            })

        return {
            "zones":      zones,
            "multiplier": mult,
            "hour":       hour,
            "is_rush":    is_rush,
            "is_night":   is_night,
        }

    @classmethod
    def get_time_multiplier(cls):
        """Returns a baseline traffic multiplier based strictly on the current hour."""
        current_hour = datetime.datetime.now().hour
        
        # Morning Rush: 08:00 - 10:00
        if 8 <= current_hour <= 10:
            return 1.8
        # Evening Rush: 17:00 - 20:00 (5 PM - 8 PM)
        elif 17 <= current_hour <= 20:
            return 2.2
        # Late Night / Early Morning: 23:00 - 06:00
        elif current_hour >= 23 or current_hour <= 6:
            return 0.75  # Roads are empty
        # Baseline / Mid-day:
        else:
            return 1.2
            
    @classmethod
    def analyze_route_congestion(cls, route_coords):
        """
        Analyzes a sequence of [lon, lat] coordinates to find what percentage 
        of the route passes through the congested city center.
        """
        if not route_coords:
            return 0.0
            
        points_in_center = 0
        for coord in route_coords:
            lon, lat = coord[0], coord[1] # OSRM returns [lon, lat]
            if (cls.CITY_CENTER_LAT_MIN <= lat <= cls.CITY_CENTER_LAT_MAX and 
                cls.CITY_CENTER_LON_MIN <= lon <= cls.CITY_CENTER_LON_MAX):
                points_in_center += 1
                
        # Returns a percentage between 0.0 and 1.0
        return points_in_center / len(route_coords)

    @classmethod
    def predict_fastest_route(cls, osrm_routes_data):
        """
        Takes raw OSRM routes payload (which has multiple paths if alternatives=true)
        and predicts the absolute fastest route adjusting for AI traffic heuristic.
        
        Returns: 
            best_route: the OSRM route object chosen
            predicted_eta_seconds: Integer ETA after ML prediction
            ai_rationale: Text description explaining the AI logic 
            waypoints: list of [lat, lon] coords for animation
        """
        if not osrm_routes_data:
            return None, 0, "Error: No routes to analyze", []

        base_time_multiplier = cls.get_time_multiplier()
        current_hour = datetime.datetime.now().hour
        
        best_route = None
        best_predicted_duration = float('inf')
        best_rationale = ""
        best_coords = []
        
        # Evaluate every route returned by OSRM
        for i, route in enumerate(osrm_routes_data):
            coords = route["geometry"]["coordinates"] # [lon, lat] pairs
            base_duration = route["duration"] # In seconds
            route_distance_km = route["distance"] / 1000.0
            
            # AI ML Heuristic logic:
            # 1. Start with the baseline hour multiplier
            route_multiplier = base_time_multiplier
            
            # 2. Add penalities for driving straight through downtown
            center_density_pct = cls.analyze_route_congestion(coords)
            
            # If during rush hour and route goes through center, exponentially increase multiplier
            if center_density_pct > 0.1 and (17 <= current_hour <= 20 or 8 <= current_hour <= 10):
                congestion_penalty = (center_density_pct * 3.0) # Up to +3.0x slower
                route_multiplier += congestion_penalty
                
            predicted_duration = base_duration * route_multiplier

            if predicted_duration < best_predicted_duration:
                best_predicted_duration = predicted_duration
                best_route = route
                
                # Formulate the rationale message
                if center_density_pct > 0.2 and route_multiplier > 2.0:
                    best_rationale = "AI chose alternative path to avoid heavy city center traffic delays."
                elif center_density_pct < 0.1 and route_multiplier < 1.0:
                    best_rationale = "AI confirmed fast nighttime straight-line route."
                else:
                    best_rationale = "AI selected optimal path based on moderate current traffic flow."
                    
                best_coords = [[c[1], c[0]] for c in coords] # Convert [lon,lat] to [lat,lon] for frontend

        return best_route, int(best_predicted_duration), best_rationale, best_coords
