"""
Flight scraping utility for Travel AI assistant.

This module provides functions to scrape flight information from 
popular flight booking sites based on user preferences.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import logging
import random
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

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


class FlightScraper:
    """A class for scraping flight information from various websites"""
    
    def __init__(self, timeout=15, max_retries=3):
        self.timeout = timeout
        self.max_retries = max_retries
    
    def get_random_user_agent(self) -> str:
        """Return a random user agent to avoid detection"""
        return random.choice(USER_AGENTS)
    
    def make_request(self, url: str, headers=None, params=None) -> Optional[requests.Response]:
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
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if text is None:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def extract_price(self, price_text: str) -> Optional[float]:
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
    
    # SKYSCANNER SCRAPING
    def scrape_skyscanner(self, origin: str, destination: str, date: str, 
                          return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Scrape flight listings from Skyscanner"""
        base_url = "https://www.skyscanner.com"
        
        # Format dates for Skyscanner (YYMMDD)
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%y%m%d")
        
        return_param = ""
        if return_date:
            return_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
            return_formatted = return_date_obj.strftime("%y%m%d")
            return_param = f"/{return_formatted}"
        
        search_url = f"{base_url}/transport/flights/{origin}/{destination}/{date_formatted}{return_param}/"
        
        params = {
            'adults': adults,
            'adultsv2': adults,
            'cabinclass': 'economy'  # Default cabin class
        }
        
        logger.info(f"Searching Skyscanner for flights from {origin} to {destination} on {date}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
    
    # KAYAK SCRAPING
    def scrape_kayak(self, origin: str, destination: str, date: str, 
                    return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Scrape flight listings from Kayak"""
        base_url = "https://www.kayak.com"
        search_url = f"{base_url}/flights/{origin}-{destination}/{date}"
        
        if return_date:
            search_url += f"/{return_date}"
        
        params = {
            'sort': 'bestflight_a',
            'fs': 'stops=0',
            'adults': adults
        }
        
        logger.info(f"Searching Kayak for flights from {origin} to {destination} on {date}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract flight results
        try:
            flight_cards = soup.select("div[class*='resultWrapper']")
            for card in flight_cards:
                try:
                    # Extract airline
                    airline_elem = card.select_one("div[class*='codeshares-airline-names']")
                    airline = self.clean_text(airline_elem.text) if airline_elem else ""
                    
                    # Extract price
                    price_elem = card.select_one("span[class*='price-text']")
                    price = self.extract_price(price_elem.text) if price_elem else None
                    
                    # Extract flight duration
                    duration_elem = card.select_one("div[class*='duration']")
                    duration = self.clean_text(duration_elem.text) if duration_elem else ""
                    
                    # Extract departure time
                    dep_time_elem = card.select_one("span[class*='depart-time']")
                    dep_time = self.clean_text(dep_time_elem.text) if dep_time_elem else ""
                    
                    # Extract arrival time
                    arr_time_elem = card.select_one("span[class*='arrival-time']")
                    arr_time = self.clean_text(arr_time_elem.text) if arr_time_elem else ""
                    
                    # Extract stops
                    stops_elem = card.select_one("span[class*='stops-text']")
                    stops = self.clean_text(stops_elem.text) if stops_elem else "Direct"
                    
                    results.append({
                        "airline": airline,
                        "price": price,
                        "duration": duration,
                        "departure_time": dep_time,
                        "arrival_time": arr_time,
                        "stops": stops,
                        "origin": origin,
                        "destination": destination,
                        "date": date,
                        "return_date": return_date,
                        "source": "Kayak"
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Kayak flight card: {e}")
        except Exception as e:
            logger.error(f"Error parsing Kayak results: {e}")
            
        return self._filter_and_rank_results(results)
    
    # EXPEDIA FLIGHTS SCRAPING
    def scrape_expedia_flights(self, origin: str, destination: str, date: str, 
                              return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Scrape flight listings from Expedia"""
        base_url = "https://www.expedia.com"
        search_url = f"{base_url}/Flights-Search"
        
        params = {
            'flight-type': 'on',
            'mode': 'search',
            'trip': 'roundtrip' if return_date else 'oneway',
            'leg1': f"from:{origin},to:{destination},departure:{date}",
            'options': f"cabinclass:economy,sortby:price,carrier:*",
            'travelers': f"adults:{adults}"
        }
        
        if return_date:
            params['leg2'] = f"from:{destination},to:{origin},departure:{return_date}"
            
        logger.info(f"Searching Expedia for flights from {origin} to {destination} on {date}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract flight data
        try:
            # First try JSON data if available
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                if "data-state" in script.attrs:
                    try:
                        data = json.loads(script.string)
                        if "offers" in data:
                            for offer in data["offers"]:
                                try:
                                    result = {
                                        "airline": offer.get("airlineName", ""),
                                        "price": offer.get("totalPrice", {}).get("amount"),
                                        "duration": offer.get("formattedDuration", ""),
                                        "departure_time": offer.get("departureTime", ""),
                                        "arrival_time": offer.get("arrivalTime", ""),
                                        "stops": f"{offer.get('stopCount', 0)} stops",
                                        "origin": origin,
                                        "destination": destination,
                                        "date": date,
                                        "return_date": return_date,
                                        "source": "Expedia"
                                    }
                                    results.append(result)
                                except Exception as e:
                                    logger.debug(f"Error parsing Expedia flight offer: {e}")
                            break
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.debug(f"Error decoding Expedia JSON: {e}")
                        
            # If JSON parsing failed, try HTML parsing
            if not results:
                flight_cards = soup.select("div.uitk-card")
                for card in flight_cards:
                    try:
                        # Extract airline
                        airline_elem = card.select_one("div[data-test-id='airline-name']")
                        airline = self.clean_text(airline_elem.text) if airline_elem else ""
                        
                        # Extract price
                        price_elem = card.select_one("span[data-test-id='price-column']")
                        price = self.extract_price(price_elem.text) if price_elem else None
                        
                        # Extract duration
                        duration_elem = card.select_one("div[data-test-id='journey-duration']")
                        duration = self.clean_text(duration_elem.text) if duration_elem else ""
                        
                        # Extract stops
                        stops_elem = card.select_one("div[data-test-id='stops']")
                        stops = self.clean_text(stops_elem.text) if stops_elem else "Direct"
                        
                        results.append({
                            "airline": airline,
                            "price": price,
                            "duration": duration,
                            "stops": stops,
                            "origin": origin,
                            "destination": destination,
                            "date": date,
                            "return_date": return_date,
                            "source": "Expedia"
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing Expedia flight card: {e}")
                        
        except Exception as e:
            logger.error(f"Error parsing Expedia flight results: {e}")
            
        return self._filter_and_rank_results(results)
    
    # GOOGLE FLIGHTS SCRAPING (Note: Google might block scraping attempts)
    def scrape_google_flights(self, origin: str, destination: str, date: str, 
                             return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Scrape flight listings from Google Flights (limited functionality)"""
        base_url = "https://www.google.com"
        search_url = f"{base_url}/travel/flights"
        
        params = {
            'hl': 'en',
            'gl': 'us',
            'curr': 'USD',
            'tfs': 'CAEyACgA',  # Default value
            'q': f"flights from {origin} to {destination}",
            'd': date,
            'r': return_date if return_date else 'undefined',
            'p': adults,
            'sort': 'price'
        }
        
        logger.info(f"Searching Google Flights for flights from {origin} to {destination} on {date}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Google Flights is particularly difficult to scrape as it uses React/JS heavily
        # This is a simplified approach that may not work consistently
        try:
            flight_cards = soup.select("div[role='listitem']")
            for card in flight_cards:
                try:
                    price_elem = card.select_one("div[aria-label*='$']")
                    if not price_elem:
                        continue
                        
                    price = self.extract_price(price_elem.get('aria-label', ''))
                    
                    # Extract airline and other details
                    info_elems = card.select("div[role='row']")
                    airline = ""
                    duration = ""
                    stops = "Direct"
                    
                    if info_elems and len(info_elems) > 0:
                        info_text = self.clean_text(info_elems[0].text)
                        
                        # Try to extract airline from the first part of text
                        airline_pattern = r'^([A-Za-z\s]+)'
                        airline_match = re.search(airline_pattern, info_text)
                        if airline_match:
                            airline = airline_match.group(1).strip()
                            
                        # Try to extract duration
                        duration_pattern = r'(\d+h\s*\d*m)'
                        duration_match = re.search(duration_pattern, info_text)
                        if duration_match:
                            duration = duration_match.group(1)
                            
                        # Check if flight is non-stop or has stops
                        if 'stop' in info_text.lower():
                            stops_pattern = r'(\d+)\s+stop'
                            stops_match = re.search(stops_pattern, info_text)
                            if stops_match:
                                stops = f"{stops_match.group(1)} stops"
                    
                    results.append({
                        "airline": airline,
                        "price": price,
                        "duration": duration,
                        "stops": stops,
                        "origin": origin,
                        "destination": destination,
                        "date": date,
                        "return_date": return_date,
                        "source": "Google Flights"
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Google Flights card: {e}")
        except Exception as e:
            logger.error(f"Error parsing Google Flights results: {e}")
            
        return self._filter_and_rank_results(results)
    
    # PRICELINE SCRAPING
    def scrape_priceline(self, origin: str, destination: str, date: str, 
                        return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Scrape flight listings from Priceline"""
        base_url = "https://www.priceline.com"
        search_url = f"{base_url}/m/fly/search"
        
        # Format dates for URL
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%Y-%m-%d")
        
        params = {
            'cabin-class': 'ECO',
            'adults': adults,
            'from': origin,
            'to': destination,
            'date': date_formatted,
        }
        
        if return_date:
            return_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
            return_date_formatted = return_date_obj.strftime("%Y-%m-%d")
            params['return-date'] = return_date_formatted
            
        logger.info(f"Searching Priceline for flights from {origin} to {destination} on {date}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract flight data
        try:
            flight_cards = soup.select("div.sc-eSePXI, div.tile-generic-content")
            for card in flight_cards:
                try:
                    # Extract airline
                    airline_elem = card.select_one("div.sc-dUbtfd, span.airline-name")
                    airline = self.clean_text(airline_elem.text) if airline_elem else ""
                    
                    # Extract price
                    price_elem = card.select_one("span.sc-TFwJa, span.total-price")
                    price = self.extract_price(price_elem.text) if price_elem else None
                    
                    # Extract duration
                    duration_elem = card.select_one("div.sc-kqlzXE, span.duration")
                    duration = self.clean_text(duration_elem.text) if duration_elem else ""
                    
                    # Extract departure and arrival times
                    times_elem = card.select_one("div.sc-OxbzP, div.flight-times")
                    times = self.clean_text(times_elem.text) if times_elem else ""
                    
                    # Extract stops
                    stops_elem = card.select_one("div.sc-lnrBVv, span.stops")
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
                        "source": "Priceline"
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Priceline flight card: {e}")
        except Exception as e:
            logger.error(f"Error parsing Priceline results: {e}")
            
        return self._filter_and_rank_results(results)
    
    def _filter_and_rank_results(self, results: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # For flights, sort by number of stops (ascending) then price (ascending)
        def count_stops(stops_text):
            if not stops_text or stops_text.lower() == "direct" or stops_text.lower() == "nonstop":
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
    
    def search_flights_all_sites(self, origin: str, destination: str, date: str,
                               return_date: Optional[str] = None, adults: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Search for flights across all supported sites"""
        results = {}
        
        # Search each site
        try:
            results["skyscanner"] = self.scrape_skyscanner(origin, destination, date, return_date, adults)
        except Exception as e:
            logger.error(f"Error searching Skyscanner: {e}")
            results["skyscanner"] = []
            
        try:
            results["kayak"] = self.scrape_kayak(origin, destination, date, return_date, adults)
        except Exception as e:
            logger.error(f"Error searching Kayak: {e}")
            results["kayak"] = []
            
        try:
            results["expedia"] = self.scrape_expedia_flights(origin, destination, date, return_date, adults)
        except Exception as e:
            logger.error(f"Error searching Expedia: {e}")
            results["expedia"] = []
            
        try:
            results["google_flights"] = self.scrape_google_flights(origin, destination, date, return_date, adults)
        except Exception as e:
            logger.error(f"Error searching Google Flights: {e}")
            results["google_flights"] = []
            
        try:
            results["priceline"] = self.scrape_priceline(origin, destination, date, return_date, adults)
        except Exception as e:
            logger.error(f"Error searching Priceline: {e}")
            results["priceline"] = []
            
        return results


# Example usage
if __name__ == "__main__":
    scraper = FlightScraper()
    
    # Example flight search
    flight_results = scraper.search_flights_all_sites(
        origin="DEL",  # Delhi
        destination="BOM",  # Mumbai
        date="2025-05-23",
        return_date="2025-05-27",
        adults=1
    )
    
    print("\n=== FLIGHT RESULTS ===")
    for site, results in flight_results.items():
        print(f"\n{site.upper()} TOP RESULTS:")
        for i, flight in enumerate(results, 1):
            print(f"{i}. {flight.get('airline', 'Unknown')} - {'${:.2f}'.format(flight['price']) if flight.get('price') else 'Price N/A'}")
            print(f"   Duration: {flight.get('duration', 'N/A')} | Stops: {flight.get('stops', 'N/A')}")
            if 'times' in flight:
                print(f"   Times: {flight.get('times', 'N/A')}")
            elif 'departure_time' in flight and 'arrival_time' in flight:
                print(f"   Departure: {flight.get('departure_time', 'N/A')} | Arrival: {flight.get('arrival_time', 'N/A')}")
