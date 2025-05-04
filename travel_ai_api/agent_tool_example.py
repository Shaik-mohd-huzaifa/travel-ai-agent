#!/usr/bin/env python
"""
Example of how to use the Amadeus Trip Planner Tool as an agent tool.
This script demonstrates how to:
1. Define a tool for an agent
2. Process user queries related to trip planning
3. Format the results in a user-friendly way

Usage:
    python agent_tool_example.py "Plan a trip from San Francisco to Tokyo for 2 adults in June"
"""

import sys
import json
from typing import Dict, Any, List, Optional
from travel_assistant.utils.amadeus_trip_planner_tool import process_trip_query

def amadeus_trip_planner_tool(query: str) -> Dict[str, Any]:
    """
    Agent tool function for trip planning using Amadeus API.
    
    Args:
        query: Natural language query from the user
        
    Returns:
        Formatted response for the agent to present to the user
    """
    # Process the query using the Amadeus Trip Planner
    result = process_trip_query(query)
    
    # Check for errors
    if result.get("status") == "error":
        return {
            "result": f"ERROR: {result.get('error')}",
            "success": False
        }
    
    # Extract trip details
    trip_details = result["trip_details"]
    origin = trip_details.get("origin_city", "Unknown")
    destination = trip_details.get("destination_city", "Unknown")
    departure_date = trip_details.get("departure_date", "Unknown")
    return_date = trip_details.get("return_date", "Unknown")
    travelers = trip_details.get("travelers", 1)
    
    # Format flight information
    flight_info = []
    if result["flights"]:
        for i, flight in enumerate(result["flights"][:3], 1):
            flight_segments = []
            for segment in flight.get("segments", []):
                flight_segments.append(
                    f"{segment.get('departure_airport', '')} → "
                    f"{segment.get('arrival_airport', '')} "
                    f"({segment.get('flight_number', '')})"
                )
            
            flight_info.append({
                "option": i,
                "price": f"{flight.get('currency', 'USD')} {flight.get('price', 0):.2f}",
                "segments": flight_segments
            })
    
    # Format hotel information
    hotel_info = []
    if result["hotels"]:
        for i, hotel in enumerate(result["hotels"][:3], 1):
            hotel_info.append({
                "option": i,
                "name": hotel.get("name", "Unknown"),
                "rating": hotel.get("rating", "N/A"),
                "price": f"{hotel.get('currency', 'USD')} {hotel.get('price', 0):.2f}"
            })
    
    # Create a summary response
    summary = result.get("recommendations", {}).get("summary", "")
    
    # Format response for the agent
    response = {
        "trip_plan": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "travelers": travelers,
            "summary": summary,
            "flights": flight_info,
            "hotels": hotel_info,
            "suggestions": result.get("suggestions", [])
        },
        "success": True
    }
    
    return response

def format_response_for_user(agent_response: Dict[str, Any]) -> str:
    """Format the agent response in a user-friendly way."""
    if not agent_response.get("success", False):
        return agent_response.get("result", "Sorry, I couldn't process your trip planning request.")
    
    trip_plan = agent_response["trip_plan"]
    
    # Build a formatted response
    response = [
        f"# Trip Plan: {trip_plan['origin']} to {trip_plan['destination']}",
        f"- **Dates:** {trip_plan['departure_date']} to {trip_plan['return_date']}",
        f"- **Travelers:** {trip_plan['travelers']}",
        "",
        f"## Summary",
        f"{trip_plan['summary']}",
        ""
    ]
    
    # Add flight options
    if trip_plan["flights"]:
        response.append("## Flight Options")
        for flight in trip_plan["flights"]:
            response.append(f"### Option {flight['option']}: {flight['price']}")
            response.append("**Itinerary:**")
            for i, segment in enumerate(flight["segments"], 1):
                response.append(f"- Segment {i}: {segment}")
            response.append("")
    else:
        response.append("## Flight Options\nNo flights found for your search criteria.")
    
    # Add hotel options
    if trip_plan["hotels"]:
        response.append("## Hotel Options")
        for hotel in trip_plan["hotels"]:
            response.append(f"### Option {hotel['option']}: {hotel['name']}")
            response.append(f"- **Rating:** {hotel['rating']}")
            response.append(f"- **Price:** {hotel['price']}")
            response.append("")
    else:
        response.append("## Hotel Options\nNo hotels found for your search criteria.")
    
    # Add suggestions
    if trip_plan["suggestions"]:
        response.append("## Suggestions")
        for suggestion in trip_plan["suggestions"]:
            response.append(f"- {suggestion}")
    
    return "\n".join(response)

# Example of how an agent would use this tool
if __name__ == "__main__":
    # Get query from command line or use default
    query = sys.argv[1] if len(sys.argv) > 1 else "Plan a trip from New York to Paris for 2 adults next month"
    
    print(f"Processing query: {query}")
    print("---------------------")
    
    # Call the tool
    agent_response = amadeus_trip_planner_tool(query)
    
    # Format the response for the user
    user_response = format_response_for_user(agent_response)
    
    # Display the response
    print(user_response)
