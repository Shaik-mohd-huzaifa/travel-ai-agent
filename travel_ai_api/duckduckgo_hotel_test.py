"""
Test script for the updated hotel search implementation which uses DuckDuckGo as the primary source.
"""

import logging
import json
from travel_assistant.utils.amadeus_trip_planner_tool import AmadeusTripPlannerTool

# Configure logging to show all details
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_trip_planning_with_duckduckgo_hotels():
    """Test trip planning with DuckDuckGo as the primary hotel source."""
    print("\n=== Testing Trip Planning with DuckDuckGo as Primary Hotel Source ===")
    
    planner = AmadeusTripPlannerTool()
    
    # Define some test queries with different destinations
    test_queries = [
        "I want to visit Paris from June 15 to June 22, 2025",
        "Plan a trip to Tokyo from July 10 to July 17, 2025",
        "I need to travel to Barcelona from August 5 to August 12, 2025"
    ]
    
    for query in test_queries:
        print(f"\nProcessing query: {query}")
        
        # Extract the destination from the query for easier logging
        destination = None
        if "Paris" in query:
            destination = "Paris"
        elif "Tokyo" in query:
            destination = "Tokyo"
        elif "Barcelona" in query:
            destination = "Barcelona"
        
        # Process the query
        result = planner.plan_trip(query)
        
        # Check hotels in the result
        if result.get("hotels"):
            print(f"✅ Found {len(result['hotels'])} hotel options for {destination}!")
            
            # Print a sample hotel
            hotel = result["hotels"][0]
            print("\nSample hotel:")
            print(f"  Name: {hotel.get('name', '')}")
            print(f"  Address: {hotel.get('address', '')}")
            print(f"  Rating: {hotel.get('rating', '')}")
            print(f"  Source: {hotel.get('source', '')}")
            
            # Check if sources are mentioned in suggestions
            source_suggestions = [s for s in result.get("suggestions", []) if "hotel" in s.lower() and "source" in s.lower()]
            if source_suggestions:
                print("\nSource Information in Suggestions:")
                for suggestion in source_suggestions:
                    print(f"  - {suggestion}")
        else:
            print(f"❌ No hotels found for {destination}!")
            
            # Print any suggestions
            if result.get("suggestions"):
                print("\nSuggestions:")
                for suggestion in result.get("suggestions", []):
                    if "hotel" in suggestion.lower():
                        print(f"  - {suggestion}")

if __name__ == "__main__":
    print("=== DuckDuckGo Hotel Search Test ===")
    test_trip_planning_with_duckduckgo_hotels()
    print("\n=== Test Complete ===")
