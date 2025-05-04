"""
Test script for verifying the improved Amadeus API integration.
"""

import logging
import os
from dotenv import load_dotenv
from travel_assistant.utils.amadeus_api_handler import AmadeusAPIHandler

# Configure logging to show all details
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_city_code_lookup():
    """Test improved city code lookup function."""
    print("\n=== Testing Improved City Code Lookup ===")
    
    handler = AmadeusAPIHandler()
    
    # Test a variety of cities
    cities = ["Tokyo", "New York", "London", "Paris", "Sydney", "Bangkok", "Dubai", "Berlin", "Moscow"]
    
    for city in cities:
        code = handler.get_city_code(city)
        print(f"City: {city} -> Code: {code}")

def test_flight_search():
    """Test improved flight search functionality."""
    print("\n=== Testing Improved Flight Search ===")
    
    handler = AmadeusAPIHandler()
    
    # Test parameters
    origin = "NYC"  # New York
    destination = "LON"  # London
    departure_date = "2025-06-15"
    return_date = "2025-06-22"
    
    print(f"Searching flights: {origin} to {destination} on {departure_date}")
    
    # Try to search flights
    results = handler.search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=1,
        max_results=3
    )
    
    # Print results
    if results:
        print(f"✅ Found {len(results)} flight options!")
        for i, flight in enumerate(results[:2], 1):  # Show first 2 for brevity
            print(f"\nFlight {i}:")
            print(f"  Price: {flight.get('currency', '')} {flight.get('price', 0)}")
            print(f"  Duration: {flight.get('total_duration', '')}")
            print(f"  Cabin: {flight.get('cabin_class', '')}")
            print(f"  Segments: {len(flight.get('segments', []))}")
            for j, segment in enumerate(flight.get('segments', [])[:2], 1):  # Show first 2 segments
                print(f"    Segment {j}: {segment.get('departure_airport')} {segment.get('departure_time')} - {segment.get('arrival_airport')} {segment.get('arrival_time')}")
    else:
        print("❌ No flight results found!")

def test_hotel_search():
    """Test improved hotel search functionality."""
    print("\n=== Testing Improved Hotel Search ===")
    
    handler = AmadeusAPIHandler()
    
    # Test parameters
    city_code = "LON"  # London
    check_in_date = "2025-06-15"
    check_out_date = "2025-06-22"
    
    print(f"Searching hotels in {city_code} from {check_in_date} to {check_out_date}")
    
    # Try to search hotels
    results = handler.search_hotels(
        city_code=city_code,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        adults=2,
        max_results=3
    )
    
    # Print results
    if results:
        print(f"✅ Found {len(results)} hotel options!")
        for i, hotel in enumerate(results[:3], 1):
            print(f"\nHotel {i}:")
            print(f"  Name: {hotel.get('name', '')}")
            print(f"  Address: {hotel.get('address', '')}")
            print(f"  Price: {hotel.get('currency', '')} {hotel.get('price', 0)}")
            print(f"  Room Type: {hotel.get('room_type', '')}")
            print(f"  Cancellation: {hotel.get('cancellation_policy', '')}")
            if hotel.get('amenities'):
                print(f"  Amenities: {', '.join(hotel.get('amenities', []))}")
    else:
        print("❌ No hotel results found!")

if __name__ == "__main__":
    print("=== Amadeus Improved API Test ===")
    test_city_code_lookup()
    test_flight_search()
    test_hotel_search()
    print("\n=== Test Complete ===")
