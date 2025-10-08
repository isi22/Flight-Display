# flight_tracker.py
# Main script to find overhead flights, print details, and generate display images.

import math  # <-- ADDED: For distance calculation
from FlightRadar24 import FlightRadar24API
from datetime import datetime
from old.dot_matrix_simulator import generate_display_image


# --- ADDED: Haversine function to calculate distance between two GPS coordinates ---
def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the earth (specified in decimal degrees).
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    r = 6371  # Radius of earth in kilometers.
    return c * r


def find_and_display_flights():
    """
    Finds nearby flights, selects the closest one, prints its details,
    and generates a display image.
    """
    IMAGE_SAVE_PATH = "flight_images"

    # Define your center point
    CENTER_LAT = 51.487077
    CENTER_LON = -0.217605
    SEARCH_RADIUS = 3000

    fr_api = FlightRadar24API()
    bounds = fr_api.get_bounds_by_point(CENTER_LAT, CENTER_LON, SEARCH_RADIUS)
    flights = fr_api.get_flights(bounds=bounds)
    print(
        f"Found {len(flights)} aircraft in the specified area. Finding the closest one..."
    )

    if not flights:
        print("No flights found overhead at the moment.")
        return

    # --- MODIFIED: Find the single closest flight ---
    closest_flight = None
    min_distance = float("inf")

    for flight in flights:
        # Check if flight has valid coordinates
        if (
            flight.latitude
            and flight.longitude
            and flight.number
            and flight.altitude < 5000
        ):
            dist = haversine(CENTER_LAT, CENTER_LON, flight.latitude, flight.longitude)
            if dist < min_distance:
                min_distance = dist
                closest_flight = flight

    # --- MODIFIED: Process ONLY the closest flight that was found ---
    if closest_flight:
        print(
            f"\nClosest flight is {closest_flight.callsign or closest_flight.registration} at {min_distance:.2f} km away."
        )
        try:
            flight_details = fr_api.get_flight_details(closest_flight)
            flight_number = (
                flight_details.get("identification", {})
                .get("number", {})
                .get("default")
            )
            altitude = flight_details.get("trail", [{}])[0].get("alt")
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
            origin_city = (
                flight_details.get("airport", {})
                .get("origin", {})
                .get("position", {})
                .get("region", {})
                .get("city")
            )
            origin_code = (
                flight_details.get("airport", {})
                .get("origin", {})
                .get("code", {})
                .get("iata")
            )

            print("\n" + "=" * 30)
            print(f"Processing flight: {flight_number} at {altitude} feet.")

            # Terminal printing logic
            callsign = flight_details.get("identification", {}).get("callsign")
            dest_airport = (
                flight_details.get("airport", {}).get("destination", {}).get("name")
            )
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
            origin_airport = (
                flight_details.get("airport", {}).get("origin", {}).get("name")
            )
            scheduled_arrival_ts = (
                flight_details.get("time", {}).get("scheduled", {}).get("arrival")
            )
            estimated_arrival_ts = (
                flight_details.get("time", {}).get("estimated", {}).get("arrival")
            )

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

            # Image generation
            if all([aircraft, origin_code, origin_city]):
                print("\n  -> Generating display image...")
                generate_display_image(
                    flight_number=flight_number.upper(),
                    origin_code=origin_code.upper(),
                    aircraft_type=aircraft.upper(),
                    origin_city=origin_city.upper(),
                    time_difference_seconds=estimated_arrival_ts - scheduled_arrival_ts,
                    save_path=IMAGE_SAVE_PATH,
                )
            else:
                print("\n  -> Skipping display image due to missing data.")

            print("=" * 30)

        except Exception as e:
            print(f"An error occurred while processing the closest flight: {e}")
    else:
        print("Could not determine the closest flight.")


if __name__ == "__main__":
    find_and_display_flights()
