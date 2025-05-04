"""
Hotel scraping utility for Travel AI assistant.

This module provides functions to scrape hotel information from 
popular hotel booking sites like Booking.com, Airbnb, Agoda, Expedia, and Hotels.com based on user preferences.
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


class HotelScraper:
    """A class for scraping hotel information from various websites"""
    
    def __init__(self, timeout=10, max_retries=3):
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
    
    # AIRBNB SCRAPING
    def scrape_airbnb(self, location: str, check_in: str, check_out: str, 
                      guests: int = 2, rooms: int = 1) -> List[Dict[str, Any]]:
        """Scrape hotel listings from Airbnb"""
        base_url = "https://www.airbnb.com"
        search_url = f"{base_url}/s/{location}/homes"
        
        params = {
            'checkin': check_in,
            'checkout': check_out,
            'adults': guests,
            'source': 'structured_search_input_header'
        }
        
        logger.info(f"Searching Airbnb for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the JSON data embedded in the page
        try:
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                if "data-state" in script.attrs and "SearchResults" in script.text:
                    data = json.loads(script.text)
                    if "results" in data:
                        for item in data["results"]:
                            try:
                                hotel = {
                                    "name": item.get("name", ""),
                                    "url": base_url + item.get("url", ""),
                                    "price": item.get("price", {}).get("rate", {}).get("amount"),
                                    "currency": item.get("price", {}).get("rate", {}).get("currency", "USD"),
                                    "rating": item.get("rating", {}).get("value"),
                                    "reviews_count": item.get("reviewsCount"),
                                    "image_url": item.get("image", {}).get("url"),
                                    "location": item.get("city", ""),
                                    "source": "Airbnb"
                                }
                                results.append(hotel)
                            except Exception as e:
                                logger.debug(f"Error parsing Airbnb hotel item: {e}")
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
                            url = base_url + url
                            
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
    
    # BOOKING.COM SCRAPING
    def scrape_booking(self, location: str, check_in: str, check_out: str,
                       guests: int = 2, rooms: int = 1) -> List[Dict[str, Any]]:
        """Scrape hotel listings from Booking.com"""
        base_url = "https://www.booking.com"
        search_url = f"{base_url}/searchresults.html"
        
        # Convert dates to Booking.com format (YYYY-MM-DD)
        check_in_obj = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_obj = datetime.strptime(check_out, "%Y-%m-%d")
        
        params = {
            'ss': location,
            'checkin': check_in,
            'checkout': check_out,
            'group_adults': guests,
            'no_rooms': rooms,
            'selected_currency': 'USD',
            'lang': 'en-us'
        }
        
        logger.info(f"Searching Booking.com for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Search for hotel cards
        hotel_cards = soup.select("div.sr_property_block")
        
        for card in hotel_cards:
            try:
                name_elem = card.select_one("span.sr-hotel__name")
                name = self.clean_text(name_elem.text) if name_elem else ""
                
                url_elem = card.select_one("a.hotel_name_link")
                url = url_elem["href"] if url_elem and "href" in url_elem.attrs else ""
                if url and not url.startswith("http"):
                    url = base_url + url
                
                price_elem = card.select_one("div.bui-price-display__value")
                price = self.extract_price(price_elem.text) if price_elem else None
                
                rating_elem = card.select_one("div.bui-review-score__badge")
                rating = float(rating_elem.text) if rating_elem else None
                
                location_elem = card.select_one("div.sr_card_address_line")
                location = self.clean_text(location_elem.text) if location_elem else ""
                
                results.append({
                    "name": name,
                    "url": url,
                    "price": price,
                    "rating": rating,
                    "location": location,
                    "source": "Booking.com"
                })
            except Exception as e:
                logger.debug(f"Error parsing Booking.com hotel card: {e}")
        
        return self._filter_and_rank_results(results)
    
    # AGODA SCRAPING
    def scrape_agoda(self, location: str, check_in: str, check_out: str,
                    guests: int = 2, rooms: int = 1) -> List[Dict[str, Any]]:
        """Scrape hotel listings from Agoda"""
        base_url = "https://www.agoda.com"
        search_url = f"{base_url}/en-us/search"
        
        # Convert date format to Agoda's expected format
        check_in_obj = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_obj = datetime.strptime(check_out, "%Y-%m-%d")
        check_in_formatted = check_in_obj.strftime("%d-%m-%Y")
        check_out_formatted = check_out_obj.strftime("%d-%m-%Y")
        
        params = {
            'city': location,
            'checkIn': check_in_formatted,
            'checkOut': check_out_formatted,
            'rooms': rooms,
            'adults': guests
        }
        
        logger.info(f"Searching Agoda for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find hotel cards
        hotel_cards = soup.select("div.PropertyCard")
        
        for card in hotel_cards:
            try:
                name_elem = card.select_one("h3.PropertyCard__HotelName")
                name = self.clean_text(name_elem.text) if name_elem else ""
                
                url_elem = card.select_one("a.PropertyCard__Link")
                url = url_elem["href"] if url_elem and "href" in url_elem.attrs else ""
                if url and not url.startswith("http"):
                    url = base_url + url
                
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
    
    # EXPEDIA SCRAPING
    def scrape_expedia(self, location: str, check_in: str, check_out: str,
                      guests: int = 2, rooms: int = 1) -> List[Dict[str, Any]]:
        """Scrape hotel listings from Expedia"""
        base_url = "https://www.expedia.com"
        search_url = f"{base_url}/Hotel-Search"
        
        params = {
            'destination': location,
            'startDate': check_in,
            'endDate': check_out,
            'rooms': rooms,
            'adults': guests
        }
        
        logger.info(f"Searching Expedia for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
                                    "url": f"{base_url}/hotel/{hotel_id}",
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
                            url = base_url + url
                        
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
    
    # HOTELS.COM SCRAPING
    def scrape_hotels_com(self, location: str, check_in: str, check_out: str,
                         guests: int = 2, rooms: int = 1) -> List[Dict[str, Any]]:
        """Scrape hotel listings from Hotels.com"""
        base_url = "https://www.hotels.com"
        search_url = f"{base_url}/search"
        
        params = {
            'destination': location,
            'startDate': check_in,
            'endDate': check_out,
            'rooms': rooms,
            'adults': guests
        }
        
        logger.info(f"Searching Hotels.com for hotels in {location} from {check_in} to {check_out}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Hotels.com uses a similar structure to Expedia
        hotel_cards = soup.select("div.uitk-card")
        for card in hotel_cards:
            try:
                name_elem = card.select_one("h3")
                name = self.clean_text(name_elem.text) if name_elem else ""
                
                url_elem = card.select_one("a.uitk-card-link")
                url = url_elem["href"] if url_elem and "href" in url_elem.attrs else ""
                if url and not url.startswith("http"):
                    url = base_url + url
                
                price_elem = card.select_one("div[data-test-id='price-summary']")
                price = self.extract_price(price_elem.text) if price_elem else None
                
                rating_elem = card.select_one("span.uitk-rating-average")
                rating = float(rating_elem.text.split('/')[0]) if rating_elem else None
                
                results.append({
                    "name": name,
                    "url": url,
                    "price": price,
                    "rating": rating,
                    "source": "Hotels.com"
                })
            except Exception as e:
                logger.debug(f"Error parsing Hotels.com hotel card: {e}")
        
        return self._filter_and_rank_results(results)
    
    def _filter_and_rank_results(self, results: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # Sort by rating (descending) then price (ascending)
        sorted_results = sorted(
            [r for r in results if r.get("name")], 
            key=lambda x: (-1 * (x.get("rating") or 0), x.get("price") or float('inf'))
        )
        
        return sorted_results[:top_n]
    
    def search_hotels_all_sites(self, location: str, check_in: str, check_out: str,
                              guests: int = 2, rooms: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Search for hotels across all supported sites"""
        results = {}
        
        # Search each site
        try:
            results["airbnb"] = self.scrape_airbnb(location, check_in, check_out, guests, rooms)
        except Exception as e:
            logger.error(f"Error searching Airbnb: {e}")
            results["airbnb"] = []
            
        try:
            results["booking"] = self.scrape_booking(location, check_in, check_out, guests, rooms)
        except Exception as e:
            logger.error(f"Error searching Booking.com: {e}")
            results["booking"] = []
            
        try:
            results["agoda"] = self.scrape_agoda(location, check_in, check_out, guests, rooms)
        except Exception as e:
            logger.error(f"Error searching Agoda: {e}")
            results["agoda"] = []
            
        try:
            results["expedia"] = self.scrape_expedia(location, check_in, check_out, guests, rooms)
        except Exception as e:
            logger.error(f"Error searching Expedia: {e}")
            results["expedia"] = []
            
        try:
            results["hotels_com"] = self.scrape_hotels_com(location, check_in, check_out, guests, rooms)
        except Exception as e:
            logger.error(f"Error searching Hotels.com: {e}")
            results["hotels_com"] = []
            
        return results


# Example usage
if __name__ == "__main__":
    scraper = HotelScraper()
    
    # Example hotel search for Ooty
    hotel_results = scraper.search_hotels_all_sites(
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
