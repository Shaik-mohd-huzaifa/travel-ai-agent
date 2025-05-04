import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import random
import time
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common user agents for rotating
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
]

class ScraperBase:
    """Base class with common scraping functionality"""
    
    def __init__(self, timeout=10, max_retries=3):
        self.timeout = timeout
        self.max_retries = max_retries
        
    def get_random_user_agent(self):
        """Return a random user agent to avoid detection"""
        return random.choice(USER_AGENTS)
    
    def make_request(self, url, headers=None, params=None):
        """Make HTTP request with retry logic"""
        if headers is None:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml'
            }
            
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to retrieve {url} after {self.max_retries} attempts: {e}")
                    return None
                
                logger.warning(f"Attempt {retries} failed. Retrying in {retries * 2} seconds...")
                time.sleep(retries * 2)
    
    def parse_html(self, html_content):
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if text is None:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def extract_price(self, price_text):
        """Extract numeric price from text"""
        if not price_text:
            return None
            
        price_match = re.search(r'[\$\€\£\₹]?\s*?(\d+[,\.\d]*)', price_text)
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                return None
        return None

class AirbnbScraper(ScraperBase):
    """Scraper for Airbnb"""
    
    def __init__(self, timeout=10, max_retries=3):
        super().__init__(timeout, max_retries)
        self.base_url = "https://www.airbnb.com"
        
    def search_hotels(self, location, check_in, check_out, guests=2, rooms=1, filters=None):
        """
        Search for hotels on Airbnb
        
        Args:
            location: Destination
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            guests: Number of guests
            rooms: Number of rooms
            filters: Dictionary of additional filters
            
        Returns:
            List of parsed hotel results
        """
        search_url = f"{self.base_url}/s/{location}/homes"
        
        params = {
            'checkin': check_in,
            'checkout': check_out,
            'adults': guests,
            'source': 'structured_search_input_header'
        }
        
        # Add any additional filters
        if filters:
            for key, value in filters.items():
                params[key] = value
                
        logger.info(f"Searching Airbnb for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = self.parse_html(response.content)
        
        # Find the JSON data embedded in the page
        try:
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                if "data-state" in script.attrs and "SearchResults" in script.text:
                    data = json.loads(script.text)
                    if "results" in data:
                        for item in data["results"]:
                            hotel = self._parse_hotel_item(item)
                            if hotel:
                                results.append(hotel)
                        break
        except Exception as e:
            logger.error(f"Error parsing Airbnb results: {e}")
            
        # If JSON data extraction fails, try HTML scraping
        if not results:
            try:
                listings = soup.select("div[itemprop='itemListElement']")
                for listing in listings:
                    try:
                        name = self.clean_text(listing.select_one("div[data-testid='listing-card-title']").text)
                        price_elem = listing.select_one("span[data-testid='price-and-total']")
                        price = self.extract_price(price_elem.text) if price_elem else None
                        url = listing.select_one("a")["href"]
                        if not url.startswith("http"):
                            url = self.base_url + url
                            
                        rating_elem = listing.select_one("span[aria-hidden='true'][class*='rating']")
                        rating = float(rating_elem.text.split()[0]) if rating_elem else None
                        
                        results.append({
                            "name": name,
                            "url": url,
                            "price": price,
                            "currency": "USD",  # Default assumption
                            "rating": rating,
                            "source": "Airbnb"
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing individual Airbnb listing: {e}")
            except Exception as e:
                logger.error(f"Error with HTML fallback scraping for Airbnb: {e}")
        
        return self._filter_and_rank_results(results)
    
    def _parse_hotel_item(self, item):
        """Parse a single hotel item from JSON data"""
        try:
            return {
                "name": item.get("name", ""),
                "url": self.base_url + item.get("url", ""),
                "price": item.get("price", {}).get("rate", {}).get("amount"),
                "currency": item.get("price", {}).get("rate", {}).get("currency", "USD"),
                "rating": item.get("rating", {}).get("value"),
                "reviews_count": item.get("reviewsCount"),
                "image_url": item.get("image", {}).get("url"),
                "location": item.get("city", ""),
                "source": "Airbnb"
            }
        except Exception as e:
            logger.debug(f"Error parsing Airbnb hotel item: {e}")
            return None
            
    def _filter_and_rank_results(self, results, top_n=3):
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # Sort by rating (descending) then price (ascending)
        sorted_results = sorted(
            [r for r in results if r.get("rating") is not None], 
            key=lambda x: (-1 * (x.get("rating") or 0), x.get("price") or float('inf'))
        )
        
        return sorted_results[:top_n]

class AgodaScraper(ScraperBase):
    """Scraper for Agoda"""
    
    def __init__(self, timeout=10, max_retries=3):
        super().__init__(timeout, max_retries)
        self.base_url = "https://www.agoda.com"
        
    def search_hotels(self, location, check_in, check_out, guests=2, rooms=1, filters=None):
        """Search for hotels on Agoda"""
        # Convert date format to Agoda's expected format
        check_in_obj = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_obj = datetime.strptime(check_out, "%Y-%m-%d")
        check_in_formatted = check_in_obj.strftime("%d-%m-%Y")
        check_out_formatted = check_out_obj.strftime("%d-%m-%Y")
        
        search_url = f"{self.base_url}/en-us/search"
        
        params = {
            'city': location,
            'checkIn': check_in_formatted,
            'checkOut': check_out_formatted,
            'rooms': rooms,
            'adults': guests
        }
        
        # Add any additional filters
        if filters:
            for key, value in filters.items():
                params[key] = value
                
        logger.info(f"Searching Agoda for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = self.parse_html(response.content)
        
        # Try to find hotel cards
        hotel_cards = soup.select("div.PropertyCard")
        
        for card in hotel_cards:
            try:
                name_elem = card.select_one("h3.PropertyCard__HotelName")
                name = self.clean_text(name_elem.text) if name_elem else ""
                
                url_elem = card.select_one("a.PropertyCard__Link")
                url = url_elem["href"] if url_elem and "href" in url_elem.attrs else ""
                if url and not url.startswith("http"):
                    url = self.base_url + url
                
                price_elem = card.select_one("span.PropertyCardPrice__Value")
                price = self.extract_price(price_elem.text) if price_elem else None
                
                rating_elem = card.select_one("div.Typographystyled__TypographyStyled-sc-j18mtu-0.hTkvyT")
                rating = float(rating_elem.text) if rating_elem else None
                
                results.append({
                    "name": name,
                    "url": url,
                    "price": price,
                    "rating": rating,
                    "source": "Agoda"
                })
            except Exception as e:
                logger.debug(f"Error parsing Agoda hotel card: {e}")
        
        return self._filter_and_rank_results(results)
    
    def _filter_and_rank_results(self, results, top_n=3):
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # Sort by rating (descending) then price (ascending)
        sorted_results = sorted(
            [r for r in results if r.get("name")], 
            key=lambda x: (-1 * (x.get("rating") or 0), x.get("price") or float('inf'))
        )
        
        return sorted_results[:top_n]

class ExpediaScraper(ScraperBase):
    """Scraper for Expedia"""
    
    def __init__(self, timeout=10, max_retries=3):
        super().__init__(timeout, max_retries)
        self.base_url = "https://www.expedia.com"
        
    def search_hotels(self, location, check_in, check_out, guests=2, rooms=1, filters=None):
        """Search for hotels on Expedia"""
        search_url = f"{self.base_url}/Hotel-Search"
        
        # Format dates for Expedia
        params = {
            'destination': location,
            'startDate': check_in,
            'endDate': check_out,
            'rooms': rooms,
            'adults': guests
        }
        
        # Add any additional filters
        if filters:
            for key, value in filters.items():
                params[key] = value
                
        logger.info(f"Searching Expedia for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = self.parse_html(response.content)
        
        # Try to extract JSON data first
        try:
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                if "data-state" in script.attrs:
                    try:
                        data = json.loads(script.string)
                        if "hotels" in data:
                            for hotel_id, hotel_data in data["hotels"].items():
                                hotel = {
                                    "name": hotel_data.get("name", ""),
                                    "url": f"{self.base_url}/hotel/{hotel_id}",
                                    "price": hotel_data.get("price", {}).get("displayPrice"),
                                    "rating": hotel_data.get("star"),
                                    "source": "Expedia"
                                }
                                results.append(hotel)
                            break
                    except (json.JSONDecodeError, AttributeError):
                        pass
        except Exception as e:
            logger.error(f"Error extracting Expedia JSON data: {e}")
        
        # If JSON extraction failed, try HTML parsing
        if not results:
            try:
                hotel_cards = soup.select("div.uitk-card")
                for card in hotel_cards:
                    try:
                        name_elem = card.select_one("h3")
                        name = self.clean_text(name_elem.text) if name_elem else ""
                        
                        url_elem = card.select_one("a.uitk-card-link")
                        url = url_elem["href"] if url_elem and "href" in url_elem.attrs else ""
                        if url and not url.startswith("http"):
                            url = self.base_url + url
                        
                        price_elem = card.select_one("div[data-stid='content-hotel-lead-price']")
                        price = self.extract_price(price_elem.text) if price_elem else None
                        
                        rating_elem = card.select_one("span.uitk-rating-average")
                        rating = float(rating_elem.text.split('/')[0]) if rating_elem else None
                        
                        results.append({
                            "name": name,
                            "url": url,
                            "price": price,
                            "rating": rating,
                            "source": "Expedia"
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing Expedia hotel card: {e}")
            except Exception as e:
                logger.error(f"Error with HTML fallback scraping for Expedia: {e}")
        
        return self._filter_and_rank_results(results)
    
    def _filter_and_rank_results(self, results, top_n=3):
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # Sort by rating (descending) then price (ascending)
        sorted_results = sorted(
            [r for r in results if r.get("name")], 
            key=lambda x: (-1 * (x.get("rating") or 0), x.get("price") or float('inf'))
        )
        
        return sorted_results[:top_n]

class SkyscannerScraper(ScraperBase):
    """Scraper for Skyscanner (flights)"""
    
    def __init__(self, timeout=15, max_retries=3):
        super().__init__(timeout, max_retries)
        self.base_url = "https://www.skyscanner.com"
        
    def search_flights(self, origin, destination, date, return_date=None, adults=1, filters=None):
        """Search for flights on Skyscanner"""
        # Format dates for Skyscanner (YYMMDD)
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%y%m%d")
        
        return_param = ""
        if return_date:
            return_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
            return_formatted = return_date_obj.strftime("%y%m%d")
            return_param = f"/{return_formatted}"
        
        search_url = f"{self.base_url}/transport/flights/{origin}/{destination}/{date_formatted}{return_param}/"
        
        params = {
            'adults': adults,
            'adultsv2': adults,
            'cabinclass': 'economy'  # Default cabin class
        }
        
        # Add any additional filters
        if filters:
            for key, value in filters.items():
                params[key] = value
                
        logger.info(f"Searching Skyscanner for flights from {origin} to {destination} on {date}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = self.parse_html(response.content)
        
        # Try to extract data from the page
        try:
            flight_cards = soup.select("div[data-testid='itinerary-card']")
            for card in flight_cards:
                try:
                    # Extract airline
                    airline_elem = card.select_one("div[data-testid='flight-info'] span")
                    airline = self.clean_text(airline_elem.text) if airline_elem else ""
                    
                    # Extract price
                    price_elem = card.select_one("span[data-testid='price']")
                    price = self.extract_price(price_elem.text) if price_elem else None
                    
                    # Extract flight duration
                    duration_elem = card.select_one("span[data-testid='duration']")
                    duration = self.clean_text(duration_elem.text) if duration_elem else ""
                    
                    # Extract departure and arrival times
                    times_elem = card.select_one("span[data-testid='flight-times']")
                    times = self.clean_text(times_elem.text) if times_elem else ""
                    
                    # Extract stops
                    stops_elem = card.select_one("span[data-testid='stops']")
                    stops = self.clean_text(stops_elem.text) if stops_elem else "Direct"
                    
                    results.append({
                        "airline": airline,
                        "price": price,
                        "duration": duration,
                        "times": times,
                        "stops": stops,
                        "origin": origin,
                        "destination": destination,
                        "date": date,
                        "return_date": return_date,
                        "source": "Skyscanner"
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Skyscanner flight card: {e}")
        except Exception as e:
            logger.error(f"Error parsing Skyscanner results: {e}")
            
        return self._filter_and_rank_results(results)
    
    def _filter_and_rank_results(self, results, top_n=3):
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # For flights, sort by number of stops (ascending) then price (ascending)
        def count_stops(stops_text):
            if not stops_text or stops_text.lower() == "direct":
                return 0
            try:
                return int(re.search(r'(\d+)', stops_text).group(1))
            except (AttributeError, ValueError):
                return 999  # High number for unknown
                
        sorted_results = sorted(
            [r for r in results if r.get("price")], 
            key=lambda x: (count_stops(x.get("stops", "")), x.get("price") or float('inf'))
        )
        
        return sorted_results[:top_n]

class MultiSiteScraper:
    """Unified scraper that can search across multiple travel sites"""
    
    def __init__(self):
        self.airbnb_scraper = AirbnbScraper()
        self.agoda_scraper = AgodaScraper()
        self.expedia_scraper = ExpediaScraper()
        self.skyscanner_scraper = SkyscannerScraper()
    
    def search_hotels(self, location, check_in, check_out, guests=2, rooms=1, filters=None, max_workers=3):
        """
        Search for hotels across multiple sites
        
        Args:
            location: Destination name
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            guests: Number of guests
            rooms: Number of rooms
            filters: Dictionary of additional filters
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with results from each site
        """
        results = {}
        
        # Define scraping tasks
        def scrape_airbnb():
            return self.airbnb_scraper.search_hotels(location, check_in, check_out, guests, rooms, filters)
            
        def scrape_agoda():
            return self.agoda_scraper.search_hotels(location, check_in, check_out, guests, rooms, filters)
            
        def scrape_expedia():
            return self.expedia_scraper.search_hotels(location, check_in, check_out, guests, rooms, filters)
        
        # Execute tasks in parallel
        tasks = [scrape_airbnb, scrape_agoda, scrape_expedia]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            task_results = list(executor.map(lambda task: task(), tasks))
        
        # Combine results
        results["airbnb"] = task_results[0]
        results["agoda"] = task_results[1]
        results["expedia"] = task_results[2]
        
        return results
    
    def search_flights(self, origin, destination, date, return_date=None, adults=1, filters=None):
        """
        Search for flights on Skyscanner
        
        Args:
            origin: Origin airport/city code
            destination: Destination airport/city code
            date: Departure date (YYYY-MM-DD)
            return_date: Return date (YYYY-MM-DD), optional
            adults: Number of adult passengers
            filters: Dictionary of additional filters
            
        Returns:
            List of flight results
        """
        return {
            "skyscanner": self.skyscanner_scraper.search_flights(
                origin, destination, date, return_date, adults, filters
            )
        }
    
    def combined_search(self, search_type, **kwargs):
        """
        Perform a combined search based on search type
        
        Args:
            search_type: Either 'hotels' or 'flights'
            **kwargs: Search parameters
            
        Returns:
            Combined search results
        """
        if search_type == 'hotels':
            return self.search_hotels(**kwargs)
        elif search_type == 'flights':
            return self.search_flights(**kwargs)
        else:
            raise ValueError("Search type must be either 'hotels' or 'flights'")


# Usage example
if __name__ == "__main__":
    scraper = MultiSiteScraper()
    
    # Example hotel search
    hotel_results = scraper.search_hotels(
        location="ooty", 
        check_in="2025-05-23", 
        check_out="2025-05-27", 
        guests=2
    )
    
    print("\n=== HOTEL RESULTS ===")
    for site, results in hotel_results.items():
        print(f"\n{site.upper()} TOP RESULTS:")
        for i, hotel in enumerate(results, 1):
            print(f"{i}. {hotel['name']} - {'${:.2f}'.format(hotel['price']) if hotel.get('price') else 'Price N/A'}")
            print(f"   Rating: {hotel.get('rating', 'N/A')} | URL: {hotel.get('url', 'N/A')}")
    
    # Example flight search
    flight_results = scraper.search_flights(
        origin="DEL",
        destination="BOM", 
        date="2025-05-23", 
        return_date="2025-05-27"
    )
    
    print("\n=== FLIGHT RESULTS ===")
    for site, results in flight_results.items():
        print(f"\n{site.upper()} TOP RESULTS:")
        for i, flight in enumerate(results, 1):
            print(f"{i}. {flight.get('airline', 'Unknown')} - {'${:.2f}'.format(flight['price']) if flight.get('price') else 'Price N/A'}")
            print(f"   Duration: {flight.get('duration', 'N/A')} | Stops: {flight.get('stops', 'N/A')}")
            print(f"   Times: {flight.get('times', 'N/A')}")

