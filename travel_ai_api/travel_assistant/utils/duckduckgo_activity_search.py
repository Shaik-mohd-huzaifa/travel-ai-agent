"""
DuckDuckGo Activity Search Module

This module provides a utility for searching activities using DuckDuckGo,
scraping content from the top search results, and passing that content to
an LLM to extract structured activity information.
"""

import os
import requests
import json
import logging
import time
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

class DuckDuckGoActivitySearch:
    """
    Class for searching activities using DuckDuckGo, scraping content,
    and extracting structured information using an LLM.
    """
    
    def __init__(self):
        """Initialize the DuckDuckGo Activity Search utility."""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is missing from environment variables")
        
        self.client = openai.OpenAI(api_key=self.openai_api_key)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
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
        import random
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
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit text length to avoid excessive token usage with the LLM
            if len(text) > 8000:
                text = text[:8000] + "..."
            
            return text
        
        except Exception as e:
            logger.error(f"Error scraping webpage {url}: {e}")
            return ""
    
    def extract_activity_info(self, location: str, content: str, activity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Use an LLM to extract structured activity information from scraped content.
        
        Args:
            location: The location for activities
            content: The scraped webpage content
            activity_type: Optional type of activity
            
        Returns:
            List of dictionaries with structured activity information
        """
        try:
            # Construct the prompt for the LLM
            activity_type_text = f" {activity_type}" if activity_type else ""
            prompt = f"""Extract information about{activity_type_text} activities, attractions, or things to do in {location} from the following content. 
            Format the information as a list of JSON objects with the following fields:
            - name: The name of the activity or attraction
            - description: A brief description
            - highlights: Key highlights or features (list of strings)
            - price_range: Approximate price range if available (string)
            - location: Specific location within {location}
            - rating: Numerical rating if available (float between 1-5)
            
            Try to extract at least 3-5 distinct activities. If certain fields are not available, use null.
            
            Content:
            {content[:5000]}"""
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured information about activities and attractions from webpage content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Extract and parse the JSON from the response
            result_text = response.choices[0].message.content
            
            # Find JSON content (could be with or without triple backticks)
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', result_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find a JSON array directly
                json_match = re.search(r'\[\s*\{[\s\S]*?\}\s*\]', result_text)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # As a fallback, use the entire text
                    json_str = result_text
            
            # Try to parse the JSON
            try:
                activities = json.loads(json_str)
                # Ensure it's a list
                if not isinstance(activities, list):
                    if isinstance(activities, dict):
                        activities = [activities]
                    else:
                        activities = []
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract individually
                logger.warning("Failed to parse JSON response, trying to extract individually")
                activities = []
                
                # Simple regex to find JSON-like objects
                object_matches = re.finditer(r'\{\s*"name"[\s\S]*?\}', json_str)
                for match in object_matches:
                    try:
                        activity = json.loads(match.group(0))
                        activities.append(activity)
                    except:
                        continue
            
            # Add source and location information
            for activity in activities:
                if 'location' not in activity or not activity['location']:
                    activity['location'] = location
                activity['source'] = 'DuckDuckGo Search'
            
            return activities
        
        except Exception as e:
            logger.error(f"Error extracting activity information: {e}")
            return []
    
    def search_activities(self, location: str, activity_type: Optional[str] = None, 
                          limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for activities in a specific location using DuckDuckGo.
        
        Args:
            location: The location to search for activities
            activity_type: Optional type of activity to search for
            limit: Maximum number of activities to return
            
        Returns:
            List of dictionaries with activity information
        """
        # Construct the search query
        if activity_type:
            query = f"best {activity_type} activities things to do in {location}"
        else:
            query = f"best activities attractions things to do in {location}"
        
        logger.info(f"Searching for activities in {location} with query: {query}")
        
        # Search DuckDuckGo
        search_results = self.search_duckduckgo(query, max_results=2)
        if not search_results:
            logger.warning(f"No search results found for {location}")
            return []
        
        # Scrape content from search results
        all_activities = []
        for result in search_results:
            logger.info(f"Scraping content from: {result['title']} ({result['url']})")
            content = self.scrape_webpage(result['url'])
            
            if content:
                # Extract activity information using the LLM
                activities = self.extract_activity_info(location, content, activity_type)
                if activities:
                    all_activities.extend(activities)
        
        # Remove duplicates (based on name)
        seen_names = set()
        unique_activities = []
        for activity in all_activities:
            name = activity.get('name', '').lower()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_activities.append(activity)
        
        # Sort by rating (if available)
        unique_activities.sort(
            key=lambda x: float(x.get('rating', 0) or 0),
            reverse=True
        )
        
        # Return up to the limit
        return unique_activities[:limit]

# Example usage
if __name__ == "__main__":
    # Test the DuckDuckGo activity search
    activity_search = DuckDuckGoActivitySearch()
    activities = activity_search.search_activities("Paris", activity_type="cultural", limit=5)
    
    print(f"\nFound {len(activities)} activities in Paris:")
    for i, activity in enumerate(activities, 1):
        print(f"\n{i}. {activity.get('name', 'Unnamed Activity')}")
        print(f"   Description: {activity.get('description', 'No description')[:100]}...")
        print(f"   Rating: {activity.get('rating', 'N/A')}")
        if activity.get('highlights'):
            print(f"   Highlights: {', '.join(activity['highlights'][:3])}")
