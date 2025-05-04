"""
DuckDuckGo Hotel Search Module

This module provides a utility for searching hotels using DuckDuckGo,
scraping content from the top search results, and passing that content to
an LLM to extract structured hotel information.
"""

import os
import requests
import json
import logging
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DuckDuckGoHotelSearch:
    """
    Class for searching hotels using DuckDuckGo, scraping content,
    and extracting structured information using an LLM.
    """
    
    def __init__(self):
        """Initialize the DuckDuckGo Hotel Search utility."""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is missing from environment variables")
        
        self.client = openai.OpenAI(api_key=self.openai_api_key)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        self.last_request_time = 0
        self.min_request_interval = 2  # seconds between requests
    
    def _throttle_request(self):
        """Simple rate limiting to avoid being blocked."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_random_user_agent(self):
        """Return a random user agent from the list."""
        return random.choice(self.user_agents)
    
    def search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Search DuckDuckGo for the given query and return search results.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with title and url of search results
        """
        # Format the search URL
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            self._throttle_request()
            
            # Send the request with a random user agent
            headers = {'User-Agent': self._get_random_user_agent()}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extract search results
            for result in soup.select('.result'):
                title_elem = result.select_one('.result__title')
                link_elem = result.select_one('.result__url')
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link_href = title_elem.find('a')['href']
                    
                    # Extract the actual URL from DuckDuckGo redirect URL
                    if 'uddg=' in link_href:
                        import urllib.parse
                        parsed_url = urllib.parse.urlparse(link_href)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        url = query_params.get('uddg', [''])[0]
                    else:
                        url = link_href
                    
                    results.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(results) >= max_results:
                        break
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")
            return []
    
    def scrape_webpage(self, url: str) -> str:
        """
        Scrape content from the given URL.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Extracted text content from the webpage
        """
        try:
            self._throttle_request()
            
            headers = {'User-Agent': self._get_random_user_agent()}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.extract()
            
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Truncate if too long (to avoid token limits)
            if len(text) > 15000:
                text = text[:15000] + "..."
            
            return text
        
        except Exception as e:
            logger.error(f"Error scraping webpage {url}: {e}")
            return ""
    
    def extract_hotel_info(self, content: str) -> Dict[str, Any]:
        """
        Use LLM to extract structured hotel information from scraped content.
        
        Args:
            content: The text content from a scraped webpage
            
        Returns:
            Dictionary with extracted hotel information
        """
        if not content or len(content.strip()) < 100:
            logger.warning("Content too short, skipping extraction")
            return {}
        
        prompt = f"""
        You are a hotel information extraction assistant. Extract detailed hotel information from the following web content.
        For each hotel mentioned, extract:
        
        1. Hotel name
        2. Location/Address
        3. Star rating (1-5)
        4. Price range (with currency if available)
        5. Amenities (list up to 5 key amenities)
        6. Room types available
        7. Description (brief summary)
        8. Special features (unique selling points)
        9. Guest rating/review score (if available)
        
        If any information is not found, leave it blank. If the content is not about hotels, reply with "No hotel information found."
        
        Provide the information in JSON format with the following structure:
        {{
            "hotels": [
                {{
                    "name": "Hotel name",
                    "location": "Full address",
                    "stars": "3", (numeric rating, 1-5)
                    "price_range": "€100-150 per night", (include currency symbol and units)
                    "amenities": ["WiFi", "Pool", "Spa", "Restaurant", "Gym"],
                    "room_types": ["Standard", "Deluxe", "Suite"],
                    "description": "Brief 1-2 sentence description",
                    "special_features": ["Ocean view", "Historical building"],
                    "guest_rating": "8.5/10" (include scale)
                }}
            ]
        }}
        
        Return up to 3 hotels from the content. Focus on extracting accurate information rather than inventing details.
        
        CONTENT:
        {content}
        
        JSON RESPONSE:
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500,
                n=1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to extract the JSON part from the response
            try:
                # Find JSON object in the response text (in case the LLM includes additional text)
                import re
                json_match = re.search(r'({[\s\S]*})', result_text)
                if json_match:
                    json_str = json_match.group(1)
                    data = json.loads(json_str)
                else:
                    data = json.loads(result_text)
                
                return data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from LLM response: {result_text[:100]}...")
                return {"hotels": []}
        
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return {"hotels": []}
    
    def search_hotels(self, city: str, check_in_date: str = None, check_out_date: str = None, 
                      budget_level: str = None, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for hotels in a specific city with optional date and budget parameters.
        
        Args:
            city: The city to search for hotels in
            check_in_date: Optional check-in date in YYYY-MM-DD format
            check_out_date: Optional check-out date in YYYY-MM-DD format
            budget_level: Optional budget level (budget, moderate, luxury)
            max_results: Maximum number of hotels to return
            
        Returns:
            List of dictionaries with hotel information
        """
        logger.info(f"Searching for hotels in {city} with query parameters: check_in={check_in_date}, check_out={check_out_date}, budget={budget_level}")
        
        # Build search query
        search_query = f"best hotels in {city}"
        if budget_level:
            if budget_level.lower() == "budget":
                search_query = f"affordable cheap budget hotels in {city}"
            elif budget_level.lower() == "luxury":
                search_query = f"luxury 5 star hotels in {city}"
            else:  # moderate
                search_query = f"mid-range moderate hotels in {city}"
        
        if check_in_date and check_out_date:
            search_query += f" {check_in_date} to {check_out_date}"
        
        # Get search results
        search_results = self.search_duckduckgo(search_query, max_results=5)
        
        if not search_results:
            logger.warning(f"No search results found for hotels in {city}")
            return []
        
        all_hotels = []
        processed_hotel_names = set()  # To avoid duplicates
        
        # Process each search result
        for result in search_results:
            logger.info(f"Scraping content from: {result['title']} ({result['url']})")
            content = self.scrape_webpage(result['url'])
            
            if not content:
                continue
            
            hotel_data = self.extract_hotel_info(content)
            
            if 'hotels' in hotel_data and hotel_data['hotels']:
                for hotel in hotel_data['hotels']:
                    # Skip hotels with missing names
                    if not hotel.get('name'):
                        continue
                    
                    # Skip duplicates (case-insensitive comparison)
                    if hotel['name'].lower() in processed_hotel_names:
                        continue
                    
                    processed_hotel_names.add(hotel['name'].lower())
                    
                    # Add source URL and further standardize the data
                    hotel['source'] = "Web Search"
                    hotel['source_url'] = result['url']
                    
                    # Standardize the format to match other hotel data in the system
                    standardized_hotel = {
                        'id': f"ddg-{len(all_hotels)}",
                        'name': hotel.get('name', ''),
                        'address': hotel.get('location', ''),
                        'stars': hotel.get('stars', ''),
                        'price': hotel.get('price_range', ''),
                        'amenities': hotel.get('amenities', []),
                        'description': hotel.get('description', ''),
                        'room_types': hotel.get('room_types', []),
                        'rating': hotel.get('guest_rating', ''),
                        'special_features': hotel.get('special_features', []),
                        'source': 'DuckDuckGo Web Search'
                    }
                    
                    all_hotels.append(standardized_hotel)
                    
                    if len(all_hotels) >= max_results:
                        break
            
            if len(all_hotels) >= max_results:
                break
        
        logger.info(f"Found {len(all_hotels)} hotels for {city} via DuckDuckGo web search")
        return all_hotels


# For testing
if __name__ == "__main__":
    hotel_search = DuckDuckGoHotelSearch()
    results = hotel_search.search_hotels("Paris", budget_level="moderate")
    print(json.dumps(results, indent=2))
