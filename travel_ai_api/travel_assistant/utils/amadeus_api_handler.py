import os
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import time
from dotenv import load_dotenv
from amadeus import Client, ResponseError, Location

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AmadeusAPIHandler:
    """
    A handler for the Amadeus Travel APIs to search for flights and hotels.
    Uses the official Amadeus Python SDK.
    """
    
    def __init__(self):
        """Initialize the Amadeus client with API key and secret from environment variables."""
        self.client_id = os.getenv("AMADEUS_API_KEY")
        self.client_secret = os.getenv("AMADEUS_API_SECRET")
        
        # Set up retry parameters
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.rate_limit_delay = 1  # seconds
        
        # Check if credentials are available
        if not self.client_id or not self.client_secret:
            logger.error("Missing Amadeus API credentials. Set AMADEUS_API_KEY and AMADEUS_API_SECRET environment variables.")
        
        # Initialize Amadeus client
        try:
            self.client = Client(client_id=self.client_id, client_secret=self.client_secret)
            logger.debug("Amadeus client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Amadeus client: {e}")
            self.client = None
    
    def search_flights(self, origin: str, destination: str, departure_date: str, 
                      return_date: Optional[str] = None, adults: int = 1, 
                      currency: str = "USD", max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for flights using Amadeus Flight Offers Search API
        
        Args:
            origin: Origin city or airport IATA code
            destination: Destination city or airport IATA code
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (for round-trip)
            adults: Number of adult passengers
            currency: Currency code (default: USD)
            max_results: Maximum number of results to return
            
        Returns:
            List of flight offers with details
        """
        logger.info(f"Searching flights from {origin} to {destination} on {departure_date}")
        
        if not self.client:
            logger.error("Amadeus client not initialized")
            return []
        
        retries = 0
        while retries < self.max_retries:
            try:
                # Prepare search parameters
                search_params = {
                    'originLocationCode': origin,
                    'destinationLocationCode': destination,
                    'departureDate': departure_date,
                    'adults': adults,
                    'currencyCode': currency,
                    'max': max_results
                }
                
                # Add return date if provided
                if return_date:
                    search_params['returnDate'] = return_date
                
                # Make API call using the SDK's named method
                logger.debug(f"Calling flight_offers_search.get with params: {search_params}")
                response = self.client.shopping.flight_offers_search.get(**search_params)
                
                # Process and return results
                if hasattr(response, 'data') and response.data:
                    logger.info(f"Found {len(response.data)} flight options")
                    return self._parse_flight_offers(response.data)
                else:
                    logger.warning(f"No flight offers found for {origin} to {destination}")
                    return []
                
            except ResponseError as error:
                # Handle rate limiting with exponential backoff
                if str(error).startswith('[429]'):
                    retries += 1
                    sleep_time = self.rate_limit_delay * (2 ** retries)
                    logger.warning(f"Rate limited. Retrying in {sleep_time} seconds")
                    time.sleep(sleep_time)
                    continue
                
                logger.error(f"Amadeus API error: {error}")
                return []
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to search flights after {self.max_retries} attempts: {e}")
                    return []
                
                logger.warning(f"Attempt {retries} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
    
    def search_hotels(self, city_code: str, check_in_date: str, check_out_date: str, 
                     adults: int = 1, rooms: int = 1, currency: str = "USD", 
                     max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for hotels using Amadeus Hotel API
        
        This method uses a two-step process:
        1. Get a list of hotels in the city
        2. Get available offers for each hotel
        
        Args:
            city_code: City IATA code
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            adults: Number of adult guests per room
            rooms: Number of rooms
            currency: Currency code (default: USD)
            max_results: Maximum number of results to return
            
        Returns:
            List of hotel offers with details
        """
        logger.info(f"Searching hotels in {city_code} from {check_in_date} to {check_out_date}")
        
        if not self.client:
            logger.error("Amadeus client not initialized")
            return []
        
        retries = 0
        max_hotels_to_try = max_results * 3  # Try more hotels to compensate for failed ones
        
        while retries < self.max_retries:
            try:
                # Step 1: Get list of hotels in the city
                logger.debug(f"Finding hotels in city {city_code}")
                hotels_response = None
                
                try:
                    hotels_response = self.client.reference_data.locations.hotels.by_city.get(
                        cityCode=city_code,
                        radius=20,
                        radiusUnit='KM',
                        hotelSource='ALL'
                    )
                except ResponseError as e:
                    logger.warning(f"Error finding hotels in city {city_code}: {e}")
                    # Try alternative approach with geocode if available
                    return []
                
                if not hasattr(hotels_response, 'data') or not hotels_response.data:
                    logger.warning(f"No hotels found in city {city_code}")
                    return []
                
                # Get hotel IDs from the response
                hotel_ids = [hotel.get('hotelId') for hotel in hotels_response.data[:max_hotels_to_try] if hotel.get('hotelId')]
                
                if not hotel_ids:
                    logger.warning(f"No valid hotel IDs found in city {city_code}")
                    return []
                
                logger.info(f"Found {len(hotel_ids)} hotels in {city_code}, checking availability")
                
                # Step 2: Check availability for each hotel
                hotels = []
                successful_hotels = 0
                
                # For each hotel ID, search for offers
                for hotel_id in hotel_ids:
                    if successful_hotels >= max_results:
                        break
                        
                    try:
                        # Direct endpoint to get hotel offers
                        hotel_offers = self.client.shopping.hotel_offers_search.get(
                            hotelIds=hotel_id,
                            adults=adults,
                            roomQuantity=rooms,
                            checkInDate=check_in_date,
                            checkOutDate=check_out_date,
                            currency=currency,
                            bestRateOnly=True,
                            includeClosed=False  # Only include hotels with available rooms
                        )
                        
                        if hasattr(hotel_offers, 'data') and hotel_offers.data:
                            parsed_hotel = self._parse_hotel_offers(hotel_offers.data)
                            if parsed_hotel:  # Make sure we have valid data
                                hotels.append(parsed_hotel)
                                successful_hotels += 1
                                logger.debug(f"Found availability for hotel {hotel_id}")
                        
                    except ResponseError as e:
                        # Log but continue with next hotel
                        logger.warning(f"Error fetching offers for hotel {hotel_id}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Unexpected error for hotel {hotel_id}: {e}")
                        continue
                
                logger.info(f"Successfully found {len(hotels)} hotels with availability in {city_code}")
                return hotels
                
            except ResponseError as error:
                # Handle rate limiting with exponential backoff
                if str(error).startswith('[429]'):
                    retries += 1
                    sleep_time = self.rate_limit_delay * (2 ** retries)
                    logger.warning(f"Rate limited. Retrying in {sleep_time} seconds")
                    time.sleep(sleep_time)
                    continue
                
                logger.error(f"Amadeus API error during hotel search: {error}")
                return []
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to search hotels after {self.max_retries} attempts: {e}")
                    return []
                
                logger.warning(f"Attempt {retries} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
    
    def _parse_flight_offers(self, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse flight offers data into a standardized format
        
        Args:
            offers: List of flight offers from Amadeus API
            
        Returns:
            List of standardized flight offers
        """
        results = []
        
        for offer in offers:
            try:
                price = offer.get('price', {})
                itineraries = offer.get('itineraries', [])
                segments = []
                
                # Process all segments across all itineraries
                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        departure = segment.get('departure', {})
                        arrival = segment.get('arrival', {})
                        carrier = segment.get('carrierCode', '')
                        aircraft = segment.get('aircraft', {}).get('code', '')
                        
                        # Parse departure and arrival dates/times
                        departure_date = departure.get('at', '').split('T')[0]
                        departure_time = departure.get('at', '').split('T')[1].split('+')[0].split('-')[0]
                        arrival_date = arrival.get('at', '').split('T')[0]
                        arrival_time = arrival.get('at', '').split('T')[1].split('+')[0].split('-')[0]
                        
                        segments.append({
                            'departure_airport': departure.get('iataCode', ''),
                            'departure_terminal': departure.get('terminal', ''),
                            'departure_date': departure_date,
                            'departure_time': departure_time,
                            'arrival_airport': arrival.get('iataCode', ''),
                            'arrival_terminal': arrival.get('terminal', ''),
                            'arrival_date': arrival_date,
                            'arrival_time': arrival_time,
                            'airline': carrier,
                            'flight_number': segment.get('number', ''),
                            'aircraft': aircraft,
                            'duration': segment.get('duration', '')
                        })
                
                # Calculate total duration
                total_duration = ''
                if itineraries and 'duration' in itineraries[0]:
                    total_duration = itineraries[0].get('duration', '')
                
                # Extract fare details
                fare_details = {}
                try:
                    fare_details = {
                        'travel_class': offer.get('travelerPricings', [{}])[0].get('fareDetailsBySegment', [{}])[0].get('cabin', ''),
                        'booking_class': offer.get('travelerPricings', [{}])[0].get('fareDetailsBySegment', [{}])[0].get('class', ''),
                        'fare_basis': offer.get('travelerPricings', [{}])[0].get('fareDetailsBySegment', [{}])[0].get('fareBasis', '')
                    }
                except (IndexError, KeyError):
                    pass
                
                # Build the standardized result
                results.append({
                    'id': offer.get('id', ''),
                    'price': float(price.get('total', 0)),
                    'currency': price.get('currency', 'USD'),
                    'segments': segments,
                    'total_duration': total_duration,
                    'passengers': offer.get('numberOfBookableSeats', 1),
                    'cabin_class': fare_details.get('travel_class', 'ECONOMY'),
                    'booking_class': fare_details.get('booking_class', ''),
                    'fare_basis': fare_details.get('fare_basis', ''),
                    'source': 'Amadeus API'
                })
            except Exception as e:
                logger.warning(f"Error parsing flight offer: {e}")
        
        return results
    
    def _parse_hotel_offers(self, offers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse hotel offers data into a standardized format
        
        Args:
            offers: List of hotel offers from Amadeus API
            
        Returns:
            Standardized hotel offer dictionary
        """
        try:
            if not offers:
                return {}
                
            # Take the first offer
            offer = offers[0]
            hotel = offer.get('hotel', {})
            offers_data = offer.get('offers', [{}])[0]
            price = offers_data.get('price', {})
            
            # Get hotel amenities if available
            amenities = []
            if 'amenities' in hotel:
                amenities = hotel.get('amenities', [])
            
            # Get room details
            room_type = ''
            bed_type = ''
            
            if 'room' in offers_data and 'typeEstimated' in offers_data['room']:
                room_type = offers_data['room']['typeEstimated'].get('category', '')
                bed_type = offers_data['room']['typeEstimated'].get('bedType', '')
            
            # Parse cancellation policies
            cancellation_policy = 'Non-refundable'
            if 'policies' in offers_data and 'cancellations' in offers_data['policies']:
                for policy in offers_data['policies'].get('cancellations', []):
                    if policy.get('type') == 'FREE_CANCELLATION':
                        deadline = policy.get('deadline', '')
                        if deadline:
                            cancellation_policy = f"Free cancellation until {deadline}"
                            break
            
            # Build the standardized result
            return {
                'id': hotel.get('hotelId', ''),
                'name': hotel.get('name', ''),
                'chain': hotel.get('chainCode', ''),
                'address': self._format_address(hotel.get('address', {})),
                'city': hotel.get('cityCode', ''),
                'rating': hotel.get('rating', ''),
                'price': float(price.get('total', 0)),
                'currency': price.get('currency', 'USD'),
                'price_per_night': float(price.get('variations', {}).get('average', {}).get('base', 0)),
                'room_type': room_type,
                'bed_type': bed_type,
                'board_type': offers_data.get('boardType', ''),
                'amenities': amenities[:5],  # Limit to first 5 amenities
                'cancellation_policy': cancellation_policy,
                'check_in_date': offers_data.get('checkInDate', ''),
                'check_out_date': offers_data.get('checkOutDate', ''),
                'guests': offers_data.get('guests', {}).get('adults', 1),
                'source': 'Amadeus API'
            }
        except Exception as e:
            logger.debug(f"Error parsing hotel offer: {e}")
            return {}
    
    def _format_address(self, address: Dict[str, Any]) -> str:
        """Format hotel address as a string"""
        parts = []
        
        if address.get('lines'):
            parts.extend(address.get('lines', []))
        if address.get('postalCode'):
            parts.append(address.get('postalCode', ''))
        if address.get('cityName'):
            parts.append(address.get('cityName', ''))
        if address.get('countryName'):
            parts.append(address.get('countryName', ''))
            
        return ', '.join(parts)
    
    def get_city_code(self, city_name: str) -> Optional[str]:
        """
        Get IATA city code for a given city name using Amadeus API.
        
        Args:
            city_name: Name of the city
            
        Returns:
            IATA city code or None if not found
        """
        logger.info(f"Getting IATA code for city: {city_name}")
        
        if not self.client:
            logger.error("Amadeus client not initialized")
            return None
        
        retries = 0
        while retries < self.max_retries:
            try:
                # Try using the dedicated cities endpoint first
                response = self.client.reference_data.locations.cities.get(
                    keyword=city_name,
                    max=1
                )
                
                # Check if we got any results
                if hasattr(response, 'data') and response.data:
                    city_code = response.data[0].get('iataCode')
                    if city_code:
                        return city_code
                
                # If no results from cities endpoint, try general locations endpoint
                response = self.client.reference_data.locations.get(
                    keyword=city_name,
                    subType=Location.CITY
                )
                
                if hasattr(response, 'data') and response.data:
                    for location in response.data:
                        if location.get('subType') == 'CITY':
                            return location.get('iataCode')
                    
                    # If no city found but we have other locations, return the first one's code
                    return response.data[0].get('iataCode')
                    
                return None
                
            except ResponseError as error:
                logger.error(f"Amadeus API error: {error}")
                # If rate limited, wait and retry
                if str(error).startswith('[429]'):
                    retries += 1
                    sleep_time = self.rate_limit_delay * (2 ** retries)  # Exponential backoff
                    logger.warning(f"Rate limited. Retrying in {sleep_time} seconds")
                    time.sleep(sleep_time)
                    continue
                return None
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to get city code after {self.max_retries} attempts: {e}")
                    return None
                
                logger.warning(f"Attempt {retries} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
