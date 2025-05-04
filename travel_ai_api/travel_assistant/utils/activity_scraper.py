"""
Activity scraping utility for Travel AI assistant.

This module provides functions to scrape activities and attractions information from
popular sites like TripAdvisor, Viator, GetYourGuide, etc. based on location.
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


class ActivityScraper:
    """A class for scraping activities and attractions from various websites"""
    
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
    
    # TRIPADVISOR SCRAPING
    def scrape_tripadvisor(self, location: str) -> List[Dict[str, Any]]:
        """Scrape activities from TripAdvisor"""
        base_url = "https://www.tripadvisor.com"
        search_url = f"{base_url}/Search"
        
        params = {
            'q': location,
            'searchType': 'Attractions'
        }
        
        logger.info(f"Searching TripAdvisor for activities in {location}")
        response = self.make_request(search_url, params=params)
        if not response:
            return []
        
        # First find the attractions page for the location
        soup = BeautifulSoup(response.content, 'html.parser')
        attractions_link = None
        
        try:
            # Try to find the "Things to Do" link for the location
            links = soup.select("a.result-title-link")
            for link in links:
                if "Attractions" in link.text or "Things to Do" in link.text:
                    attractions_link = link.get('href')
                    if attractions_link and not attractions_link.startswith("http"):
                        attractions_link = base_url + attractions_link
                    break
        except Exception as e:
            logger.error(f"Error finding attractions page for {location}: {e}")
        
        results = []
        
        # If we found the attractions page, scrape it
        if attractions_link:
            try:
                attractions_response = self.make_request(attractions_link)
                if attractions_response:
                    attractions_soup = BeautifulSoup(attractions_response.content, 'html.parser')
                    activity_cards = attractions_soup.select("div.alPVI.eNNhq.PgLKC.tnGGX")
                    
                    for card in activity_cards[:10]:  # Limit to top 10
                        try:
                            name_elem = card.select_one("div.XfVdV.o.AIbhI")
                            name = self.clean_text(name_elem.text) if name_elem else ""
                            
                            url_elem = card.select_one("a")
                            url = url_elem.get('href') if url_elem else ""
                            if url and not url.startswith("http"):
                                url = base_url + url
                            
                            # Extract rating
                            rating_elem = card.select_one("svg.UctUV")
                            rating = None
                            if rating_elem:
                                aria_label = rating_elem.get('aria-label', '')
                                rating_match = re.search(r'([\d\.]+) of 5 bubbles', aria_label)
                                if rating_match:
                                    rating = float(rating_match.group(1))
                            
                            # Extract description
                            desc_elem = card.select_one("div.bBGEi")
                            description = self.clean_text(desc_elem.text) if desc_elem else ""
                            
                            results.append({
                                "name": name,
                                "url": url,
                                "rating": rating,
                                "description": description,
                                "location": location,
                                "source": "TripAdvisor"
                            })
                        except Exception as e:
                            logger.debug(f"Error parsing TripAdvisor activity card: {e}")
            except Exception as e:
                logger.error(f"Error scraping TripAdvisor attractions page: {e}")
        
        return results
    
    # VIATOR SCRAPING
    def scrape_viator(self, location: str) -> List[Dict[str, Any]]:
        """Scrape activities from Viator"""
        base_url = "https://www.viator.com"
        search_url = f"{base_url}/search/{location}"
        
        logger.info(f"Searching Viator for activities in {location}")
        response = self.make_request(search_url)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract activity cards
        try:
            activity_cards = soup.select("div.product-card-main")
            
            for card in activity_cards[:10]:  # Limit to top 10
                try:
                    name_elem = card.select_one("h2")
                    name = self.clean_text(name_elem.text) if name_elem else ""
                    
                    url_elem = card.select_one("a")
                    url = url_elem.get('href') if url_elem else ""
                    if url and not url.startswith("http"):
                        url = base_url + url
                    
                    # Extract price
                    price_elem = card.select_one("span.basePrice")
                    price = self.extract_price(price_elem.text) if price_elem else None
                    
                    # Extract rating
                    rating_elem = card.select_one("span.rating-star")
                    rating = None
                    if rating_elem:
                        rating_text = rating_elem.get('aria-label', '')
                        rating_match = re.search(r'([\d\.]+) of 5', rating_text)
                        if rating_match:
                            rating = float(rating_match.group(1))
                    
                    # Extract description
                    desc_elem = card.select_one("div.product-card-description")
                    description = self.clean_text(desc_elem.text) if desc_elem else ""
                    
                    results.append({
                        "name": name,
                        "url": url,
                        "price": price,
                        "rating": rating,
                        "description": description,
                        "location": location,
                        "source": "Viator"
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Viator activity card: {e}")
        except Exception as e:
            logger.error(f"Error scraping Viator activities: {e}")
        
        return results
    
    # GETYOURGUIDE SCRAPING
    def scrape_getyourguide(self, location: str) -> List[Dict[str, Any]]:
        """Scrape activities from GetYourGuide"""
        base_url = "https://www.getyourguide.com"
        search_url = f"{base_url}/{location}-l/"
        
        logger.info(f"Searching GetYourGuide for activities in {location}")
        response = self.make_request(search_url)
        if not response:
            return []
            
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract activity cards
        try:
            activity_cards = soup.select("div.activity-card-body")
            
            for card in activity_cards[:10]:  # Limit to top 10
                try:
                    name_elem = card.select_one("h3")
                    name = self.clean_text(name_elem.text) if name_elem else ""
                    
                    url_elem = card.select_one("a")
                    url = url_elem.get('href') if url_elem else ""
                    if url and not url.startswith("http"):
                        url = base_url + url
                    
                    # Extract price
                    price_elem = card.select_one("div.price-text")
                    price = self.extract_price(price_elem.text) if price_elem else None
                    
                    # Extract rating
                    rating_elem = card.select_one("span.rating-overall")
                    rating = float(rating_elem.text) if rating_elem else None
                    
                    # Extract duration
                    duration_elem = card.select_one("div.activity-card-attributes-duration")
                    duration = self.clean_text(duration_elem.text) if duration_elem else ""
                    
                    results.append({
                        "name": name,
                        "url": url,
                        "price": price,
                        "rating": rating,
                        "duration": duration,
                        "location": location,
                        "source": "GetYourGuide"
                    })
                except Exception as e:
                    logger.debug(f"Error parsing GetYourGuide activity card: {e}")
        except Exception as e:
            logger.error(f"Error scraping GetYourGuide activities: {e}")
        
        return results
    
    def _filter_and_rank_results(self, results: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """Filter and rank results, returning top N"""
        if not results:
            return []
            
        # Sort by rating (descending) then price (ascending if available)
        sorted_results = sorted(
            [r for r in results if r.get("name")], 
            key=lambda x: (-1 * (x.get("rating") or 0), x.get("price") or float('inf'))
        )
        
        return sorted_results[:top_n]
    
    def search_activities_all_sites(self, location: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search for activities across all supported sites"""
        results = {}
        
        # Search each site
        try:
            results["tripadvisor"] = self.scrape_tripadvisor(location)
        except Exception as e:
            logger.error(f"Error searching TripAdvisor: {e}")
            results["tripadvisor"] = []
            
        try:
            results["viator"] = self.scrape_viator(location)
        except Exception as e:
            logger.error(f"Error searching Viator: {e}")
            results["viator"] = []
            
        try:
            results["getyourguide"] = self.scrape_getyourguide(location)
        except Exception as e:
            logger.error(f"Error searching GetYourGuide: {e}")
            results["getyourguide"] = []
            
        # Return the top results from each site
        return {k: self._filter_and_rank_results(v, 5) for k, v in results.items()}


# Example usage
if __name__ == "__main__":
    scraper = ActivityScraper()
    
    # Example search for activities in Paris
    activity_results = scraper.search_activities_all_sites(location="Paris")
    
    print("\n=== ACTIVITY RESULTS ===")
    for site, results in activity_results.items():
        print(f"\n{site.upper()} TOP RESULTS:")
        for i, activity in enumerate(results, 1):
            print(f"{i}. {activity['name']} - {'${:.2f}'.format(activity['price']) if activity.get('price') else 'Price N/A'}")
            print(f"   Rating: {activity.get('rating', 'N/A')}")
            if 'description' in activity and activity['description']:
                print(f"   Description: {activity['description'][:100]}...")
