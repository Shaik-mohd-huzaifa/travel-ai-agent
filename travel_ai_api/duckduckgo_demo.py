"""
Demo script for testing the DuckDuckGo Activity Search implementation.

This script demonstrates how to use the DuckDuckGoActivitySearch class
to find activities in different locations by searching DuckDuckGo,
scraping content from top results, and extracting structured information
using OpenAI's GPT-4o model.
"""

import json
import os
from dotenv import load_dotenv
from travel_assistant.utils.duckduckgo_activity_search import DuckDuckGoActivitySearch

# Load environment variables
load_dotenv()

def main():
    """Run the DuckDuckGo activity search demo."""
    print("DuckDuckGo Activity Search Demo")
    print("===============================")
    
    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY is not set in environment variables")
        return
    
    # Initialize the activity search
    try:
        activity_search = DuckDuckGoActivitySearch()
        print("✅ Successfully initialized DuckDuckGo Activity Search")
    except Exception as e:
        print(f"❌ Error initializing DuckDuckGo Activity Search: {e}")
        return
    
    # Test locations and activity types
    test_cases = [
        {"location": "Paris", "activity_type": "cultural"},
        {"location": "Tokyo", "activity_type": None},
        {"location": "London", "activity_type": "outdoor"}
    ]
    
    for test_case in test_cases:
        location = test_case["location"]
        activity_type = test_case["activity_type"]
        
        print(f"\n\n🔍 Searching for", end=" ")
        if activity_type:
            print(f"{activity_type}", end=" ")
        print(f"activities in {location}...")
        
        # Search for activities
        activities = activity_search.search_activities(
            location=location,
            activity_type=activity_type,
            limit=3
        )
        
        if activities:
            print(f"\n✨ Found {len(activities)} activities in {location}:")
            
            for i, activity in enumerate(activities, 1):
                print(f"\n{i}. {activity.get('name', 'Unnamed Activity')}")
                print(f"   Description: {activity.get('description', 'No description')[:150]}...")
                
                if activity.get('highlights'):
                    print(f"   Highlights: {', '.join(activity['highlights'][:3])}")
                
                print(f"   Rating: {activity.get('rating', 'N/A')}")
                print(f"   Price Range: {activity.get('price_range', 'N/A')}")
                print(f"   Location: {activity.get('location', location)}")
                
            # Save results to a JSON file
            filename = f"{location.lower()}_activities.json"
            with open(filename, 'w') as f:
                json.dump(activities, f, indent=2)
            print(f"\n📄 Saved results to {filename}")
            
        else:
            print(f"❌ No activities found for {location}")
    
    print("\n🎉 DuckDuckGo Activity Search Demo completed!")

if __name__ == "__main__":
    main()
