"""
Full integration test for the Travel AI application with DuckDuckGo as the primary hotel source.
"""

import json
import requests
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_amadeus_agent_endpoint():
    """Test the AmadeusAgentAPIView endpoint with a sample query."""
    print("\n=== Testing the Amadeus Agent Endpoint ===")
    
    # Sample queries
    queries = [
        "I want to plan a trip to Paris from June 15 to June 22, 2025.",
        "Plan a luxury trip to Barcelona for a week in August 2025.",
        "I need a budget hotel in Tokyo for July 2025."
    ]
    
    for query in queries:
        print(f"\nSubmitting query: {query}")
        
        # Make the API request
        url = "http://localhost:8000/api/amadeus-agent/"
        data = {"message": query}
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            print(f"✅ API Response Status: {response.status_code}")
            print(f"Response from API:")
            
            # Get the text response
            text_response = result.get("response", "No response received")
            print(f"\n{text_response[:300]}..." if len(text_response) > 300 else f"\n{text_response}")
            
            # Check for raw data
            if "raw_data" in result:
                raw_data = result.get("raw_data", {})
                
                # Check for hotels
                hotels = raw_data.get("hotels", [])
                if hotels:
                    print(f"\nFound {len(hotels)} hotels:")
                    for i, hotel in enumerate(hotels[:2], 1):  # Show first 2 for brevity
                        print(f"  Hotel {i}: {hotel.get('name', '')} - Source: {hotel.get('source', '')}")
                else:
                    print("\nNo hotels found in the response.")
                
                # Check for activities
                activities = raw_data.get("activities", [])
                if activities:
                    print(f"Found {len(activities)} activities:")
                    for i, activity in enumerate(activities[:2], 1):  # Show first 2 for brevity
                        print(f"  Activity {i}: {activity.get('name', '')}")
                else:
                    print("No activities found in the response.")
            else:
                print("\nNo raw data found in the response.")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error making API request: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    print("=== Travel AI Integration Test with DuckDuckGo ===")
    test_amadeus_agent_endpoint()
    print("\n=== Test Complete ===")
