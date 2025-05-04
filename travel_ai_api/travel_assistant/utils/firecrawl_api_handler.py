"""
Module for handling API calls to Firecrawl for searching activities.
"""
import os
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Load environment variables
load_dotenv()

class FirecrawlAPIHandler:
    """
    Handler for Firecrawl API calls to search for activities in different locations.
    """
    def __init__(self):
        """
        Initialize the Firecrawl API client.
        """
        self.api_key = os.getenv('FIRECRAWL_API_KEY')
        print(f"DEBUG: Firecrawl API key loaded: {self.api_key[:8]}...")  # Print first 8 chars for debug
        
        if not self.api_key:
            raise ValueError("Firecrawl API key is missing from environment variables")
        
        # Force reload the key directly from the .env file if running in a long-lived process
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        if os.path.exists(dotenv_path):
            with open(dotenv_path, 'r') as f:
                for line in f:
                    if line.startswith('FIRECRAWL_API_KEY='):
                        self.api_key = line.strip().split('=', 1)[1].strip().strip("'").strip('"')
                        print(f"DEBUG: Reloaded API key from file: {self.api_key[:8]}...")
        
        self.app = FirecrawlApp(api_key=self.api_key)
        self.last_request_time = 0
        self.min_request_interval = 6  # Seconds between requests to avoid rate limiting
    
    def _throttle_request(self):
        """
        Implement simple rate limiting to avoid hitting API limits.
        Waits if needed to ensure minimum time between requests.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            print(f"Rate limiting: Waiting {sleep_time:.2f} seconds before next request")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_activities(self, location: str, activity_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for activities in a specific location.
        
        Args:
            location (str): The location to search for activities (city or country)
            activity_type (str, optional): Type of activity (e.g. 'outdoor', 'museum', 'restaurant')
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of activity results with details
        """
        # Build search query based on parameters
        query = f"things to do in {location}"
        if activity_type:
            query += f" {activity_type} activities"
        
        try:
            # Throttle request if needed
            self._throttle_request()
            
            # Perform the search
            search_result = self.app.search(query, limit=limit)
            
            # Format the results
            activities = []
            for result in search_result.data:
                # Handle both object attributes and dictionary access
                if isinstance(result, dict):
                    activity = {
                        "name": result.get("title", "Unknown Activity"),
                        "url": result.get("url", ""),
                        "description": result.get("description", "No description available"),
                        "location": location,
                        "source": "Firecrawl"
                    }
                else:
                    # Try attribute access with fallbacks
                    try:
                        activity = {
                            "name": getattr(result, "title", "Unknown Activity"),
                            "url": getattr(result, "url", ""),
                            "description": getattr(result, "description", "No description available"),
                            "location": location,
                            "source": "Firecrawl"
                        }
                    except Exception:
                        # Last resort fallback
                        activity = {
                            "name": str(result),
                            "url": "",
                            "description": "Error parsing activity data",
                            "location": location,
                            "source": "Firecrawl"
                        }
                
                activities.append(activity)
            
            return activities
        
        except Exception as e:
            print(f"Error searching activities with Firecrawl: {e}")
            return []
    
    def search_restaurants(self, location: str, cuisine_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for restaurants in a specific location.
        
        Args:
            location (str): The location to search for restaurants
            cuisine_type (str, optional): Type of cuisine (e.g. 'italian', 'indian', 'vegetarian')
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of restaurant results with details
        """
        # Build search query based on parameters
        query = f"best restaurants in {location}"
        if cuisine_type:
            query += f" {cuisine_type} food"
        
        try:
            # Throttle request if needed
            self._throttle_request()
            
            # Perform the search
            search_result = self.app.search(query, limit=limit)
            
            # Format the results
            restaurants = []
            for result in search_result.data:
                # Handle both object attributes and dictionary access
                if isinstance(result, dict):
                    restaurant = {
                        "name": result.get("title", "Unknown Restaurant"),
                        "url": result.get("url", ""),
                        "description": result.get("description", "No description available"),
                        "location": location,
                        "cuisine_type": cuisine_type if cuisine_type else "Various",
                        "source": "Firecrawl"
                    }
                else:
                    # Try attribute access with fallbacks
                    try:
                        restaurant = {
                            "name": getattr(result, "title", "Unknown Restaurant"),
                            "url": getattr(result, "url", ""),
                            "description": getattr(result, "description", "No description available"),
                            "location": location,
                            "cuisine_type": cuisine_type if cuisine_type else "Various",
                            "source": "Firecrawl"
                        }
                    except Exception:
                        # Last resort fallback
                        restaurant = {
                            "name": str(result),
                            "url": "",
                            "description": "Error parsing restaurant data",
                            "location": location,
                            "cuisine_type": cuisine_type if cuisine_type else "Various",
                            "source": "Firecrawl"
                        }
                
                restaurants.append(restaurant)
            
            return restaurants
        
        except Exception as e:
            print(f"Error searching restaurants with Firecrawl: {e}")
            return []

    def search_tourist_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for top tourist attractions in a specific location.
        
        Args:
            location (str): The location to search for attractions
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of attraction results with details
        """
        query = f"top tourist attractions in {location}"
        
        try:
            # Throttle request if needed
            self._throttle_request()
            
            # Perform the search
            search_result = self.app.search(query, limit=limit)
            
            # Format the results
            attractions = []
            for result in search_result.data:
                # Handle both object attributes and dictionary access
                if isinstance(result, dict):
                    attraction = {
                        "name": result.get("title", "Unknown Attraction"),
                        "url": result.get("url", ""),
                        "description": result.get("description", "No description available"),
                        "location": location,
                        "source": "Firecrawl"
                    }
                else:
                    # Try attribute access with fallbacks
                    try:
                        attraction = {
                            "name": getattr(result, "title", "Unknown Attraction"),
                            "url": getattr(result, "url", ""),
                            "description": getattr(result, "description", "No description available"),
                            "location": location,
                            "source": "Firecrawl"
                        }
                    except Exception:
                        # Last resort fallback
                        attraction = {
                            "name": str(result),
                            "url": "",
                            "description": "Error parsing attraction data",
                            "location": location,
                            "source": "Firecrawl"
                        }
                
                attractions.append(attraction)
            
            return attractions
        
        except Exception as e:
            print(f"Error searching attractions with Firecrawl: {e}")
            return []
