#!/usr/bin/env python
"""
Trip Planner LLM Integration Demo

This script demonstrates how to use the Trip Planner Tool with an LLM (OpenAI).
It's designed to show how an LLM can call the trip planner as a function/tool
and format the results into a cohesive response.
"""

import os
import json
import sys
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
import openai

# Add project directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_ai_project.settings')
import django
django.setup()

# Import the trip planner tool
from travel_assistant.utils.trip_planner_tool import llm_trip_planner_tool

# Load environment variables
load_dotenv()

# Get OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in your .env file or environment.")

# Set up OpenAI client
client = openai.OpenAI(api_key=api_key)

def format_sample_hotel_search():
    """Run a sample hotel search and format the results"""
    # Define sample parameters
    params = {
        "origin_city": "New York",
        "destination_city": "Paris",
        "start_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d"),
        "travelers": 2,
        "budget_level": "moderate",
        "trip_type": "leisure",
        "accommodation_type": "hotel",
        "flight_class": "economy",
        "include_activities": True
    }
    
    print(f"\n=== PLANNING A TRIP FROM {params['origin_city']} TO {params['destination_city']} ===")
    print(f"Dates: {params['start_date']} to {params['end_date']}")
    print(f"Travelers: {params['travelers']}")
    print("Planning trip, this may take a minute...\n")
    
    # Call the trip planner tool
    try:
        trip_plan = llm_trip_planner_tool(params)
        
        # Format the results with an LLM
        system_prompt = """
        You are an expert travel assistant helping to plan trips.
        Format the trip planning results into a beautiful, well-structured response.
        Focus on highlighting the most important information in a helpful, enthusiastic way.
        Include emoji where appropriate to make the response engaging.
        Structure your response with clear headers and bullet points.
        """
        
        user_prompt = f"""
        Please create a complete trip plan based on the following data. Format it nicely with headers, 
        bullet points, and make it easy to read. Focus on the top recommendations:
        
        {json.dumps(trip_plan, indent=2)}
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Print the formatted response
        print(response.choices[0].message.content)
        print("\n")
        
    except Exception as e:
        print(f"Error during trip planning: {str(e)}")
        return None

def main():
    """Main function to run the demo"""
    parser = argparse.ArgumentParser(description='Trip Planner LLM Integration Demo')
    parser.add_argument('--run', action='store_true', help='Run the demo')
    
    args = parser.parse_args()
    
    if args.run:
        format_sample_hotel_search()
    else:
        print("""
Trip Planner LLM Integration Demo
---------------------------------

This script demonstrates how to integrate the Trip Planner Tool with an LLM (OpenAI).
To run the demo, use the --run flag:

    python llm_trip_planner_demo.py --run

Note: You need to have an OpenAI API key set in your .env file or environment variables.
""")

if __name__ == "__main__":
    main()
