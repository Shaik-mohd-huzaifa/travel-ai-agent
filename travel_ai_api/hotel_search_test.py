"""
Test script for comparing Amadeus API and DuckDuckGo hotel search results
and demonstrating the fallback mechanism.
"""

import logging
import os
from dotenv import load_dotenv
from travel_assistant.utils.amadeus_api_handler import AmadeusAPIHandler
from travel_assistant.utils.duckduckgo_hotel_search import DuckDuckGoHotelSearch
from travel_assistant.utils.amadeus_trip_planner_tool import AmadeusTripPlannerTool

# Configure logging to show all details
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_amadeus_hotel_search():
    """Test Amadeus API hotel search directly."""
    print("\n=== Testing Amadeus API Hotel Search ===")
    
    handler = AmadeusAPIHandler()
    
    # Test parameters
    city_code = "PAR"  # Paris
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
        print(f"✅ Found {len(results)} hotel options with Amadeus API!")
        for i, hotel in enumerate(results, 1):
            print(f"\nHotel {i}:")
            print(f"  Name: {hotel.get('name', '')}")
            print(f"  Address: {hotel.get('address', '')}")
            print(f"  Price: {hotel.get('currency', '')} {hotel.get('price', 0)}")
            if 'amenities' in hotel and hotel['amenities']:
                print(f"  Amenities: {', '.join(hotel.get('amenities', []))}")
    else:
        print("❌ No hotel results found with Amadeus API!")

def test_duckduckgo_hotel_search():
    """Test DuckDuckGo hotel search directly."""
    print("\n=== Testing DuckDuckGo Hotel Search ===")
    
    handler = DuckDuckGoHotelSearch()
    
    # Test parameters
    city = "Paris"
    check_in_date = "2025-06-15"
    check_out_date = "2025-06-22"
    budget_level = "moderate"
    
    print(f"Searching hotels in {city} from {check_in_date} to {check_out_date} with budget level: {budget_level}")
    
    # Try to search hotels
    results = handler.search_hotels(
        city=city,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        budget_level=budget_level,
        max_results=3
    )
    
    # Print results
    if results:
        print(f"✅ Found {len(results)} hotel options with DuckDuckGo!")
        for i, hotel in enumerate(results, 1):
            print(f"\nHotel {i}:")
            print(f"  Name: {hotel.get('name', '')}")
            print(f"  Address: {hotel.get('address', '')}")
            print(f"  Price: {hotel.get('price', '')}")
            print(f"  Rating: {hotel.get('rating', '')}")
            if hotel.get('amenities'):
                print(f"  Amenities: {', '.join(hotel.get('amenities', []))}")
    else:
        print("❌ No hotel results found with DuckDuckGo!")

def test_integrated_search():
    """Test the integrated hotel search with fallback mechanism."""
    print("\n=== Testing Integrated Hotel Search (with Fallback) ===")
    
    planner = AmadeusTripPlannerTool()
    
    # Test query
    query = "I want to visit Paris from June 15 to June 22, 2025"
    
    print(f"Processing query: {query}")
    
    # Process the query
    result = planner.plan_trip(query)
    
    # Check hotels in the result
    if result.get("hotels"):
        print(f"\n✅ Found {len(result['hotels'])} hotel options in total!")
        
        # Count hotels by source
        amadeus_hotels = [h for h in result['hotels'] if h.get('source') == 'Amadeus API']
        web_hotels = [h for h in result['hotels'] if h.get('source') == 'DuckDuckGo Web Search']
        
        print(f"  - Amadeus API: {len(amadeus_hotels)} hotels")
        print(f"  - Web Search: {len(web_hotels)} hotels")
        
        # Show a sample from each source
        if amadeus_hotels:
            print("\nSample Amadeus API hotel:")
            hotel = amadeus_hotels[0]
            print(f"  Name: {hotel.get('name', '')}")
            print(f"  Price: {hotel.get('currency', '')} {hotel.get('price', 0)}")
        
        if web_hotels:
            print("\nSample Web Search hotel:")
            hotel = web_hotels[0]
            print(f"  Name: {hotel.get('name', '')}")
            print(f"  Price: {hotel.get('price', '')}")
    else:
        print("❌ No hotels found in the result!")
    
    # Print any suggestions
    if result.get("suggestions"):
        print("\nSuggestions:")
        for suggestion in result["suggestions"]:
            print(f"  - {suggestion}")

if __name__ == "__main__":
    print("=== Hotel Search Integration Test ===")
    test_amadeus_hotel_search()
    test_duckduckgo_hotel_search()
    test_integrated_search()
    print("\n=== Test Complete ===")
