"""
Trip Planner Tool for LLM Integration

This module provides a comprehensive travel planning function that can be called by an LLM
as a tool. It integrates hotel scraping, flight scraping, activity search, and travel
information retrieval into a single coherent trip planning tool.
"""

import json
import logging
import openai
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

# Import the various scrapers
from .hotel_scraper import HotelScraper
from .flight_scraper import FlightScraper
from .activity_scraper import ActivityScraper
from .travel_info_scraper import TravelInfoScraper
from .amadeus_api_handler import AmadeusAPIHandler
from .firecrawl_api_handler import FirecrawlAPIHandler
from .duckduckgo_activity_search import DuckDuckGoActivitySearch
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("OPENAI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client (ensure OPENAI_API_KEY is set in environment or .env file)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file if present
    
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment. LLM integration will not work.")
except ImportError:
    logger.warning("dotenv package not installed. Using environment variables directly.")

# Set up OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    client = openai.OpenAI(api_key=openai_api_key)


def plan_trip(
    origin_city: str,
    destination_city: str,
    start_date: str,
    end_date: str,
    travelers: int = 2,
    budget_level: str = "moderate",  # "budget", "moderate", "luxury"
    trip_type: Optional[str] = None,  # "leisure", "business", "adventure", etc.
    accommodation_type: Optional[str] = None,  # "hotel", "resort", "airbnb", etc.
    flight_class: str = "economy",  # "economy", "premium_economy", "business", "first"
    include_activities: bool = True,
    origin_country: Optional[str] = "United States",
    destination_country: Optional[str] = None,
    max_results_per_category: int = 3
) -> Dict[str, Any]:
    """
    Plan a comprehensive trip with flights, accommodations, activities, and travel information.
    This function is designed to be called by a language model as a tool.
    
    Args:
        origin_city: City of departure
        destination_city: City of destination
        start_date: Trip start date in YYYY-MM-DD format
        end_date: Trip end date in YYYY-MM-DD format
        travelers: Number of travelers
        budget_level: Budget level (budget, moderate, luxury)
        trip_type: Type of trip (leisure, business, adventure, etc.)
        accommodation_type: Type of accommodation to prefer
        flight_class: Class of flight (economy, premium_economy, business, first)
        include_activities: Whether to include activity recommendations
        origin_country: Country of origin (for visa info)
        destination_country: Country of destination (if different from city)
        max_results_per_category: Maximum number of results to return per category
    
    Returns:
        Dictionary containing the complete trip plan with flights, accommodations,
        activities, travel information, and a summary.
    """
    logger.info(f"Planning trip from {origin_city} to {destination_city} ({start_date} to {end_date})")
    trip_plan = {}
    errors = []
    
    # Validate input dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if end < start:
            return {
                "error": "End date must be after start date",
                "status": "failed"
            }
        trip_duration = (end - start).days
    except ValueError:
        return {
            "error": "Invalid date format. Please use YYYY-MM-DD",
            "status": "failed"
        }
    
    # Set default destination country if not provided
    if not destination_country:
        destination_country = destination_city
    
    # 1. Get flight options
    try:
        flight_results = get_flight_options(
            origin_city=origin_city,
            destination_city=destination_city,
            departure_date=start_date,
            return_date=end_date,
            travelers=travelers,
            flight_class=flight_class,
            max_results=max_results_per_category
        )
        trip_plan["flights"] = flight_results
    except Exception as e:
        logger.error(f"Error getting flight options: {str(e)}")
        errors.append(f"Could not retrieve flight options: {str(e)}")
        trip_plan["flights"] = {"error": str(e), "results": []}
    
    # 2. Get accommodation options
    try:
        accommodation_results = get_accommodation_options(
            location=destination_city,
            check_in=start_date,
            check_out=end_date,
            guests=travelers,
            budget_level=budget_level,
            accommodation_type=accommodation_type,
            max_results=max_results_per_category
        )
        trip_plan["accommodations"] = accommodation_results
    except Exception as e:
        logger.error(f"Error getting accommodation options: {str(e)}")
        errors.append(f"Could not retrieve accommodation options: {str(e)}")
        trip_plan["accommodations"] = {"error": str(e), "results": []}
    
    # 3. Get activity options if requested
    if include_activities:
        try:
            activity_results = get_activity_options(
                location=destination_city,
                max_results=max_results_per_category
            )
            trip_plan["activities"] = activity_results
        except Exception as e:
            logger.error(f"Error getting activity options: {str(e)}")
            errors.append(f"Could not retrieve activity options: {str(e)}")
            trip_plan["activities"] = {"error": str(e), "results": []}
    
    # 4. Get travel information (visa, health, advisories)
    try:
        travel_info = get_travel_information(
            origin_country=origin_country,
            destination_country=destination_country
        )
        trip_plan["travel_info"] = travel_info
    except Exception as e:
        logger.error(f"Error getting travel information: {str(e)}")
        errors.append(f"Could not retrieve travel information: {str(e)}")
        trip_plan["travel_info"] = {"error": str(e)}
    
    # 5. Generate a summary with LLM if available
    if openai_api_key:
        try:
            trip_summary = generate_trip_summary(trip_plan, errors)
            trip_plan["summary"] = trip_summary
        except Exception as e:
            logger.error(f"Error generating trip summary: {str(e)}")
            trip_plan["summary"] = {
                "error": f"Could not generate summary: {str(e)}",
                "headline": f"Trip to {destination_city}"
            }
    else:
        trip_plan["summary"] = {
            "headline": f"Trip to {destination_city}",
            "overview": f"A {trip_duration}-day trip from {origin_city} to {destination_city}."
        }
    
    # Add metadata
    trip_plan["metadata"] = {
        "origin_city": origin_city,
        "destination_city": destination_city,
        "start_date": start_date,
        "end_date": end_date,
        "travelers": travelers,
        "budget_level": budget_level,
        "trip_type": trip_type,
        "errors": errors,
        "created_at": datetime.now().isoformat()
    }
    
    # Set status
    if errors:
        trip_plan["status"] = "partial" if len(errors) < 4 else "failed"
    else:
        trip_plan["status"] = "success"
    
    return trip_plan


def get_flight_options(
    origin_city: str,
    destination_city: str,
    departure_date: str,
    return_date: str,
    travelers: int = 1,
    flight_class: str = "economy",
    max_results: int = 3
) -> Dict[str, Any]:
    """Get flight options using both the flight scraper and Amadeus API"""
    # Convert city names to airport codes
    origin_code = get_airport_code(origin_city)
    destination_code = get_airport_code(destination_city)
    
    results = {}
    
    # 1. Try Amadeus API first
    try:
        # Initialize Amadeus client
        amadeus_client = AmadeusAPIHandler()
        
        # Get city codes if needed
        origin_iata = amadeus_client.get_city_code(origin_city) or origin_code
        destination_iata = amadeus_client.get_city_code(destination_city) or destination_code
        
        # Search flights
        amadeus_flights = amadeus_client.search_flights(
            origin=origin_iata,
            destination=destination_iata,
            departure_date=departure_date,
            return_date=return_date,
            adults=travelers,
            max_results=max_results
        )
        
        if amadeus_flights:
            results["amadeus"] = amadeus_flights
            logger.info(f"Found {len(amadeus_flights)} flights via Amadeus API")
    except Exception as e:
        logger.error(f"Error getting flights from Amadeus API: {str(e)}")
    
    # 2. Fallback to scrapers if needed
    try:
        # Initialize scraper and search for flights
        scraper = FlightScraper()
        all_results = scraper.search_flights_all_sites(
            origin=origin_code,
            destination=destination_code,
            date=departure_date,
            return_date=return_date,
            adults=travelers
        )
        
        # Process and filter results
        for site, flights in all_results.items():
            # Filter for flight class if specified in the data
            filtered_flights = []
            for flight in flights:
                if len(filtered_flights) >= max_results:
                    break
                # Only add flights that match our criteria
                filtered_flights.append(flight)
            
            if filtered_flights:
                results[site] = filtered_flights
                
    except Exception as e:
        logger.error(f"Error getting flights from scrapers: {str(e)}")
    
    # If no results from either source, return empty
    if not results:
        return {
            "best_overall": [],
            "by_site": {},
            "search_params": {
                "origin": origin_city,
                "destination": destination_city,
                "departure_date": departure_date,
                "return_date": return_date,
                "travelers": travelers,
                "class": flight_class
            }
        }
    
    # Find the best overall options across all sources
    all_flights = []
    for site, flights in results.items():
        for flight in flights:
            flight_copy = flight.copy()
            flight_copy["site"] = site
            all_flights.append(flight_copy)
    
    # Sort by price and stops
    def flight_sort_key(flight):
        # Get number of stops (0 for direct flights)
        stops = 0
        if isinstance(flight.get("stops"), str):
            if "direct" in flight.get("stops", "").lower() or "nonstop" in flight.get("stops", "").lower():
                stops = 0
            else:
                # Try to extract number from text like "1 stop"
                import re
                match = re.search(r'(\d+)', flight.get("stops", ""))
                if match:
                    stops = int(match.group(1))
                else:
                    stops = 1  # Default if we can't determine
        elif "segments" in flight:
            # For Amadeus API results, count segments
            stops = len(flight.get("segments", [])) - 1
            
        return (stops, flight.get("price", float("inf")))
    
    sorted_flights = sorted(all_flights, key=flight_sort_key)
    best_overall = sorted_flights[:max_results] if sorted_flights else []
    
    # Format the results
    return {
        "best_overall": best_overall,
        "by_site": results,
        "search_params": {
            "origin": origin_city,
            "destination": destination_city,
            "departure_date": departure_date,
            "return_date": return_date,
            "travelers": travelers,
            "class": flight_class
        }
    }


def get_accommodation_options(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    budget_level: str = "moderate",
    accommodation_type: Optional[str] = None,
    max_results: int = 3
) -> Dict[str, Any]:
    """Get accommodation options using both the hotel scraper and Amadeus API"""
    results = {}
    
    # 1. Try Amadeus API first
    try:
        # Initialize Amadeus client
        amadeus_client = AmadeusAPIHandler()
        
        # Get city code
        city_code = amadeus_client.get_city_code(location)
        
        if city_code:
            # Search hotels
            amadeus_hotels = amadeus_client.search_hotels(
                city_code=city_code,
                check_in_date=check_in,
                check_out_date=check_out,
                adults=guests,
                rooms=1,  # Default to 1 room
                max_results=max_results
            )
            
            if amadeus_hotels:
                results["amadeus"] = amadeus_hotels
                logger.info(f"Found {len(amadeus_hotels)} hotels via Amadeus API")
    except Exception as e:
        logger.error(f"Error getting hotels from Amadeus API: {str(e)}")
    
    # 2. Fallback to scrapers
    try:
        # Initialize scraper and search for accommodations
        scraper = HotelScraper()
        all_results = scraper.search_hotels_all_sites(
            location=location,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            rooms=1  # Default to 1 room
        )
        
        # Define price ranges for budget levels (simplified)
        price_ranges = {
            "budget": (0, 100),
            "moderate": (100, 300),
            "luxury": (300, float("inf"))
        }
        
        min_price, max_price = price_ranges.get(budget_level.lower(), (0, float("inf")))
        
        for site, hotels in all_results.items():
            # Filter based on budget and accommodation type
            filtered_hotels = []
            for hotel in hotels:
                if len(filtered_hotels) >= max_results:
                    break
                    
                price = hotel.get("price", 0)
                if price and min_price <= price <= max_price:
                    # Check accommodation type if specified
                    if accommodation_type:
                        hotel_type = hotel.get("type", "").lower()
                        if accommodation_type.lower() not in hotel_type and accommodation_type.lower() not in hotel.get("name", "").lower():
                            continue
                    
                    filtered_hotels.append(hotel)
            
            if filtered_hotels:
                results[site] = filtered_hotels
                
    except Exception as e:
        logger.error(f"Error getting hotels from scrapers: {str(e)}")
    
    # If no results from either source, return empty
    if not results:
        return {
            "best_overall": [],
            "by_site": {},
            "search_params": {
                "location": location,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests,
                "budget_level": budget_level,
                "accommodation_type": accommodation_type
            }
        }
    
    # Find the best overall options across all sources
    all_accommodations = []
    for site, hotels in results.items():
        for hotel in hotels:
            hotel_copy = hotel.copy()
            hotel_copy["site"] = site
            all_accommodations.append(hotel_copy)
    
    # Sort by rating and price
    def accommodation_sort_key(hotel):
        return (-1 * (hotel.get("rating") or 0), hotel.get("price", float("inf")))
    
    sorted_accommodations = sorted(all_accommodations, key=accommodation_sort_key)
    best_overall = sorted_accommodations[:max_results] if sorted_accommodations else []
    
    # Format the results
    return {
        "best_overall": best_overall,
        "by_site": results,
        "search_params": {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "budget_level": budget_level,
            "accommodation_type": accommodation_type
        }
    }


def get_activity_options(
    location: str,
    max_results: int = 5,
    activity_type: str = None
) -> Dict[str, Any]:
    """Get activity options using DuckDuckGo search with LLM extraction, Firecrawl API, 
    and fallback to scraper if needed
    
    Args:
        location: The location to search for activities
        max_results: Maximum number of results to return
        activity_type: Type of activity to search for (optional)
        
    Returns:
        Dictionary containing activity options
    """
    logger.info(f"Searching for activities in {location}")
    
    results = {
        "duckduckgo": [],
        "firecrawl": [],
        "scraper": []
    }
    
    # Try DuckDuckGo search with LLM extraction first
    try:
        duckduckgo_handler = DuckDuckGoActivitySearch()
        
        # Get activities using DuckDuckGo + LLM
        activities = duckduckgo_handler.search_activities(
            location=location, 
            activity_type=activity_type,
            limit=max_results
        )
        
        if activities:
            results["duckduckgo"].extend(activities)
            logger.info(f"Found {len(results['duckduckgo'])} activities via DuckDuckGo + LLM")
    
    except Exception as e:
        logger.error(f"Error getting activities from DuckDuckGo: {str(e)}")
    
    # Try Firecrawl API if we don't have enough results yet
    if len(results["duckduckgo"]) < max_results:
        try:
            firecrawl_handler = FirecrawlAPIHandler()
            
            # Get regular activities
            activities = firecrawl_handler.search_activities(
                location=location, 
                activity_type=activity_type,
                limit=max_results
            )
            
            # Get tourist attractions
            attractions = firecrawl_handler.search_tourist_attractions(
                location=location,
                limit=max_results
            )
            
            # Get restaurants as activities
            restaurants = firecrawl_handler.search_restaurants(
                location=location,
                limit=max_results
            )
            
            # Add all results to the Firecrawl section
            if activities:
                results["firecrawl"].extend(activities)
            if attractions:
                results["firecrawl"].extend(attractions)
            if restaurants:
                results["firecrawl"].extend(restaurants)
                
            logger.info(f"Found {len(results['firecrawl'])} activities via Firecrawl")
        
        except Exception as e:
            logger.error(f"Error getting activities from Firecrawl: {str(e)}")
    
    # Fallback to scraper if needed
    if not results["duckduckgo"] and not results["firecrawl"]:
        try:
            scraper = ActivityScraper()
            all_results = scraper.search_activities_all_sites(location=location)
            
            for site, activities in all_results.items():
                for activity in activities:
                    activity["source"] = site
                    results["scraper"].append(activity)
                    
            logger.info(f"Found {len(results['scraper'])} activities via scraper")
        
        except Exception as e:
            logger.error(f"Error getting activities from scraper: {str(e)}")
    
    # If no results from any source, return empty
    if not results["duckduckgo"] and not results["firecrawl"] and not results["scraper"]:
        return {
            "best_overall": [],
            "by_source": {},
            "search_params": {
                "location": location,
                "activity_type": activity_type
            }
        }
    
    # Combine and sort all activities
    all_activities = []
    
    # Prioritize DuckDuckGo results (highest quality due to LLM extraction)
    if results["duckduckgo"]:
        all_activities.extend(results["duckduckgo"])
    
    # Then add Firecrawl results
    if results["firecrawl"] and (len(all_activities) < max_results):
        all_activities.extend(results["firecrawl"])
    
    # Finally add scraper results if needed
    if results["scraper"] and (len(all_activities) < max_results):
        all_activities.extend(results["scraper"])
    
    # Sort activities (by rating if available, else keep original order)
    all_activities.sort(
        key=lambda x: (-(float(x.get("rating", 0)) if isinstance(x.get("rating"), (int, float)) else 0)),
        reverse=False
    )
    
    # Limit to max_results
    best_overall = all_activities[:max_results] if all_activities else []
    
    # Organize by source for the final output
    by_source = {}
    if results["duckduckgo"]:
        by_source["duckduckgo"] = results["duckduckgo"][:max_results]
    if results["firecrawl"]:
        by_source["firecrawl"] = results["firecrawl"][:max_results]
    if results["scraper"]:
        by_source["scraper"] = results["scraper"][:max_results]
    
    # Format the results
    return {
        "best_overall": best_overall,
        "by_source": by_source,
        "search_params": {
            "location": location,
            "activity_type": activity_type
        }
    }


def get_travel_information(
    origin_country: str,
    destination_country: str
) -> Dict[str, Any]:
    """Get travel information using the travel info scraper"""
    # Initialize scraper and get travel information
    scraper = TravelInfoScraper()
    travel_info = scraper.get_travel_info(
        from_country=origin_country,
        to_country=destination_country
    )
    
    # Extract and format the most important information
    visa_req = travel_info.get("visa", {}).get("requirement", "Unknown")
    visa_desc = travel_info.get("visa", {}).get("description", "")
    
    advisories = []
    for advisory in travel_info.get("advisories", {}).get("advisories", []):
        advisories.append({
            "source": advisory.get("source", ""),
            "level": advisory.get("level", ""),
            "summary": advisory.get("summary", "")[:200] + "..." if len(advisory.get("summary", "")) > 200 else advisory.get("summary", "")
        })
    
    health_info = {
        "summary": travel_info.get("health", {}).get("summary", "")[:200] + "..." if len(travel_info.get("health", {}).get("summary", "")) > 200 else travel_info.get("health", {}).get("summary", ""),
        "vaccinations": travel_info.get("health", {}).get("vaccinations", [])[:5]
    }
    
    # Format the results
    return {
        "visa": {
            "requirement": visa_req,
            "description": visa_desc[:300] + "..." if len(visa_desc) > 300 else visa_desc
        },
        "advisories": advisories,
        "health": health_info,
        "details": travel_info  # Include full details for reference
    }


def generate_trip_summary(trip_plan: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
    """Generate a human-readable summary of the trip plan using OpenAI"""
    if not openai_api_key or not client:
        return {
            "headline": f"Trip to {trip_plan['metadata']['destination_city']}",
            "overview": f"A {(datetime.strptime(trip_plan['metadata']['end_date'], '%Y-%m-%d') - datetime.strptime(trip_plan['metadata']['start_date'], '%Y-%m-%d')).days}-day trip from {trip_plan['metadata']['origin_city']} to {trip_plan['metadata']['destination_city']}."
        }
    
    try:
        # Create a condensed version of the trip plan for the prompt
        origin = trip_plan["metadata"]["origin_city"]
        destination = trip_plan["metadata"]["destination_city"]
        start_date = trip_plan["metadata"]["start_date"]
        end_date = trip_plan["metadata"]["end_date"]
        travelers = trip_plan["metadata"]["travelers"]
        
        # Get best flight if available
        best_flight = "No flight information available."
        if trip_plan.get("flights", {}).get("best_overall"):
            flight = trip_plan["flights"]["best_overall"][0]
            price = f"${flight.get('price', 0):.2f}" if flight.get("price") else "price unknown"
            airline = flight.get("airline", "Unknown airline")
            best_flight = f"{airline} flight for {price}"
        
        # Get best accommodation if available
        best_accommodation = "No accommodation information available."
        if trip_plan.get("accommodations", {}).get("best_overall"):
            hotel = trip_plan["accommodations"]["best_overall"][0]
            price = f"${hotel.get('price', 0):.2f}" if hotel.get("price") else "price unknown"
            name = hotel.get("name", "Unknown hotel")
            rating = f"{hotel.get('rating', 'N/A')}/5" if hotel.get("rating") else "rating unknown"
            best_accommodation = f"{name} ({rating}) for {price} per night"
        
        # Get visa requirement if available
        visa_req = "Unknown visa requirements."
        if trip_plan.get("travel_info", {}).get("visa", {}).get("requirement"):
            visa_req = f"Visa requirement: {trip_plan['travel_info']['visa']['requirement']}"
        
        # Prepare the prompt
        prompt = f"""
        Create a JSON summary of this trip plan with two fields:
        1. "headline": A catchy headline for this trip
        2. "overview": A brief 2-3 sentence overview that summarizes the key details
        
        Trip details:
        - Trip from {origin} to {destination}
        - Dates: {start_date} to {end_date}
        - Number of travelers: {travelers}
        - Best flight option: {best_flight}
        - Best accommodation: {best_accommodation}
        - {visa_req}
        """
        
        if errors:
            prompt += f"\nNote: There were some issues retrieving all information: {', '.join(errors)}"
        
        # Call the API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a travel assistant that creates concise, informative trip summaries in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=400
        )
        
        # Extract and parse the result
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logger.error(f"Error generating summary with OpenAI: {str(e)}")
        return {
            "headline": f"Trip to {trip_plan['metadata']['destination_city']}",
            "overview": f"A {(datetime.strptime(trip_plan['metadata']['end_date'], '%Y-%m-%d') - datetime.strptime(trip_plan['metadata']['start_date'], '%Y-%m-%d')).days}-day trip from {trip_plan['metadata']['origin_city']} to {trip_plan['metadata']['destination_city']}."
        }


def get_airport_code(city: str) -> str:
    """
    Get airport code for a city (simplified version).
    In a real implementation, you would use an API or database lookup.
    """
    # Simple dictionary of common city to airport code mappings
    airport_codes = {
        "new york": "JFK",
        "los angeles": "LAX",
        "chicago": "ORD",
        "san francisco": "SFO",
        "miami": "MIA",
        "london": "LHR",
        "paris": "CDG",
        "tokyo": "HND",
        "sydney": "SYD",
        "dubai": "DXB",
        "delhi": "DEL",
        "mumbai": "BOM",
        "bangalore": "BLR",
        "hyderabad": "HYD",
        "chennai": "MAA",
        # Add more as needed
    }
    
    # Try to find a direct match
    city_lower = city.lower()
    if city_lower in airport_codes:
        return airport_codes[city_lower]
    
    # Try partial match
    for key, code in airport_codes.items():
        if key in city_lower or city_lower in key:
            return code
    
    # If we can't find a match, return the first 3 letters of the city (simplified)
    return city.upper()[:3]


# Example of how to call this function from an LLM tool setup
def llm_trip_planner_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM Tool wrapper for the trip planner function.
    
    This function is designed to be called by a language model as a tool.
    It extracts parameters from the input dictionary and calls the plan_trip function.
    
    Args:
        params: Dictionary containing trip planning parameters
            - origin_city: City of departure
            - destination_city: City of destination
            - start_date: Trip start date (YYYY-MM-DD)
            - end_date: Trip end date (YYYY-MM-DD)
            - travelers: Number of travelers (default: 2)
            - budget_level: Budget level (default: "moderate")
            - trip_type: Type of trip (optional)
            - accommodation_type: Type of accommodation (optional)
            - flight_class: Class of flight (default: "economy")
            - include_activities: Whether to include activities (default: True)
            - origin_country: Country of origin (default: "United States")
            - destination_country: Country of destination (optional)
    
    Returns:
        Complete trip plan with flights, accommodations, activities, and travel info
    """
    # Extract parameters with fallbacks
    origin_city = params.get("origin_city")
    destination_city = params.get("destination_city")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    
    # Validate required parameters
    if not all([origin_city, destination_city, start_date, end_date]):
        return {
            "error": "Missing required parameters. Must provide origin_city, destination_city, start_date, and end_date.",
            "status": "failed"
        }
    
    # Extract optional parameters with defaults
    travelers = params.get("travelers", 2)
    budget_level = params.get("budget_level", "moderate")
    trip_type = params.get("trip_type")
    accommodation_type = params.get("accommodation_type")
    flight_class = params.get("flight_class", "economy")
    include_activities = params.get("include_activities", True)
    origin_country = params.get("origin_country", "United States")
    destination_country = params.get("destination_country")
    
    # Call the main function
    return plan_trip(
        origin_city=origin_city,
        destination_city=destination_city,
        start_date=start_date,
        end_date=end_date,
        travelers=travelers,
        budget_level=budget_level,
        trip_type=trip_type,
        accommodation_type=accommodation_type,
        flight_class=flight_class,
        include_activities=include_activities,
        origin_country=origin_country,
        destination_country=destination_country
    )


# Example usage
if __name__ == "__main__":
    # Example trip planning request
    trip_request = {
        "origin_city": "New York",
        "destination_city": "Tokyo",
        "start_date": "2025-06-01",
        "end_date": "2025-06-07",
        "travelers": 2,
        "budget_level": "moderate",
        "flight_class": "economy",
        "include_activities": True
    }
    
    # Call the trip planner
    trip_plan = llm_trip_planner_tool(trip_request)
    
    # Print summary
    print("\n=== TRIP PLAN SUMMARY ===")
    if trip_plan.get("summary"):
        print(f"Headline: {trip_plan['summary'].get('headline', 'No headline available')}")
        print(f"Overview: {trip_plan['summary'].get('overview', 'No overview available')}")
    
    # Print flight options
    print("\n=== BEST FLIGHT OPTIONS ===")
    for i, flight in enumerate(trip_plan.get("flights", {}).get("best_overall", []), 1):
        print(f"{i}. {flight.get('airline', 'Unknown airline')} - ${flight.get('price', 0):.2f}")
        print(f"   Duration: {flight.get('duration', 'N/A')} | Stops: {flight.get('stops', 'N/A')}")
    
    # Print accommodation options
    print("\n=== BEST ACCOMMODATION OPTIONS ===")
    for i, hotel in enumerate(trip_plan.get("accommodations", {}).get("best_overall", []), 1):
        print(f"{i}. {hotel.get('name', 'Unknown hotel')} - ${hotel.get('price', 0):.2f} per night")
        print(f"   Rating: {hotel.get('rating', 'N/A')}")
    
    # Print visa info
    print("\n=== TRAVEL REQUIREMENTS ===")
    visa_info = trip_plan.get("travel_info", {}).get("visa", {})
    print(f"Visa: {visa_info.get('requirement', 'Unknown')}")
    
    # Print trip status
    print(f"\nTrip planning status: {trip_plan.get('status', 'unknown')}")
