"""
Amadeus Trip Planner Tool

This module provides a tool that agents can use to process user queries about trip planning
and return relevant flight and hotel information using the Amadeus API.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dotenv import load_dotenv
import os
from travel_assistant.utils.amadeus_api_handler import AmadeusAPIHandler
from travel_assistant.utils.firecrawl_api_handler import FirecrawlAPIHandler
from travel_assistant.utils.duckduckgo_activity_search import DuckDuckGoActivitySearch
from travel_assistant.utils.duckduckgo_hotel_search import DuckDuckGoHotelSearch

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AmadeusTripPlannerTool:
    """
    A tool for processing natural language trip planning queries and fetching
    relevant flight and hotel information using the Amadeus API.
    """
    
    def __init__(self):
        """Initialize the AmadeusTripPlannerTool with required API handlers."""
        self.amadeus = AmadeusAPIHandler()
        self.firecrawl = FirecrawlAPIHandler()
        self.duckduckgo_activities = DuckDuckGoActivitySearch()
        self.duckduckgo_hotels = DuckDuckGoHotelSearch()
        
    def extract_trip_details(self, query: str) -> Dict[str, Any]:
        """
        Extract trip details from a user query using regex patterns.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with extracted trip details
        """
        # Initialize with default values
        details = {
            "origin_city": None,
            "destination_city": None,
            "departure_date": None,
            "return_date": None,
            "travelers": 1,
            "budget_level": "moderate",
            "accommodation_type": None,
            "flight_class": "economy"
        }
        
        # Extract destination city
        destination_patterns = [
            r"(?:to|in|visit|at|for|going to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"trip to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"travel to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"visit\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        # Try each pattern for destination
        for pattern in destination_patterns:
            match = re.search(pattern, query)
            if match:
                details["destination_city"] = match.group(1)
                break
        
        # Extract origin city
        origin_match = re.search(r"from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)(?:\s+to|\s+on|\s+starting|\s+for|\s+until|$)", query)
        if origin_match:
            # Check if this is actually a destination ("travel from X to Y")
            potential_origin = origin_match.group(1)
            if potential_origin != details["destination_city"]:
                details["origin_city"] = potential_origin
        
        # Extract dates - try different patterns for date formats
        # Format: YYYY-MM-DD
        date_pattern1 = r"(?:from|on|between)?\s+(\d{4}-\d{1,2}-\d{1,2})\s+(?:to|until|and|through)\s+(\d{4}-\d{1,2}-\d{1,2})"
        # Format: Month Day, Year or Month Day - Day, Year
        date_pattern2 = r"(?:from|on|between)?\s+([A-Z][a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\s+(?:to|until|and|through|-)?\s+(?:([A-Z][a-z]+)\s+)?(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"
        # Format: MM/DD/YYYY
        date_pattern3 = r"(?:from|on|between)?\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+(?:to|until|and|through)\s+(\d{1,2})/(\d{1,2})/(\d{4})"
        # Format: Month Day-Day, Year
        date_pattern4 = r"(?:from|on|between)?\s+([A-Z][a-z]+)\s+(\d{1,2})-(\d{1,2}),?\s+(\d{4})"
        
        # Try each date pattern
        date_match1 = re.search(date_pattern1, query)
        if date_match1:
            details["departure_date"] = date_match1.group(1)
            details["return_date"] = date_match1.group(2)
        else:
            # If not found, try to extract from text mentions of months
            date_match2 = re.search(date_pattern2, query)
            if date_match2:
                month1 = date_match2.group(1)
                day1 = date_match2.group(2)
                year1 = date_match2.group(3)
                
                # If there's a second month mentioned, use it; otherwise use the first month
                month2 = date_match2.group(4) if date_match2.group(4) else month1
                day2 = date_match2.group(5)
                year2 = date_match2.group(6)
                
                # Convert month names to numbers
                month_to_num = {
                    "January": "01", "February": "02", "March": "03", "April": "04",
                    "May": "05", "June": "06", "July": "07", "August": "08",
                    "September": "09", "October": "10", "November": "11", "December": "12",
                    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "Jun": "06",
                    "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                }
                
                month1_num = month_to_num.get(month1, "01")
                month2_num = month_to_num.get(month2, "01")
                
                details["departure_date"] = f"{year1}-{month1_num}-{day1.zfill(2)}"
                details["return_date"] = f"{year2}-{month2_num}-{day2.zfill(2)}"
            else:
                # Try MM/DD/YYYY format
                date_match3 = re.search(date_pattern3, query)
                if date_match3:
                    month1 = date_match3.group(1)
                    day1 = date_match3.group(2)
                    year1 = date_match3.group(3)
                    month2 = date_match3.group(4)
                    day2 = date_match3.group(5)
                    year2 = date_match3.group(6)
                    
                    details["departure_date"] = f"{year1}-{month1.zfill(2)}-{day1.zfill(2)}"
                    details["return_date"] = f"{year2}-{month2.zfill(2)}-{day2.zfill(2)}"
                else:
                    # Try Month Day-Day, Year format
                    date_match4 = re.search(date_pattern4, query)
                    if date_match4:
                        month = date_match4.group(1)
                        day1 = date_match4.group(2)
                        day2 = date_match4.group(3)
                        year = date_match4.group(4)
                        
                        month_to_num = {
                            "January": "01", "February": "02", "March": "03", "April": "04",
                            "May": "05", "June": "06", "July": "07", "August": "08",
                            "September": "09", "October": "10", "November": "11", "December": "12",
                            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "Jun": "06",
                            "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                        }
                        
                        month_num = month_to_num.get(month, "01")
                        
                        details["departure_date"] = f"{year}-{month_num}-{day1.zfill(2)}"
                        details["return_date"] = f"{year}-{month_num}-{day2.zfill(2)}"
        
        # If no dates found, but a destination is specified, use default dates (30 days from now)
        if details["destination_city"] and not details["departure_date"]:
            today = datetime.now()
            departure = today + timedelta(days=30)
            return_date = departure + timedelta(days=7)
            details["departure_date"] = departure.strftime("%Y-%m-%d")
            details["return_date"] = return_date.strftime("%Y-%m-%d")
        
        # Extract number of travelers
        travelers_match = re.search(r"(\d+)\s+(?:travelers|travellers|people|adults|persons)", query)
        if travelers_match:
            details["travelers"] = int(travelers_match.group(1))
        
        # Extract budget level
        if re.search(r"\b(?:cheap|budget|affordable|inexpensive)\b", query, re.IGNORECASE):
            details["budget_level"] = "budget"
        elif re.search(r"\b(?:luxury|luxurious|high-end|five-star|5-star)\b", query, re.IGNORECASE):
            details["budget_level"] = "luxury"
        
        # Extract accommodation type
        if re.search(r"\b(?:hotel|resort)\b", query, re.IGNORECASE):
            details["accommodation_type"] = "hotel"
        elif re.search(r"\b(?:apartment|flat|condo)\b", query, re.IGNORECASE):
            details["accommodation_type"] = "apartment"
        elif re.search(r"\b(?:hostel|backpacker)\b", query, re.IGNORECASE):
            details["accommodation_type"] = "hostel"
        
        # Extract flight class
        if re.search(r"\b(?:business\s+class|business)\b", query, re.IGNORECASE):
            details["flight_class"] = "business"
        elif re.search(r"\b(?:first\s+class|first)\b", query, re.IGNORECASE):
            details["flight_class"] = "first"
        elif re.search(r"\b(?:premium\s+economy|premium)\b", query, re.IGNORECASE):
            details["flight_class"] = "premium_economy"
        
        # Special processing for destination extraction from poorly structured queries
        if not details["destination_city"]:
            # Try to find any capitalized words that might be city names
            words = query.split()
            for i, word in enumerate(words):
                if word[0].isupper() and len(word) > 2 and word.lower() not in ["i", "a", "the", "from", "to"]:
                    # Check if it's part of a phrase like "to Paris" or "visit London"
                    if i > 0 and words[i-1].lower() in ["to", "in", "visit", "at", "for"]:
                        details["destination_city"] = word
                        break
        
        # Final fallback - extract first capitalized word as possible destination
        if not details["destination_city"]:
            words = query.split()
            for word in words:
                if word[0].isupper() and len(word) > 2 and word.lower() not in ["i", "a", "the", "from", "to"]:
                    details["destination_city"] = word
                    break
        
        logger.info(f"Extracted trip details: {details}")
        return details
    
    def plan_trip(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query and return trip planning information.
        
        Args:
            query: The user's natural language query about trip planning
            
        Returns:
            Dictionary with trip planning information
        """
        # Extract trip details from the query
        trip_details = self.extract_trip_details(query)
        logger.info(f"Extracted trip details: {trip_details}")
        
        # Validate mandatory fields
        if not trip_details["destination_city"]:
            return {
                "status": "error",
                "error": "Could not determine the destination city from your query. Please specify where you want to go."
            }
            
        # Get city codes
        origin = trip_details["origin_city"]
        destination = trip_details["destination_city"]
        
        result = {
            "status": "success",
            "query": query,
            "trip_details": trip_details,
            "flights": [],
            "hotels": [],
            "activities": [],
            "suggestions": []
        }
        
        # Get flight information if origin city is provided
        if origin:
            try:
                origin_code = self.amadeus.get_city_code(origin)
                if not origin_code:
                    origin_code = self._get_default_airport_code(origin)
                    if not origin_code:
                        logger.warning(f"Could not determine IATA code for origin city: {origin}")
                        result["suggestions"].append(f"I couldn't find the airport code for {origin}. Try using a major city nearby.")
                
                destination_code = self.amadeus.get_city_code(destination)
                if not destination_code:
                    destination_code = self._get_default_airport_code(destination)
                    if not destination_code:
                        logger.warning(f"Could not determine IATA code for destination city: {destination}")
                        result["suggestions"].append(f"I couldn't find the airport code for {destination}. Try using a major city nearby.")
                
                # Only search flights if we have both origin and destination codes
                if origin_code and destination_code:
                    logger.info(f"Searching flights from {origin} ({origin_code}) to {destination} ({destination_code})")
                    
                    flights = self.amadeus.search_flights(
                        origin=origin_code,
                        destination=destination_code,
                        departure_date=trip_details["departure_date"],
                        return_date=trip_details["return_date"],
                        adults=trip_details["travelers"],
                        max_results=5
                    )
                    
                    if flights:
                        logger.info(f"Found {len(flights)} flight options")
                        result["flights"] = flights
                    else:
                        logger.warning(f"No flights found from {origin_code} to {destination_code}")
                        result["suggestions"].append(
                            f"I couldn't find any flights from {origin} to {destination} for the specified dates. "
                            f"Try different dates or nearby airports."
                        )
                else:
                    logger.warning(f"Missing airport codes. Origin: {origin_code}, Destination: {destination_code}")
                    
                    if not origin_code:
                        result["suggestions"].append(f"I couldn't identify the airport code for {origin}.")
                    if not destination_code:
                        result["suggestions"].append(f"I couldn't identify the airport code for {destination}.")
                    
                    result["suggestions"].append("Try specifying major cities with international airports.")
            except Exception as e:
                logger.error(f"Error getting flight information: {e}")
                result["suggestions"].append(
                    f"There was an error getting flight information. Please try again later."
                )
        
        # Get hotel information
        try:
            logger.info(f"Searching for hotels in {destination} using DuckDuckGo")
            # Use DuckDuckGo as primary hotel search method
            web_hotels = self.duckduckgo_hotels.search_hotels(
                city=destination,
                check_in_date=trip_details["departure_date"],
                check_out_date=trip_details["return_date"],
                budget_level=trip_details["budget_level"],
                max_results=5
            )
            
            if web_hotels:
                logger.info(f"Found {len(web_hotels)} hotels via DuckDuckGo web search")
                result["hotels"] = web_hotels
            else:
                logger.warning(f"No hotels found for {destination} via DuckDuckGo, trying Amadeus API as fallback")
                # Fall back to Amadeus API if DuckDuckGo found nothing
                try:
                    destination_code = self.amadeus.get_city_code(destination) or self._get_default_airport_code(destination)
                    
                    hotels = self.amadeus.search_hotels(
                        city_code=destination_code,
                        check_in_date=trip_details["departure_date"],
                        check_out_date=trip_details["return_date"],
                        adults=trip_details["travelers"],
                        rooms=1,  # Assuming 1 room for simplicity
                        max_results=5
                    )
                    
                    if hotels:
                        logger.info(f"Found {len(hotels)} hotels via Amadeus API")
                        result["hotels"] = hotels
                        
                        if "suggestions" not in result:
                            result["suggestions"] = []
                        result["suggestions"].append(
                            "Hotel information was sourced from our official hotel provider."
                        )
                    else:
                        if "suggestions" not in result:
                            result["suggestions"] = []
                        result["suggestions"].append(
                            f"I couldn't find any hotels in {destination} for the specified dates. "
                            f"Try different dates or a different destination."
                        )
                except Exception as amadeus_error:
                    logger.error(f"Error with Amadeus API fallback: {amadeus_error}")
                    if "suggestions" not in result:
                        result["suggestions"] = []
                    result["suggestions"].append(
                        f"I couldn't find any hotels in {destination} for the specified dates. "
                        f"Try different dates or a different destination."
                    )
            
            # If we still don't have hotels, add a suggestion
            if not result.get("hotels"):
                if "suggestions" not in result:
                    result["suggestions"] = []
                result["suggestions"].append(
                    f"I couldn't find any hotels in {destination} for the specified dates. "
                    f"Try different dates or a different destination."
                )
                
        except Exception as e:
            logger.error(f"Error getting hotel information: {e}")
            
            if "suggestions" not in result:
                result["suggestions"] = []
            result["suggestions"].append(
                f"There was an error getting hotel information. Please try again later."
            )
            
        # Get activity information using DuckDuckGo with LLM content extraction
        try:
            # Extract activity type if mentioned in the query
            activity_type = None
            if re.search(r'\b(?:outdoor|nature|hiking|adventure)\b', query, re.IGNORECASE):
                activity_type = "outdoor"
            elif re.search(r'\b(?:museum|art|culture|historical)\b', query, re.IGNORECASE):
                activity_type = "cultural"
            elif re.search(r'\b(?:food|dining|culinary|restaurant)\b', query, re.IGNORECASE):
                activity_type = "food"
            
            # Search for activities using DuckDuckGo and LLM content extraction
            logger.info(f"Searching for activities in {destination} using DuckDuckGo and LLM")
            activities = self.duckduckgo_activities.search_activities(
                location=destination,
                activity_type=activity_type,
                limit=5
            )
            
            # If DuckDuckGo search didn't yield results, try Firecrawl as fallback
            if not activities:
                logger.info(f"No DuckDuckGo results, trying Firecrawl for activities in {destination}")
                # Search for activities via Firecrawl
                firecrawl_activities = self.firecrawl.search_activities(
                    location=destination,
                    activity_type=activity_type,
                    limit=3
                )
                
                # Search for tourist attractions
                attractions = self.firecrawl.search_tourist_attractions(
                    location=destination,
                    limit=3
                )
                
                # Add all activities to the result
                if firecrawl_activities:
                    activities.extend(firecrawl_activities)
                
                if attractions:
                    activities.extend(attractions)
                
                # Add restaurant recommendations if "food" was mentioned
                if re.search(r'\b(?:food|dining|culinary|restaurant|eat)\b', query, re.IGNORECASE):
                    restaurants = self.firecrawl.search_restaurants(
                        location=destination,
                        limit=3
                    )
                    if restaurants:
                        activities.extend(restaurants)
            
            # Add all activities to the result
            if activities:
                result["activities"] = activities
                logger.info(f"Found {len(activities)} activities for {destination}")
            else:
                result["suggestions"].append(
                    f"I couldn't find any activities in {destination}. "
                    f"Try being more specific about what you'd like to do."
                )
        except Exception as e:
            logger.error(f"Error getting activity information: {e}")
            result["suggestions"].append(
                f"There was an error getting activity information. Please try again later."
            )
            
        # Generate recommendations
        result["recommendations"] = self._generate_recommendations(result)
            
        return result
    
    def _generate_recommendations(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trip recommendations based on the trip planning results.
        
        Args:
            result: Dictionary with trip planning results
            
        Returns:
            Dictionary with recommendations
        """
        recommendations = {
            "top_flights": [],
            "top_hotels": [],
            "top_activities": [],
            "summary": ""
        }
        
        # Add top flights
        if "flights" in result and result["flights"]:
            for i, flight in enumerate(result["flights"][:3], 1):
                price = ""
                if isinstance(flight.get('price'), (int, float)):
                    price = f"{flight.get('currency', 'USD')} {flight.get('price', 0):.2f}"
                else:
                    price = f"{flight.get('currency', 'USD')} {flight.get('price', 0)}"
                
                segments = flight.get("segments", [])
                if segments:
                    first_segment = segments[0]
                    last_segment = segments[-1]
                    flight_info = {
                        "price": price,
                        "departure": f"{first_segment.get('departure_airport')} at {first_segment.get('departure_time')}",
                        "arrival": f"{last_segment.get('arrival_airport')} at {last_segment.get('arrival_time')}",
                        "stops": len(segments) - 1
                    }
                    recommendations["top_flights"].append(flight_info)
        
        # Add top hotels
        if "hotels" in result and result["hotels"]:
            for i, hotel in enumerate(result["hotels"][:3], 1):
                # Handle price formatting for both numeric and string price values
                price = ""
                if isinstance(hotel.get('price'), (int, float)):
                    price = f"{hotel.get('currency', 'USD')} {hotel.get('price', 0):.2f}"
                else:
                    price = str(hotel.get('price', 'Price not available'))
                
                hotel_info = {
                    "name": hotel.get("name", ""),
                    "price": price,
                    "rating": hotel.get("rating", "") or str(hotel.get("stars", "")) + " stars" if hotel.get("stars") else "",
                    "address": hotel.get("address", "")
                }
                recommendations["top_hotels"].append(hotel_info)
        
        # Add top activities
        if "activities" in result and result["activities"]:
            for i, activity in enumerate(result["activities"][:3], 1):
                price_info = ""
                if activity.get("price"):
                    price_info = f" - {activity.get('price')}"
                
                activity_info = {
                    "name": activity.get("name", ""),
                    "description": activity.get("description", ""),
                    "price": price_info,
                    "rating": activity.get("rating", "")
                }
                recommendations["top_activities"].append(activity_info)
        
        # Generate summary
        destination = result.get("trip_details", {}).get("destination_city", "your destination")
        start_date = result.get("trip_details", {}).get("departure_date", "")
        end_date = result.get("trip_details", {}).get("return_date", "")
        
        summary = f"Your trip to {destination}"
        if start_date and end_date:
            summary += f" from {start_date} to {end_date}"
        
        if recommendations["top_flights"]:
            flight = recommendations["top_flights"][0]
            summary += f". Best flight option: {flight['departure']} to {flight['arrival']} (Stops: {flight['stops']}) for {flight['price']}."
        
        if recommendations["top_hotels"]:
            hotel = recommendations["top_hotels"][0]
            summary += f" Recommended hotel: {hotel['name']} ({hotel['price']})."
        
        if recommendations["top_activities"]:
            activity = recommendations["top_activities"][0]
            summary += f" Don't miss: {activity['name']}."
        
        recommendations["summary"] = summary
        
        return recommendations
    
    def _get_default_airport_code(self, city: str) -> str:
        """Get a default airport code for common cities."""
        city_codes = {
            "new york": "NYC",
            "london": "LON",
            "paris": "PAR",
            "tokyo": "TYO",
            "los angeles": "LAX",
            "chicago": "CHI",
            "san francisco": "SFO",
            "miami": "MIA",
            "dubai": "DXB",
            "sydney": "SYD",
            "amsterdam": "AMS",
            "barcelona": "BCN",
            "madrid": "MAD",
            "frankfurt": "FRA",
            "rome": "ROM",
            "bangkok": "BKK",
            "hong kong": "HKG",
            "singapore": "SIN",
            "toronto": "YTO",
            "delhi": "DEL",
            "mumbai": "BOM",
            # Add more common city codes
            "beijing": "BJS",
            "shanghai": "SHA",
            "moscow": "MOW", 
            "seoul": "SEL",
            "berlin": "BER",
            "istanbul": "IST",
            "kuala lumpur": "KUL",
            "cairo": "CAI",
            "johannesburg": "JNB",
            "sao paulo": "SAO",
            "rio de janeiro": "RIO",
            "melbourne": "MEL",
            "brisbane": "BNE",
            "perth": "PER",
            "auckland": "AKL",
            "vancouver": "YVR",
            "montreal": "YMQ",
            "mexico city": "MEX",
            "milan": "MIL",
            "zurich": "ZRH",
            "vienna": "VIE",
            "osaka": "OSA",
            "manila": "MNL",
            "athens": "ATH",
            "helsinki": "HEL",
            "stockholm": "STO",
            "oslo": "OSL",
            "copenhagen": "CPH",
            "lisbon": "LIS",
            "geneva": "GVA",
            "dublin": "DUB",
            "brussels": "BRU",
            "buenos aires": "BUE"
        }
        
        city_lower = city.lower()
        default_code = city_codes.get(city_lower)
        
        if default_code:
            logger.info(f"Using default city code for {city}: {default_code}")
        else:
            logger.warning(f"No default city code found for {city}")
            
        return default_code

# Tool function that agents can call
def process_trip_query(query: str) -> Dict[str, Any]:
    """
    Process a natural language trip planning query and return relevant information.
    
    This function is designed to be called by an agent as a tool.
    
    Args:
        query: The user's natural language query about trip planning
        
    Returns:
        Dictionary with trip planning information including flights, hotels, and recommendations
    
    Example:
        >>> result = process_trip_query("Plan a trip from New York to Paris from June 15 to June 22 for 2 adults")
        >>> print(result['recommendations']['summary'])
        7-day trip to Paris from Jun 15 to Jun 22. Best flight option: JFK to CDG for USD 842.50. Recommended hotel: Hotel de Ville for EUR 1250.00
    """
    planner = AmadeusTripPlannerTool()
    return planner.plan_trip(query)

# Example of how to use this tool
if __name__ == "__main__":
    # Example query
    query = "I want to plan a trip from New York to Paris from June 15 to June 22 for 2 adults"
    
    # Process the query
    result = process_trip_query(query)
    
    # Print the results
    print(f"Query: {query}")
    print(f"Extracted trip details: {result['trip_details']}")
    
    if result["flights"]:
        print(f"\nFound {len(result['flights'])} flights:")
        for i, flight in enumerate(result["flights"][:3], 1):
            print(f"\nFlight {i}:")
            print(f"  Price: {flight['currency']} {flight['price']}")
            print("  Segments:")
            for j, segment in enumerate(flight['segments'], 1):
                print(f"    Segment {j}: {segment['departure_airport']} → {segment['arrival_airport']}")
                print(f"      Departure: {segment['departure_time']}")
                print(f"      Arrival: {segment['arrival_time']}")
                print(f"      Flight: {segment['flight_number']}")
    else:
        print("\nNo flights found")
    
    if result["hotels"]:
        print(f"\nFound {len(result['hotels'])} hotels:")
        for i, hotel in enumerate(result["hotels"][:3], 1):
            print(f"\nHotel {i}: {hotel['name']}")
            print(f"  Rating: {hotel.get('rating', 'N/A')}")
            print(f"  Address: {hotel['address']}")
            print(f"  Room type: {hotel.get('room_type', 'Standard')}")
            print(f"  Price: {hotel['currency']} {hotel['price']} ({hotel.get('board_type', 'Room only')})")
    else:
        print("\nNo hotels found")
    
    if result["activities"]:
        print(f"\nFound {len(result['activities'])} activities:")
        for i, activity in enumerate(result["activities"][:3], 1):
            print(f"\nActivity {i}: {activity['name']}")
            print(f"  Type: {activity.get('type', 'Unknown')}")
            print(f"  Location: {activity['location']}")
            print(f"  Rating: {activity.get('rating', 'N/A')}")
    else:
        print("\nNo activities found")
    
    print("\nRecommendations:")
    print(f"  {result['recommendations']['summary']}")
