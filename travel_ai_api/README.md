# Travel AI API

A Django REST API for a Travel AI agent that helps users plan their trips. The API uses OpenAI's GPT models for natural language processing and web scraping to gather real-time information about hotels, flights, and attractions.

## Features

- **AI-Powered Trip Planning**: Generate comprehensive travel plans based on user queries
- **Hotel Search**: Find hotels with detailed filtering options
- **Flight Search**: Search for flights between locations with various filters
- **Conversational Assistant**: Ask travel-related questions to get helpful responses
- **Web Scraping**: Gather real-time information from travel websites

## Setup Instructions

1. **Clone the repository**

2. **Set up a virtual environment**
   ```bash
   cd travel_ai_api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the OpenAI API key**
   
   Create a `.env` file in the project root and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Trip Planning

- **POST /api/plan-trip/**
  
  Generate a complete travel plan based on user query and preferences.
  
  *Request Body:*
  ```json
  {
    "query": "I want to plan a trip to Paris for 5 days in June with my partner",
    "origin": "New York",
    "destination": "Paris",
    "start_date": "2025-06-10",
    "end_date": "2025-06-15",
    "budget": "moderate",
    "travelers": 2,
    "preferences": "We enjoy art, culture, and fine dining"
  }
  ```
  *Note: Only "query" is required. Other fields can be auto-extracted from the query.*

### Hotel Search

- **POST /api/search-hotels/**
  
  Search for hotels with detailed filtering.
  
  *Request Body:*
  ```json
  {
    "location": "Paris",
    "check_in": "2025-06-10",
    "check_out": "2025-06-15",
    "adults": 2,
    "children": 0,
    "rooms": 1,
    "min_price": 100,
    "max_price": 300,
    "hotel_type": "hotel",
    "star_rating": 4,
    "amenities": ["wifi", "pool"]
  }
  ```

### Flight Search

- **POST /api/search-flights/**
  
  Search for flights between locations.
  
  *Request Body:*
  ```json
  {
    "origin": "NYC",
    "destination": "PAR",
    "departure_date": "2025-06-10",
    "return_date": "2025-06-15",
    "adults": 2,
    "children": 0,
    "infants": 0,
    "cabin_class": "economy",
    "preferred_airlines": ["AF", "DL"],
    "max_stops": 0
  }
  ```

### Travel Assistant

- **POST /api/ask-assistant/**
  
  Ask travel-related questions to the AI assistant.
  
  *Request Body:*
  ```json
  {
    "query": "What's the best time to visit Paris?"
  }
  ```

## Database Models

- **TravelRequest**: Stores user travel requests
- **TripPlan**: Stores generated trip plans

## Technologies Used

- **Django & Django REST Framework**: Backend framework
- **OpenAI API**: For natural language understanding and generation
- **BeautifulSoup**: For web scraping
- **DuckDuckGo Search**: For general web queries
- **SQLite**: Database (default)

## Web Scraping Notice

This API includes web scraping functionality for educational and demonstration purposes. When using in production, ensure compliance with the terms of service of any websites being scraped.

## License

This project is licensed under the MIT License.
