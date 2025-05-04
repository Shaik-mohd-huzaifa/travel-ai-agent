#!/usr/bin/env python
"""
Travel Scraper CLI

A command-line tool to scrape hotel and flight information from multiple sites.
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_ai_project.settings')

# Import Django and initialize it
import django
django.setup()

# Now we can import our scraper utilities
from travel_assistant.utils.hotel_scraper import HotelScraper
from travel_assistant.utils.flight_scraper import FlightScraper


def format_date(date_str):
    """Format date string to YYYY-MM-DD or use today/tomorrow keywords"""
    if date_str.lower() == 'today':
        return datetime.now().strftime('%Y-%m-%d')
    elif date_str.lower() == 'tomorrow':
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            try:
                date_obj = datetime.strptime(date_str, '%d-%m-%Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD or 'today'/'tomorrow'")
                sys.exit(1)


def search_hotels(args):
    """Search for hotels across multiple sites"""
    # Validate and format dates
    check_in = format_date(args.check_in)
    check_out = format_date(args.check_out)
    
    # Create a scraper and search
    print(f"Searching for hotels in {args.location} from {check_in} to {check_out}...")
    scraper = HotelScraper()
    results = scraper.search_hotels_all_sites(
        location=args.location,
        check_in=check_in,
        check_out=check_out,
        guests=args.guests,
        rooms=args.rooms
    )
    
    # Print results
    if args.format == 'json':
        print(json.dumps(results, indent=2))
    else:
        print("\n=== HOTEL SEARCH RESULTS ===")
        for site, hotels in results.items():
            print(f"\n{site.upper()} TOP RESULTS:")
            if not hotels:
                print("  No results found")
                continue
                
            for i, hotel in enumerate(hotels, 1):
                print(f"{i}. {hotel.get('name', 'Unknown')} - {'${:.2f}'.format(hotel['price']) if hotel.get('price') else 'Price N/A'}")
                print(f"   Rating: {hotel.get('rating', 'N/A')} | URL: {hotel.get('url', 'N/A')}")


def search_flights(args):
    """Search for flights across multiple sites"""
    # Validate and format dates
    date = format_date(args.date)
    return_date = format_date(args.return_date) if args.return_date else None
    
    # Create a scraper and search
    print(f"Searching for flights from {args.origin} to {args.destination} on {date}...")
    scraper = FlightScraper()
    results = scraper.search_flights_all_sites(
        origin=args.origin,
        destination=args.destination,
        date=date,
        return_date=return_date,
        adults=args.adults
    )
    
    # Print results
    if args.format == 'json':
        print(json.dumps(results, indent=2))
    else:
        print("\n=== FLIGHT SEARCH RESULTS ===")
        for site, flights in results.items():
            print(f"\n{site.upper()} TOP RESULTS:")
            if not flights:
                print("  No results found")
                continue
                
            for i, flight in enumerate(flights, 1):
                print(f"{i}. {flight.get('airline', 'Unknown')} - {'${:.2f}'.format(flight['price']) if flight.get('price') else 'Price N/A'}")
                print(f"   Duration: {flight.get('duration', 'N/A')} | Stops: {flight.get('stops', 'N/A')}")
                if 'times' in flight:
                    print(f"   Times: {flight.get('times', 'N/A')}")
                elif 'departure_time' in flight and 'arrival_time' in flight:
                    print(f"   Departure: {flight.get('departure_time', 'N/A')} | Arrival: {flight.get('arrival_time', 'N/A')}")


def main():
    """Main entry point for the CLI tool"""
    parser = argparse.ArgumentParser(description='Travel Scraper CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Hotel search parser
    hotel_parser = subparsers.add_parser('hotels', help='Search for hotels')
    hotel_parser.add_argument('--location', required=True, help='Destination city or area')
    hotel_parser.add_argument('--check-in', required=True, help='Check-in date (YYYY-MM-DD or "today"/"tomorrow")')
    hotel_parser.add_argument('--check-out', required=True, help='Check-out date (YYYY-MM-DD or "today"/"tomorrow")')
    hotel_parser.add_argument('--guests', type=int, default=2, help='Number of guests')
    hotel_parser.add_argument('--rooms', type=int, default=1, help='Number of rooms')
    hotel_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Flight search parser
    flight_parser = subparsers.add_parser('flights', help='Search for flights')
    flight_parser.add_argument('--origin', required=True, help='Origin airport code')
    flight_parser.add_argument('--destination', required=True, help='Destination airport code')
    flight_parser.add_argument('--date', required=True, help='Departure date (YYYY-MM-DD or "today"/"tomorrow")')
    flight_parser.add_argument('--return-date', help='Return date (YYYY-MM-DD or "today"/"tomorrow")')
    flight_parser.add_argument('--adults', type=int, default=1, help='Number of adult passengers')
    flight_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    if args.command == 'hotels':
        search_hotels(args)
    elif args.command == 'flights':
        search_flights(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
