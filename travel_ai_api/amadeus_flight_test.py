"""
Test script for debugging Amadeus flight search functionality.
"""

import logging
import os
from dotenv import load_dotenv
from travel_assistant.utils.amadeus_api_handler import AmadeusAPIHandler
from travel_assistant.utils.amadeus_trip_planner_tool import AmadeusTripPlannerTool

# Configure logging to show all details
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_flight_search_direct():
    """Test direct flight search with the AmadeusAPIHandler."""
    print("\n=== Testing Direct Flight Search with AmadeusAPIHandler ===")
    
    try:
        # Initialize the API handler
        handler = AmadeusAPIHandler()
        
        # Test parameters
        origin = "JFK"  # New York JFK
        destination = "LHR"  # London Heathrow
        departure_date = "2025-06-03"
        return_date = "2025-06-10"
        adults = 1
        
        print(f"Searching flights: {origin} to {destination} on {departure_date}")
        
        # Try to search flights
        results = handler.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            max_results=5
        )
        
        # Print results
        if results:
            print(f"✅ Found {len(results)} flight options!")
            for i, flight in enumerate(results[:2], 1):  # Show first 2 for brevity
                print(f"\nFlight {i}:")
                print(f"  Price: {flight.get('currency', '')} {flight.get('price', 0)}")
                print(f"  Segments: {len(flight.get('segments', []))}")
                for j, segment in enumerate(flight.get('segments', [])[:2], 1):  # Show first 2 segments
                    print(f"    Segment {j}: {segment.get('departure_airport')} - {segment.get('arrival_airport')}")
        else:
            print("❌ No flight results found!")
    
    except Exception as e:
        print(f"❌ Error during direct flight search: {e}")

def test_city_code_lookup():
    """Test IATA city code lookup."""
    print("\n=== Testing City Code Lookup ===")
    
    try:
        # Initialize the API handler
        handler = AmadeusAPIHandler()
        
        # Test cities
        cities = ["Tokyo", "New York", "London", "Paris", "Sydney"]
        
        for city in cities:
            code = handler.get_city_code(city)
            print(f"City: {city} -> Code: {code}")
    
    except Exception as e:
        print(f"❌ Error during city code lookup: {e}")

def test_trip_planner_query():
    """Test the full trip planner with a specific query."""
    print("\n=== Testing Full Trip Planner ===")
    
    try:
        # Initialize the trip planner
        planner = AmadeusTripPlannerTool()
        
        # Test query
        query = "I want to fly from New York to London from June 3 to June 10, 2025"
        
        print(f"Processing query: {query}")
        
        # Process the query
        trip_details = planner.extract_trip_details(query)
        print("\nExtracted Trip Details:")
        for key, value in trip_details.items():
            print(f"  {key}: {value}")
        
        # Plan the trip
        result = planner.plan_trip(query)
        
        # Check flights in the result
        if result.get("flights"):
            print(f"\n✅ Found {len(result['flights'])} flight options!")
        else:
            print("\n❌ No flights found in the result!")
            print(f"Suggestions: {result.get('suggestions', [])}")
        
        # Check if origin city was recognized
        if not trip_details.get("origin_city"):
            print("\n⚠️ Origin city was not extracted from the query!")
        
        # Print any error messages
        if "error" in result:
            print(f"\n❌ Error: {result['error']}")
    
    except Exception as e:
        print(f"❌ Error during trip planning: {e}")

if __name__ == "__main__":
    print("=== Amadeus Flight Search Test ===")
    test_flight_search_direct()
    test_city_code_lookup()
    test_trip_planner_query()
    print("\n=== Test Complete ===")
