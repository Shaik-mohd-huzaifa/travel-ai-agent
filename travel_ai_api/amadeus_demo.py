#!/usr/bin/env python
"""
Demo script to show how to use the Amadeus API handler to fetch flight and hotel details.
Before running this script:
1. Set up your Amadeus API credentials in the .env file
2. Install required packages with: pip install -r requirements.txt
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from travel_assistant.utils.amadeus_api_handler import AmadeusAPIHandler

# Load environment variables
load_dotenv()

def main():
    # Check if Amadeus API credentials are set
    if not os.getenv('AMADEUS_API_KEY') or not os.getenv('AMADEUS_API_SECRET'):
        print("Error: Amadeus API credentials not found in .env file")
        print("Please set AMADEUS_API_KEY and AMADEUS_API_SECRET in your .env file")
        return
    
    # Initialize the Amadeus API handler
    amadeus = AmadeusAPIHandler()
    
    # Example: Get IATA city code for a city
    origin_city = "New York"
    destination_city = "London"
    
    origin_code = amadeus.get_city_code(origin_city)
    if not origin_code:
        print(f"Could not find IATA code for {origin_city}")
        origin_code = "NYC"  # Default fallback
    
    destination_code = amadeus.get_city_code(destination_city)
    if not destination_code:
        print(f"Could not find IATA code for {destination_city}")
        destination_code = "LON"  # Default fallback
    
    # Example: Search for flights
    # Use dates starting from tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    departure_date = tomorrow.strftime("%Y-%m-%d")
    return_date = (tomorrow + timedelta(days=7)).strftime("%Y-%m-%d")
    
    print(f"\nSearching flights from {origin_city} ({origin_code}) to {destination_city} ({destination_code})")
    print(f"Departure: {departure_date}, Return: {return_date}")
    
    flights = amadeus.search_flights(
        origin=origin_code,
        destination=destination_code,
        departure_date=departure_date,
        return_date=return_date,
        adults=1,
        max_results=3
    )
    
    # Display flight results
    if flights:
        print(f"\nFound {len(flights)} flights:")
        for i, flight in enumerate(flights, 1):
            print(f"\nFlight {i}:")
            print(f"  Price: {flight['currency']} {flight['price']}")
            print("  Segments:")
            for j, segment in enumerate(flight['segments'], 1):
                print(f"    Segment {j}: {segment['departure_airport']} → {segment['arrival_airport']}")
                print(f"      Departure: {segment['departure_time']}")
                print(f"      Arrival: {segment['arrival_time']}")
                print(f"      Flight: {segment['flight_number']}")
    else:
        print("No flights found or API error occurred")
    
    # Example: Search for hotels
    print(f"\nSearching hotels in {destination_city} ({destination_code})")
    print(f"Check-in: {departure_date}, Check-out: {return_date}")
    
    hotels = amadeus.search_hotels(
        city_code=destination_code,
        check_in_date=departure_date,
        check_out_date=return_date,
        adults=1,
        rooms=1,
        max_results=3
    )
    
    # Display hotel results
    if hotels:
        print(f"\nFound {len(hotels)} hotels:")
        for i, hotel in enumerate(hotels, 1):
            print(f"\nHotel {i}: {hotel['name']}")
            print(f"  Rating: {hotel.get('rating', 'N/A')}")
            print(f"  Address: {hotel['address']}")
            print(f"  Room type: {hotel.get('room_type', 'Standard')}")
            print(f"  Price: {hotel['currency']} {hotel['price']} ({hotel.get('board_type', 'Room only')})")
    else:
        print("No hotels found or API error occurred")

if __name__ == "__main__":
    main()
