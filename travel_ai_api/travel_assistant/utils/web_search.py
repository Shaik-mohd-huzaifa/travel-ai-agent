from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from datetime import datetime, timedelta
from .hotel_scraper import HotelScraper
from .flight_scraper import FlightScraper

class WebSearchClient:
    """
    Utility class for performing web searches to get travel-related information
    """
    def __init__(self):
        """Initialize the search clients"""
        self.ddgs = DDGS()
        self.hotel_scraper = HotelScraper()
        self.flight_scraper = FlightScraper()
    
    def search_travel_info(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for travel information using DuckDuckGo
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results as dictionaries
        """
        try:
            # Format the query to focus on travel information
            search_query = f"{query} travel information hotels flights"
            results = list(self.ddgs.text(search_query, max_results=max_results))
            return results
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []
    
    def search_hotel_info(self, 
                         location: str, 
                         check_in_date: Optional[datetime] = None,
                         check_out_date: Optional[datetime] = None,
                         adults: int = 2,
                         max_results: int = 5,
                         hotel_type: Optional[str] = None,
                         min_price: Optional[int] = None,
                         max_price: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for hotel information at a location using web scraping
        
        Args:
            location: The location to search hotels for
            check_in_date: Check-in date
            check_out_date: Check-out date
            adults: Number of adults
            max_results: Maximum number of results to return
            hotel_type: Type of accommodation (hotel, apartment, etc.)
            min_price: Minimum price per night
            max_price: Maximum price per night
            
        Returns:
            List of hotel search results
        """
        try:
            # First try to use the scraper
            hotels = self.hotel_scraper.search_hotels(
                location=location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                adults=adults,
                min_price=min_price,
                max_price=max_price,
                hotel_type=hotel_type
            )
            
            # If scraper fails or returns no results, fall back to DuckDuckGo
            if not hotels:
                search_query = f"best hotels in {location} accommodations"
                text_results = list(self.ddgs.text(search_query, max_results=max_results))
                return text_results
            
            # Limit the number of results
            return hotels[:max_results]
            
        except Exception as e:
            print(f"Hotel search error: {str(e)}")
            # Fall back to simple search
            search_query = f"best hotels in {location} accommodations"
            text_results = list(self.ddgs.text(search_query, max_results=max_results))
            return text_results
    
    def search_flight_info(self, 
                          origin: str, 
                          destination: str, 
                          departure_date: Optional[datetime] = None,
                          return_date: Optional[datetime] = None,
                          adults: int = 1,
                          max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for flight information between two locations using web scraping
        
        Args:
            origin: Origin location or airport code
            destination: Destination location or airport code
            departure_date: Departure date
            return_date: Return date (for round trips)
            adults: Number of adults
            max_results: Maximum number of results to return
            
        Returns:
            List of flight search results
        """
        try:
            # First try to use the scraper
            flights = self.flight_scraper.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults
            )
            
            # If scraper fails or returns no results, fall back to DuckDuckGo
            if not flights:
                search_query = f"flights from {origin} to {destination} prices"
                text_results = list(self.ddgs.text(search_query, max_results=max_results))
                return text_results
            
            # Limit the number of results
            return flights[:max_results]
            
        except Exception as e:
            print(f"Flight search error: {str(e)}")
            # Fall back to simple search
            search_query = f"flights from {origin} to {destination} prices"
            text_results = list(self.ddgs.text(search_query, max_results=max_results))
            return text_results
    
    def search_attractions(self, location: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for tourist attractions at a location
        
        Args:
            location: The location to search attractions for
            max_results: Maximum number of results to return
            
        Returns:
            List of attraction search results
        """
        try:
            search_query = f"best tourist attractions in {location} things to do"
            results = list(self.ddgs.text(search_query, max_results=max_results))
            return results
        except Exception as e:
            print(f"Attractions search error: {str(e)}")
            return []
            
    def get_hotel_details(self, hotel_url: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific hotel
        
        Args:
            hotel_url: URL to the hotel detail page
            
        Returns:
            Dictionary with detailed hotel information
        """
        try:
            return self.hotel_scraper.get_hotel_details(hotel_url)
        except Exception as e:
            print(f"Hotel details error: {str(e)}")
            return {'error': str(e)}
            
    def get_flight_details(self, 
                          origin: str, 
                          destination: str, 
                          flight_number: str, 
                          date: datetime) -> Dict[str, Any]:
        """
        Get detailed information about a specific flight
        
        Args:
            origin: Origin airport code
            destination: Destination airport code
            flight_number: Flight number
            date: Flight date
            
        Returns:
            Dictionary with detailed flight information
        """
        try:
            return self.flight_scraper.get_flight_details(origin, destination, flight_number, date)
        except Exception as e:
            print(f"Flight details error: {str(e)}")
            return {'error': str(e)}
