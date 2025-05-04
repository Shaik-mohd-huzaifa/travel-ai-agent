"""
Demo script for testing the Firecrawl API integration for activity search.

This script demonstrates how to use the FirecrawlAPIHandler to search for
activities, tourist attractions, and restaurants in a given location.
"""

import os
import json
from dotenv import load_dotenv
from travel_assistant.utils.firecrawl_api_handler import FirecrawlAPIHandler

# Load environment variables
load_dotenv()

def main():
    """Run the Firecrawl API demo."""
    print("Firecrawl API Demo for Activity Search")
    print("======================================")
    
    # Initialize the API handler
    try:
        firecrawl_handler = FirecrawlAPIHandler()
        print("✅ Successfully initialized Firecrawl API handler")
    except Exception as e:
        print(f"❌ Error initializing Firecrawl API handler: {e}")
        return
    
    # Test with one location to avoid hitting rate limits
    location = "London"
    
    print(f"\n🔍 Searching for activities in {location}...")
    
    # 1. Search for regular activities
    print(f"\n📍 Regular activities in {location}:")
    activities = firecrawl_handler.search_activities(location=location, limit=2)
    if activities:
        for i, activity in enumerate(activities, 1):
            print(f"  {i}. {activity['name']}")
            print(f"     Description: {activity['description'][:100]}...")
            print(f"     URL: {activity['url']}")
    else:
        print("  No activities found")
    
    # 2. Search for tourist attractions
    print(f"\n🏛️ Tourist attractions in {location}:")
    attractions = firecrawl_handler.search_tourist_attractions(location=location, limit=2)
    if attractions:
        for i, attraction in enumerate(attractions, 1):
            print(f"  {i}. {attraction['name']}")
            print(f"     Description: {attraction['description'][:100]}...")
            print(f"     URL: {attraction['url']}")
    else:
        print("  No attractions found")
    
    # 3. Search for restaurants
    print(f"\n🍽️ Restaurants in {location}:")
    restaurants = firecrawl_handler.search_restaurants(location=location, limit=2)
    if restaurants:
        for i, restaurant in enumerate(restaurants, 1):
            print(f"  {i}. {restaurant['name']}")
            print(f"     Description: {restaurant['description'][:100]}...")
            print(f"     URL: {restaurant['url']}")
    else:
        print("  No restaurants found")
    
    # Test with a specific activity type
    activity_type = "outdoor"
    
    print(f"\n🎯 {activity_type.title()} activities in {location}:")
    activities = firecrawl_handler.search_activities(
        location=location,
        activity_type=activity_type,
        limit=2
    )
    
    if activities:
        for i, activity in enumerate(activities, 1):
            print(f"  {i}. {activity['name']}")
            print(f"     Description: {activity['description'][:100]}...")
            print(f"     URL: {activity['url']}")
    else:
        print(f"  No {activity_type} activities found")
    
    print("\n✨ Firecrawl API Demo completed")

if __name__ == "__main__":
    main()
