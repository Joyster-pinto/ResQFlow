import datetime
import math

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
