import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from django.conf import settings

class OpenAIClient:
    """
    Utility class for interacting with the OpenAI API
    """
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # Using GPT-4o for better travel planning capabilities
    
    def generate_travel_plan(self, 
                           travel_request: Dict[str, Any],
                           search_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a travel plan based on the travel request and search results
        
        Args:
            travel_request: Dictionary containing travel request details
            search_results: Optional list of search results for enriching the response
            
        Returns:
            Dictionary containing the generated travel plan
        """
        # Build prompt with all available information
        prompt = self._build_travel_plan_prompt(travel_request, search_results)
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert travel planner. Your task is to create detailed, "
                                             "comprehensive travel plans based on user requests. Include accommodations, "
                                             "transportation options, itinerary details, cost estimates, and activities. "
                                             "All responses should be well-structured JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Parse response
        try:
            plan_json = json.loads(response.choices[0].message.content)
            return plan_json
        except (json.JSONDecodeError, AttributeError) as e:
            return {"error": f"Failed to parse response: {str(e)}"}
    
    def extract_travel_details(self, query: str) -> Dict[str, Any]:
        """
        Extract structured travel details from a natural language query
        
        Args:
            query: User's natural language query
            
        Returns:
            Dictionary containing extracted travel details
        """
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Extract travel planning details from the user query into JSON format with "
                                             "the following fields: origin, destination, start_date, end_date, budget, "
                                             "travelers, preferences. Use null for missing fields."},
                {"role": "user", "content": query}
            ],
            temperature=0.3
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, AttributeError) as e:
            return {"error": f"Failed to extract details: {str(e)}"}
    
    def _build_travel_plan_prompt(self, 
                                travel_request: Dict[str, Any], 
                                search_results: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Build a prompt for generating a travel plan
        """
        origin = travel_request.get('origin', 'Not specified')
        destination = travel_request.get('destination', 'Not specified')
        start_date = travel_request.get('start_date', 'Not specified')
        end_date = travel_request.get('end_date', 'Not specified')
        budget = travel_request.get('budget', 'Not specified')
        travelers = travel_request.get('travelers', 1)
        preferences = travel_request.get('preferences', 'Not specified')
        original_query = travel_request.get('user_query', '')
        
        prompt = (
            f"Create a detailed travel plan for a trip from {origin} to {destination}. "
            f"Travel dates: {start_date} to {end_date}. "
            f"Budget: {budget}. Number of travelers: {travelers}. "
            f"Preferences: {preferences}. "
            f"Original query: '{original_query}'\n\n"
        )
        
        # Add search results if available
        if search_results and len(search_results) > 0:
            prompt += "Here is some additional information that might be helpful:\n\n"
            
            for i, result in enumerate(search_results, 1):
                title = result.get('title', 'No title')
                snippet = result.get('snippet', 'No content')
                url = result.get('url', 'No URL')
                prompt += f"{i}. {title}\n{snippet}\nSource: {url}\n\n"
        
        prompt += (
            "Please provide a comprehensive travel plan in JSON format with the following structure:\n"
            "{\n"
            '  "title": "Trip title",\n'
            '  "summary": "Brief summary of the trip",\n'
            '  "itinerary": "Detailed day-by-day itinerary",\n'
            '  "accommodations": "Recommended places to stay",\n'
            '  "transportation": "Transportation options and recommendations",\n'
            '  "activities": "Recommended activities and attractions",\n'
            '  "estimated_cost": "Estimated total cost in USD (numeric value)",\n'
            '  "cost_breakdown": {"category1": amount1, "category2": amount2, ...},\n'
            '  "references": ["reference_url1", "reference_url2", ...]\n'
            "}"
        )
        
        return prompt
