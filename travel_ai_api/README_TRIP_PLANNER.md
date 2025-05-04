# Trip Planner Tool for LLMs

This document explains how to use the comprehensive Trip Planner Tool that we've created for integration with Language Models (LLMs).

## Overview

The Trip Planner Tool combines multiple data sources to create a comprehensive travel plan:

1. **Flights**: Searches across multiple flight booking sites (Skyscanner, Kayak, Expedia, Google Flights, Priceline)
2. **Hotels**: Searches across multiple hotel booking sites (Airbnb, Booking.com, Agoda, Expedia, Hotels.com)
3. **Activities**: Discovers popular activities at the destination (TripAdvisor, Viator, GetYourGuide)
4. **Travel Info**: Provides visa requirements, travel advisories, and health information
5. **LLM Integration**: Uses OpenAI to generate a summary of the trip

## API Endpoint

The tool is available as a REST API endpoint:

```
POST /api/trip-planner-tool/
```

### Request Format

```json
{
  "origin_city": "New York",
  "destination_city": "Paris",
  "start_date": "2025-06-01",
  "end_date": "2025-06-07",
  "travelers": 2,
  "budget_level": "moderate",
  "trip_type": "leisure",
  "accommodation_type": "hotel",
  "flight_class": "economy",
  "include_activities": true,
  "origin_country": "United States",
  "destination_country": "France"
}
```

### Required Parameters

- `origin_city`: Departure city
- `destination_city`: Destination city
- `start_date`: Trip start date (YYYY-MM-DD)
- `end_date`: Trip end date (YYYY-MM-DD)

### Optional Parameters

- `travelers`: Number of travelers (default: 2)
- `budget_level`: "budget", "moderate", or "luxury" (default: "moderate")
- `trip_type`: Type of trip, e.g., "leisure", "business", "adventure" (optional)
- `accommodation_type`: Type of accommodation preferred, e.g., "hotel", "resort", "airbnb" (optional)
- `flight_class`: "economy", "premium_economy", "business", or "first" (default: "economy")
- `include_activities`: Whether to include activity recommendations (default: true)
- `origin_country`: Country of origin for visa info (default: "United States")
- `destination_country`: Country of destination if different from city (optional)

## Using as an LLM Function Tool

The Trip Planner Tool is designed to be called by an LLM as a function/tool. Here's how to use it as an OpenAI function:

```python
import openai
import requests
import json

# Define the trip planner tool as a function
def trip_planner(params):
    """
    Plan a trip with flights, accommodations, activities, and travel info.
    
    Args:
        params: Dictionary containing trip parameters
    
    Returns:
        Comprehensive trip plan
    """
    url = "https://your-api-url.com/api/trip-planner-tool/"
    response = requests.post(url, json=params)
    return response.json()

# Define the function spec for OpenAI
tools = [
    {
        "type": "function",
        "function": {
            "name": "trip_planner",
            "description": "Plan a trip with flights, accommodations, activities, and travel info",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_city": {
                        "type": "string",
                        "description": "City of departure"
                    },
                    "destination_city": {
                        "type": "string",
                        "description": "City of destination"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Trip start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Trip end date (YYYY-MM-DD)"
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "Number of travelers"
                    },
                    "budget_level": {
                        "type": "string",
                        "enum": ["budget", "moderate", "luxury"],
                        "description": "Budget level for the trip"
                    },
                    "trip_type": {
                        "type": "string",
                        "description": "Type of trip (leisure, business, adventure, etc.)"
                    },
                    "accommodation_type": {
                        "type": "string",
                        "description": "Type of accommodation to prefer"
                    },
                    "flight_class": {
                        "type": "string",
                        "enum": ["economy", "premium_economy", "business", "first"],
                        "description": "Class of flight"
                    },
                    "include_activities": {
                        "type": "boolean",
                        "description": "Whether to include activity recommendations"
                    },
                    "origin_country": {
                        "type": "string",
                        "description": "Country of origin (for visa info)"
                    },
                    "destination_country": {
                        "type": "string",
                        "description": "Country of destination (if different from city)"
                    }
                },
                "required": ["origin_city", "destination_city", "start_date", "end_date"]
            }
        }
    }
]

# Example conversation with the LLM
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful travel assistant that can plan trips."},
        {"role": "user", "content": "I want to plan a trip to Paris from New York in June 2025 for 1 week."}
    ],
    tools=tools,
    tool_choice="auto"
)

# Check if the LLM wants to call our function
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    if function_name == "trip_planner":
        # Call our trip planner API
        trip_data = trip_planner(function_args)
        
        # Return the result to the LLM
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant that can plan trips."},
                {"role": "user", "content": "I want to plan a trip to Paris from New York in June 2025 for 1 week."},
                {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                {"role": "tool", "content": json.dumps(trip_data), "tool_call_id": tool_call.id}
            ]
        )
        
        print(response.choices[0].message.content)
```

## Local Demo

You can use the included demo script to test the Trip Planner Tool locally:

```bash
# Make sure your environment has OPENAI_API_KEY set
python llm_trip_planner_demo.py --run
```

## Output Format

The Trip Planner Tool returns a JSON object with the following structure:

```json
{
  "flights": {
    "best_overall": [...],
    "by_site": {...},
    "search_params": {...}
  },
  "accommodations": {
    "best_overall": [...],
    "by_site": {...},
    "search_params": {...}
  },
  "activities": {
    "best_overall": [...],
    "by_site": {...},
    "search_params": {...}
  },
  "travel_info": {
    "visa": {...},
    "advisories": [...],
    "health": {...}
  },
  "summary": {
    "headline": "Your Paris Adventure Awaits!",
    "overview": "A 7-day trip from New York to Paris with..."
  },
  "metadata": {...},
  "status": "success"
}
```

## Notes on Usage

- The scraping functionality may need regular updates as travel websites change
- Consider implementing rate limiting when using in production
- Implement proper caching to avoid excessive API calls
- Add error handling for cases where certain sites are unavailable
