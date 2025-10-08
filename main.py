# main.py - Your primary flight checker script.

from display import get_display
from image_generator import generate_display_image
import os
import math
import time
from FlightRadar24 import FlightRadar24API
from datetime import datetime


# --- Configuration ---
SAVE_FOLDER = "simulated_displays"
# Define your home location and search radius in kilometers
HOME_LAT = 51.487077
HOME_LON = -0.217605
SEARCH_RADIUS_KM = 3  # Search within a 20km radius


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the earth.
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    r = 6371  # Radius of earth in kilometers.
    return c * r


def find_closest_flight(api):
    """
    Finds the closest flight to the home location.
    """
    bounds = api.get_bounds_by_point(
        HOME_LAT, HOME_LON, SEARCH_RADIUS_KM * 1000
    )  # API uses metres
    flights = api.get_flights(bounds=bounds)
    print(f"Found {len(flights)} aircraft in the area. Finding the closest...")

    closest_flight = None
    min_distance = float("inf")

    for flight in flights:
        # Ensure flight has valid data and is not on the ground
        if flight.latitude and flight.longitude and flight.altitude < 5000:
            dist = haversine(HOME_LAT, HOME_LON, flight.latitude, flight.longitude)
            if dist < min_distance and dist < SEARCH_RADIUS_KM:
                min_distance = dist
                closest_flight = flight

    if closest_flight:
        print(
            f"Closest flight is {closest_flight.callsign} at {min_distance:.2f} km away."
        )
        return api.get_flight_details(closest_flight)
    else:
        print("No suitable flights found overhead right now.")
        return None


def main():
    """
    Main application loop. Fetches flight data and displays it.
    """

    display = get_display()
    fr_api = FlightRadar24API()

    flight_details = find_closest_flight(fr_api)

    if not flight_details:
        return

    # --- Extract and Format Data for Display ---
    flight_number = (
        flight_details.get("identification", {}).get("number", {}).get("default")
    )
    callsign = flight_details.get("identification", {}).get("callsign")

    airline = flight_details.get("airline", {}).get("name")
    aircraft = flight_details.get("aircraft", {}).get("model", {}).get("text")
    aircraft = (
        aircraft.replace("Airbus", "")
        .replace("Boeing ", "B")
        .replace("Dreamliner", "DL")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )

    origin_airport = flight_details.get("airport", {}).get("origin", {}).get("name")
    origin_code = (
        flight_details.get("airport", {}).get("origin", {}).get("code", {}).get("iata")
    )
    origin_city = (
        flight_details.get("airport", {})
        .get("origin", {})
        .get("position", {})
        .get("region", {})
        .get("city")
    )

    dest_airport = flight_details.get("airport", {}).get("destination", {}).get("name")
    dest_code = (
        flight_details.get("airport", {})
        .get("destination", {})
        .get("code", {})
        .get("iata")
    )
    dest_city = (
        flight_details.get("airport", {})
        .get("destination", {})
        .get("position", {})
        .get("region", {})
        .get("city")
    )

    scheduled_arrival_ts = (
        flight_details.get("time", {}).get("scheduled", {}).get("arrival")
    )
    estimated_arrival_ts = (
        flight_details.get("time", {}).get("estimated", {}).get("arrival")
    )
    altitude = flight_details.get("trail", [{}])[0].get("alt")

    print("\n" + "=" * 30)
    print(f"Processing flight: {flight_number} at {altitude} feet.")
    print(f"  Callsign: {callsign or 'N/A'}")
    print(f"  Airline: {airline or 'N/A'}")
    print(f"  Aircraft: {aircraft or 'N/A'}")
    print(
        f"  Origin: {origin_airport or 'N/A'} ({origin_code or 'N/A'}), {origin_city or 'N/A'}"
    )
    print(
        f"  Destination: {dest_airport or 'N/A'
        } ({dest_code or 'N/A'}), {dest_city or 'N/A'}"
    )
    if scheduled_arrival_ts:
        print(
            f"  Scheduled Arrival: {datetime.fromtimestamp(scheduled_arrival_ts).strftime('%H:%M:%S on %d-%b-%Y')}"
        )
    if estimated_arrival_ts:
        print(
            f"  Estimated Arrival: {datetime.fromtimestamp(estimated_arrival_ts).strftime('%H:%M:%S on %d-%b-%Y')}"
        )

    # --- Generate the Image ---
    image_frames = generate_display_image(
        flight_number=flight_number.upper(),
        origin_code=origin_code.upper(),
        aircraft_type=aircraft.upper(),
        origin_city=origin_city.upper(),
        time_difference_seconds=estimated_arrival_ts - scheduled_arrival_ts,
    )

    # --- Show the Image (Simulator or Physical Matrix) ---
    if image_frames:
        os.makedirs(SAVE_FOLDER, exist_ok=True)
        filename = f"{flight_number.replace('/', '_')}.png"  # Ensure filename is valid
        full_path = os.path.join(SAVE_FOLDER, filename)
        display.show(image_frames, path=full_path)

    print("Display updated.")


if __name__ == "__main__":
    main()
