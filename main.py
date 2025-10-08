# main.py - Your primary flight checker script.

from display import get_display
from image_generator import generate_display_image
import math
import time
from FlightRadar24 import FlightRadar24API
from datetime import datetime


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


def find_closest_flight(fr_api, lat, lon, radius, max_altitude):
    """
    Finds the closest flight to the home location.
    """
    bounds = fr_api.get_bounds_by_point(lat, lon, radius)  # API uses metres
    flights = fr_api.get_flights(bounds=bounds)
    print(f"Found {len(flights)} aircraft in the area.")

    if flights:
        print("Finding the closest...")
        closest_flight = None
        min_distance = float("inf")

        for flight in flights:
            # Ensure flight has valid data and is not on the ground
            if flight.latitude and flight.longitude and flight.altitude < max_altitude:
                dist = haversine(lat, lon, flight.latitude, flight.longitude)
                if dist < min_distance:
                    min_distance = dist
                    closest_flight = flight

        print(
            f"Closest flight is {closest_flight.callsign} at {min_distance:.2f} km away."
        )
        return fr_api.get_flight_details(closest_flight)

    else:
        return None


def main():
    """
    Main application loop. Fetches flight data and displays it.
    """

    # --- Configuration ---
    # Define your home location and search radius in kilometers
    HOME_LAT = 51.487077
    HOME_LON = -0.217605
    SEARCH_RADIUS_KM = 3  # Search within a 20km radius
    MAX_ALTITUDE_FT = 5000  # Only consider flights below this altitude
    REFRESH_INTERVAL_SECONDS = 5
    API_TIMEOUT = 1

    display = get_display()
    fr_api = FlightRadar24API(timeout=API_TIMEOUT)

    while True:
        cycle_start_time = time.time()
        print("\n" + "=" * 30)
        print(f"Searching for flights... ({datetime.now().strftime('%H:%M:%S')})")

        find_api_start_time = time.time()
        flight_details = find_closest_flight(
            fr_api, HOME_LAT, HOME_LON, SEARCH_RADIUS_KM * 1000, MAX_ALTITUDE_FT
        )
        find_api_time = time.time()

        if flight_details:
            try:
                # --- Extract and Format Data for Display ---
                flight_data = {
                    "flight_number": flight_details.get("identification", {})
                    .get("number", {})
                    .get("default"),
                    "callsign": flight_details.get("identification", {}).get(
                        "callsign"
                    ),
                    "airline": flight_details.get("airline", {}).get("name"),
                    "aircraft": flight_details.get("aircraft", {})
                    .get("model", {})
                    .get("text"),
                    "origin_airport": flight_details.get("airport", {})
                    .get("origin", {})
                    .get("name"),
                    "origin_code": flight_details.get("airport", {})
                    .get("origin", {})
                    .get("code", {})
                    .get("iata"),
                    "origin_city": flight_details.get("airport", {})
                    .get("origin", {})
                    .get("position", {})
                    .get("region", {})
                    .get("city"),
                    "dest_airport": flight_details.get("airport", {})
                    .get("destination", {})
                    .get("name"),
                    "dest_code": flight_details.get("airport", {})
                    .get("destination", {})
                    .get("code", {})
                    .get("iata"),
                    "dest_city": flight_details.get("airport", {})
                    .get("destination", {})
                    .get("position", {})
                    .get("region", {})
                    .get("city"),
                    "scheduled_arrival": flight_details.get("time", {})
                    .get("scheduled", {})
                    .get("arrival"),
                    "estimated_arrival": flight_details.get("time", {})
                    .get("estimated", {})
                    .get("arrival"),
                    "altitude": flight_details.get("trail", [{}])[0].get("alt"),
                }

                flight_data["aircraft"] = (
                    flight_data["aircraft"]
                    .replace("Airbus", "")
                    .replace("Boeing ", "B")
                    .replace("Dreamliner", "DL")
                    .replace("(", "")
                    .replace(")", "")
                    .strip()
                )

                print(f"Displaying data for: {flight_data['flight_number']}")
                print(f"  Callsign: {flight_data['callsign'] or 'N/A'}")
                print(f"  Airline: {flight_data['airline'] or 'N/A'}")
                print(f"  Aircraft: {flight_data['aircraft'] or 'N/A'}")
                print(
                    f"  Origin: {flight_data['origin_airport'] or 'N/A'} ({flight_data['origin_code'] or 'N/A'}), {flight_data['origin_city'] or 'N/A'}"
                )
                print(
                    f"  Destination: {flight_data['dest_airport'] or 'N/A'
                    } ({flight_data['dest_code'] or 'N/A'}), {flight_data['dest_city'] or 'N/A'}"
                )
                print(
                    f"  Scheduled Arrival: {datetime.fromtimestamp(flight_data['scheduled_arrival']).strftime('%H:%M:%S on %d-%b-%Y')}"
                )
                print(
                    f"  Estimated Arrival: {datetime.fromtimestamp(flight_data['estimated_arrival']).strftime('%H:%M:%S on %d-%b-%Y')}"
                )

                # --- Generate the Image ---
                image_gen_start_time = time.time()
                image_frames = generate_display_image(
                    flight_number=flight_data["flight_number"].upper(),
                    origin_code=flight_data["origin_code"].upper(),
                    aircraft_type=flight_data["aircraft"].upper(),
                    origin_city=flight_data["origin_city"].upper(),
                    time_difference_seconds=flight_data["estimated_arrival"]
                    - flight_data["scheduled_arrival"],
                )
                image_gen_time = time.time()

                # --- Show the Image (Simulator or Physical Matrix) ---
                display_start_time = time.time()
                display.show(image_frames, flight_data=flight_data)
                display_time = time.time()

                print("\n--- Performance ---")
                print(
                    f"  Find Flights API:    {find_api_time - find_api_start_time:.2f}s"
                )
                print(
                    f"  Image Generation:    {image_gen_time - image_gen_start_time:.2f}s"
                )
                print(
                    f"  Display Time:        {display_time - display_start_time:.2f}s"
                )

            except Exception as e:
                print(f"Error processing flight details: {e}")
        else:
            print("No suitable flights found nearby. Clearing display.")
            display.clear()

        total_processing_time = time.time() - cycle_start_time
        print(f"  Total Cycle Time:    {total_processing_time:.2f}s")

        print(f"Waiting for {REFRESH_INTERVAL_SECONDS} seconds...")
        time.sleep(REFRESH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
