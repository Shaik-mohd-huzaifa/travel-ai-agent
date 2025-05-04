import os
import openai
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TRIP_PLANNER_URL = "http://localhost:8000/api/trip-planner-tool/"  # Change to your deployed URL if needed

client = openai.OpenAI(api_key=OPENAI_API_KEY)

trip_planner_function = {
    "name": "trip_planner",
    "description": "Plan a trip with flights, accommodations, activities, and travel info.",
    "parameters": {
        "type": "object",
        "properties": {
            "origin_city": {"type": "string", "description": "City of departure"},
            "destination_city": {"type": "string", "description": "City of destination"},
            "start_date": {"type": "string", "description": "Trip start date (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Trip end date (YYYY-MM-DD)"},
            "travelers": {"type": "integer", "description": "Number of travelers"},
            "budget_level": {"type": "string", "enum": ["budget", "moderate", "luxury"], "description": "Budget level"},
            "trip_type": {"type": "string", "description": "Type of trip (leisure, business, adventure, etc.)"},
            "accommodation_type": {"type": "string", "description": "Type of accommodation"},
            "flight_class": {"type": "string", "enum": ["economy", "premium_economy", "business", "first"], "description": "Flight class"},
            "include_activities": {"type": "boolean", "description": "Whether to include activity recommendations"},
            "origin_country": {"type": "string", "description": "Country of origin (for visa info)"},
            "destination_country": {"type": "string", "description": "Country of destination (if different from city)"}
        },
        "required": ["origin_city", "destination_city", "start_date", "end_date"]
    }
}

def trip_planner(params):
    """Call the Trip Planner Tool API endpoint."""
    response = requests.post(TRIP_PLANNER_URL, json=params)
    response.raise_for_status()
    return response.json()

def agent_conversation():
    print("Welcome to the Trip Planning Agent! Type your travel request (type 'exit' to quit).")
    messages = [
        {"role": "system", "content": "You are a helpful travel assistant that can plan trips for users."}
    ]
    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() == "exit":
            break
        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="gpt-4o",  # or "gpt-4" or "gpt-3.5-turbo-1106"
            messages=messages,
            tools=[{"type": "function", "name": "trip_planner", "function": trip_planner_function}],
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", [])

        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "trip_planner":
                    args = json.loads(tool_call.function.arguments)
                    print("\n[Agent] Planning your trip...")
                    try:
                        trip_result = trip_planner(args)
                        # Optionally, summarize with the LLM for pretty output
                        summary_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "Format the following trip plan as a beautiful, helpful, and concise travel summary for the user. Use headers and bullet points."},
                                {"role": "user", "content": json.dumps(trip_result)}
                            ],
                            temperature=0.6,
                        )
                        print("\n" + summary_response.choices[0].message.content)
                    except Exception as e:
                        print(f"[Agent] Error calling trip planner tool: {e}")
        else:
            print("\n[Agent]:", message.content)
        messages.append(message.model_dump(exclude_unset=True))

if __name__ == "__main__":
    agent_conversation()
