from django.shortcuts import render
import json
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import openai
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

from .models import TravelRequest, TripPlan, SearchQuery, HotelResult, FlightResult
from .serializers import (
    TravelRequestSerializer, 
    TripPlanSerializer,
    TravelPlanningRequestSerializer,
    HotelResultSerializer,
    FlightResultSerializer
)
from .utils.openai_client import OpenAIClient
from .utils.web_search import WebSearchClient
from .utils.hotel_scraper import HotelScraper
from .utils.flight_scraper import FlightScraper


class TravelRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing travel requests
    """
    queryset = TravelRequest.objects.all()
    serializer_class = TravelRequestSerializer


class TripPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing trip plans
    """
    queryset = TripPlan.objects.all()
    serializer_class = TripPlanSerializer
    
    def get_queryset(self):
        """Filter trip plans by travel_request if provided"""
        queryset = super().get_queryset()
        travel_request_id = self.request.query_params.get('travel_request_id')
        
        if travel_request_id:
            queryset = queryset.filter(travel_request_id=travel_request_id)
        
        return queryset


class TravelPlannerAPIView(APIView):
    """
    API endpoint for generating travel plans using AI
    """
    def post(self, request, *args, **kwargs):
        # Validate input
        serializer = TravelPlanningRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get validated data
        data = serializer.validated_data
        user_query = data.get('query', '')
        
        # Initialize clients
        openai_client = OpenAIClient()
        web_search_client = WebSearchClient()
        
        try:
            # Extract structured travel details from query if not provided explicitly
            if not all([data.get(field) for field in ['origin', 'destination']]):
                extracted_details = openai_client.extract_travel_details(user_query)
                
                # Merge extracted details with provided details
                for key, value in extracted_details.items():
                    if key != 'error' and not data.get(key) and value:
                        data[key] = value
            
            # Create and save travel request
            travel_request_data = {
                'user_query': user_query,
                'origin': data.get('origin'),
                'destination': data.get('destination'),
                'start_date': data.get('start_date'),
                'end_date': data.get('end_date'),
                'budget': data.get('budget'),
                'travelers': data.get('travelers', 1),
                'preferences': data.get('preferences'),
            }
            
            travel_request = TravelRequest.objects.create(**travel_request_data)
            
            # Convert string dates to datetime objects for scrapers if available
            start_date = None
            end_date = None
            if travel_request.start_date:
                start_date = datetime.combine(travel_request.start_date, datetime.min.time())
            if travel_request.end_date:
                end_date = datetime.combine(travel_request.end_date, datetime.min.time())
            
            # Perform web searches to get additional information
            search_results = []
            
            # General travel information
            if data.get('destination'):
                travel_info = web_search_client.search_travel_info(
                    f"{data.get('destination')} travel guide", max_results=3
                )
                search_results.extend(travel_info)
            
            # Hotel information with enhanced scraping
            if data.get('destination'):
                # Parse budget to extract price range if available
                min_price = None
                max_price = None
                if data.get('budget'):
                    budget_str = str(data.get('budget')).lower()
                    # Simple budget parsing - can be enhanced with NLP
                    if 'luxury' in budget_str or 'high' in budget_str:
                        min_price = 200
                    elif 'mid' in budget_str or 'moderate' in budget_str:
                        min_price = 100
                        max_price = 200
                    elif 'budget' in budget_str or 'low' in budget_str or 'cheap' in budget_str:
                        max_price = 100
                
                # Determine hotel type from preferences if available
                hotel_type = None
                if data.get('preferences'):
                    pref_str = str(data.get('preferences')).lower()
                    if 'hostel' in pref_str:
                        hotel_type = 'hostel'
                    elif 'apartment' in pref_str or 'rental' in pref_str:
                        hotel_type = 'apartment'
                    elif 'resort' in pref_str:
                        hotel_type = 'resort'
                    elif 'villa' in pref_str:
                        hotel_type = 'villa'
                    elif 'guest house' in pref_str or 'guesthouse' in pref_str:
                        hotel_type = 'guest_house'
                
                hotel_info = web_search_client.search_hotel_info(
                    location=data.get('destination'),
                    check_in_date=start_date,
                    check_out_date=end_date,
                    adults=data.get('travelers', 2),
                    max_results=3,
                    hotel_type=hotel_type,
                    min_price=min_price,
                    max_price=max_price
                )
                search_results.extend(hotel_info)
            
            # Flight information with enhanced scraping
            if data.get('origin') and data.get('destination'):
                flight_info = web_search_client.search_flight_info(
                    origin=data.get('origin'),
                    destination=data.get('destination'),
                    departure_date=start_date,
                    return_date=end_date,
                    adults=data.get('travelers', 1),
                    max_results=3
                )
                search_results.extend(flight_info)
            
            # Attractions
            if data.get('destination'):
                attractions = web_search_client.search_attractions(data.get('destination'), max_results=3)
                search_results.extend(attractions)
            
            # Generate travel plan
            travel_plan_json = openai_client.generate_travel_plan(travel_request_data, search_results)
            
            if 'error' in travel_plan_json:
                return Response({'error': travel_plan_json['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Save trip plan
            trip_plan_data = {
                'travel_request': travel_request,
                'title': travel_plan_json.get('title', f'Trip to {data.get("destination", "destination")}'),
                'summary': travel_plan_json.get('summary', ''),
                'itinerary': travel_plan_json.get('itinerary', ''),
                'accommodations': travel_plan_json.get('accommodations', ''),
                'transportation': travel_plan_json.get('transportation', ''),
                'activities': travel_plan_json.get('activities', ''),
                'estimated_cost': travel_plan_json.get('estimated_cost', None),
                'cost_breakdown': json.dumps(travel_plan_json.get('cost_breakdown', {})),
                'references': json.dumps(travel_plan_json.get('references', [])),
            }
            
            trip_plan = TripPlan.objects.create(**trip_plan_data)
            
            # Process search results for the response
            processed_results = self._process_search_results(search_results)
            
            # Serialize the response
            response_data = {
                'travel_request': TravelRequestSerializer(travel_request).data,
                'trip_plan': TripPlanSerializer(trip_plan).data,
                'sources': processed_results
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_search_results(self, search_results):
        """
        Process and format search results for the response
        """
        processed_results = []
        
        for result in search_results:
            # If it's a scraped hotel or flight result (dict with specific keys)
            if isinstance(result, dict):
                if 'name' in result and ('price' in result or 'facilities' in result):
                    # It's a hotel result
                    processed_item = {
                        'type': 'hotel',
                        'name': result.get('name', ''),
                        'price': result.get('price', ''),
                        'currency': result.get('currency', 'USD'),
                        'rating': result.get('rating', ''),
                        'address': result.get('address', ''),
                        'facilities': result.get('facilities', []),
                        'url': result.get('url', ''),
                        'image_url': result.get('image_url', '')
                    }
                elif 'airline' in result and 'departure' in result:
                    # It's a flight result
                    processed_item = {
                        'type': 'flight',
                        'airline': result.get('airline', ''),
                        'price': result.get('price', ''),
                        'currency': result.get('currency', 'USD'),
                        'departure': result.get('departure', {}),
                        'arrival': result.get('arrival', {}),
                        'duration': result.get('duration', ''),
                        'stops': result.get('stops', 0),
                        'flight_number': result.get('flight_number', '')
                    }
                else:
                    # Generic dictionary result
                    processed_item = {
                        'type': 'generic',
                        **result
                    }
            # DDGS search result (contains title, href, body)
            elif hasattr(result, 'get'):
                processed_item = {
                    'type': 'web_search',
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', '')
                }
            else:
                # Unknown format
                processed_item = {
                    'type': 'unknown',
                    'content': str(result)
                }
            
            processed_results.append(processed_item)
        
        return processed_results


class TravelAIAssistantView(APIView):
    """
    API endpoint for conversational travel planning assistance
    """
    def post(self, request, *args, **kwargs):
        query = request.data.get('query')
        travel_request_id = request.data.get('travel_request_id')
        
        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Initialize OpenAI client
            openai_client = OpenAIClient()
            
            # Get travel request context if ID provided
            travel_request = None
            if travel_request_id:
                try:
                    travel_request = TravelRequest.objects.get(id=travel_request_id)
                except TravelRequest.DoesNotExist:
                    pass
            
            # Generate response based on user query and context
            response = openai_client.client.chat.completions.create(
                model=openai_client.model,
                messages=[
                    {"role": "system", "content": "You are a helpful travel assistant providing advice and information "
                                                "about travel planning. Be concise but informative."},
                    {"role": "user", "content": query}
                ],
                temperature=0.7
            )
            
            response_data = {
                'response': response.choices[0].message.content,
                'travel_request_id': str(travel_request.id) if travel_request else None
            }
            
            return Response(response_data)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HotelSearchAPIView(APIView):
    """
    API endpoint for searching hotels with detailed filtering
    """
    def post(self, request, *args, **kwargs):
        location = request.data.get('location')
        check_in = request.data.get('check_in')
        check_out = request.data.get('check_out')
        adults = request.data.get('adults', 2)
        children = request.data.get('children', 0)
        rooms = request.data.get('rooms', 1)
        min_price = request.data.get('min_price')
        max_price = request.data.get('max_price')
        hotel_type = request.data.get('hotel_type')
        star_rating = request.data.get('star_rating')
        amenities = request.data.get('amenities', [])
        
        if not location:
            return Response({'error': 'Location is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parse dates if provided
            check_in_date = None
            check_out_date = None
            if check_in:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            if check_out:
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            
            # Initialize web search client
            web_search_client = WebSearchClient()
            
            # Search for hotels
            hotels = web_search_client.hotel_scraper.search_hotels(
                location=location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                adults=adults,
                children=children,
                rooms=rooms,
                min_price=min_price,
                max_price=max_price,
                hotel_type=hotel_type,
                star_rating=star_rating,
                amenities=amenities
            )
            
            return Response(hotels)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FlightSearchAPIView(APIView):
    """
    API endpoint for searching flights with detailed filtering
    """
    def post(self, request, *args, **kwargs):
        origin = request.data.get('origin')
        destination = request.data.get('destination')
        departure_date = request.data.get('departure_date')
        return_date = request.data.get('return_date')
        adults = request.data.get('adults', 1)
        children = request.data.get('children', 0)
        infants = request.data.get('infants', 0)
        cabin_class = request.data.get('cabin_class', 'economy')
        preferred_airlines = request.data.get('preferred_airlines', [])
        max_stops = request.data.get('max_stops')
        
        if not origin or not destination:
            return Response({'error': 'Origin and destination are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parse dates if provided
            departure_datetime = None
            return_datetime = None
            if departure_date:
                departure_datetime = datetime.strptime(departure_date, '%Y-%m-%d')
            if return_date:
                return_datetime = datetime.strptime(return_date, '%Y-%m-%d')
            
            # Initialize web search client
            web_search_client = WebSearchClient()
            
            # Search for flights
            flights = web_search_client.flight_scraper.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_datetime,
                return_date=return_datetime,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
                preferred_airlines=preferred_airlines,
                max_stops=max_stops
            )
            
            return Response(flights)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TravelScraperView(APIView):
    """
    API endpoint for scraping travel information from multiple sites
    """
    # Uncomment to require authentication
    # permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        """
        Handle POST requests for travel scraping
        
        Expected request format for hotels:
        {
            "search_type": "hotels",
            "location": "city_name",
            "check_in": "YYYY-MM-DD",
            "check_out": "YYYY-MM-DD",
            "guests": 2,
            "rooms": 1,
            "filters": {
                "min_price": 50,
                "max_price": 300,
                "star_rating": 4
            }
        }
        
        Expected request format for flights:
        {
            "search_type": "flights",
            "origin": "airport_code",
            "destination": "airport_code",
            "date": "YYYY-MM-DD",
            "return_date": "YYYY-MM-DD",  // Optional
            "adults": 1,
            "filters": {
                "max_stops": 1,
                "preferred_airlines": ["airline1", "airline2"]
            }
        }
        """
        search_type = request.data.get('search_type', '').lower()
        
        # Create a SearchQuery record
        query = SearchQuery(
            user=request.user if request.user.is_authenticated else None,
            query_type=search_type,
            query_params=request.data
        )
        query.save()
        
        try:
            if search_type == 'hotels':
                return self._handle_hotel_search(request.data, query)
            elif search_type == 'flights':
                return self._handle_flight_search(request.data, query)
            else:
                return Response(
                    {"error": "Invalid search_type. Must be 'hotels' or 'flights'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Error in travel scraper: {str(e)}")
            return Response(
                {"error": f"An error occurred during scraping: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_hotel_search(self, data, query):
        """Handle hotel search requests"""
        required_fields = ['location', 'check_in', 'check_out']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return Response(
                    {"error": f"Missing required field: {field}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Extract request parameters
        location = data.get('location')
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        guests = data.get('guests', 2)
        rooms = data.get('rooms', 1)
        filters = data.get('filters', {})
        
        # Validate date formats
        try:
            datetime.strptime(check_in, '%Y-%m-%d')
            datetime.strptime(check_out, '%Y-%m-%d')
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform the scraping
        scraper = HotelScraper()
        hotel_results = scraper.search_hotels_all_sites(
            location=location,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            rooms=rooms
        )
        
        # Save results to database
        saved_results = []
        for site, hotels in hotel_results.items():
            for hotel in hotels:
                hotel_result = HotelResult(
                    search_query=query,
                    hotel_name=hotel.get('name', ''),
                    source=hotel.get('source', site),
                    price=hotel.get('price'),
                    rating=hotel.get('rating'),
                    location=location,
                    url=hotel.get('url', ''),
                    result_data=hotel
                )
                hotel_result.save()
                saved_results.append(hotel_result)
        
        # Format and return the response
        response_data = {
            'query_id': query.id,
            'search_type': 'hotels',
            'parameters': {
                'location': location,
                'check_in': check_in,
                'check_out': check_out,
                'guests': guests,
                'rooms': rooms
            },
            'results': hotel_results
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _handle_flight_search(self, data, query):
        """Handle flight search requests"""
        required_fields = ['origin', 'destination', 'date']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return Response(
                    {"error": f"Missing required field: {field}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Extract request parameters
        origin = data.get('origin')
        destination = data.get('destination')
        date = data.get('date')
        return_date = data.get('return_date')
        adults = data.get('adults', 1)
        filters = data.get('filters', {})
        
        # Validate date formats
        try:
            datetime.strptime(date, '%Y-%m-%d')
            if return_date:
                datetime.strptime(return_date, '%Y-%m-%d')
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform the scraping
        scraper = FlightScraper()
        flight_results = scraper.search_flights_all_sites(
            origin=origin,
            destination=destination,
            date=date,
            return_date=return_date,
            adults=adults
        )
        
        # Save results to database
        saved_results = []
        for site, flights in flight_results.items():
            for flight in flights:
                flight_result = FlightResult(
                    search_query=query,
                    airline=flight.get('airline', ''),
                    source=flight.get('source', site),
                    price=flight.get('price'),
                    duration=flight.get('duration', ''),
                    stops=flight.get('stops', 'Direct'),
                    origin=origin,
                    destination=destination,
                    departure_date=date,
                    return_date=return_date,
                    result_data=flight
                )
                flight_result.save()
                saved_results.append(flight_result)
        
        # Format and return the response
        response_data = {
            'query_id': query.id,
            'search_type': 'flights',
            'parameters': {
                'origin': origin,
                'destination': destination,
                'date': date,
                'return_date': return_date,
                'adults': adults
            },
            'results': flight_results
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class TripPlannerToolView(APIView):
    """
    API endpoint that exposes the trip planner tool as a callable function for LLMs
    """
    # Uncomment to require authentication
    # permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        """
        Handle POST requests for comprehensive trip planning
        
        This endpoint expects a JSON object with trip planning parameters:
        {
            "origin_city": "New York",
            "destination_city": "Paris",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "travelers": 2,
            "budget_level": "moderate", // "budget", "moderate", "luxury"
            "trip_type": "leisure", // optional
            "accommodation_type": "hotel", // optional
            "flight_class": "economy", // "economy", "premium_economy", "business", "first"
            "include_activities": true,
            "origin_country": "United States", // optional, defaults to United States
            "destination_country": "France" // optional
        }
        """
        try:
            # Import the trip planner tool
            from .utils.trip_planner_tool import llm_trip_planner_tool
            
            # Call the trip planner tool with the request data
            trip_plan = llm_trip_planner_tool(request.data)
            
            # Return the results
            return Response(trip_plan, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in trip planner tool: {str(e)}")
            return Response(
                {"error": f"An error occurred during trip planning: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AgentChatAPIView(APIView):
    """
    REST API endpoint for the Trip Planner Agent (LLM tool-calling agent).
    Requires JWT authentication.
    POST { "message": "your message here" }
    Returns: { "response": "agent's reply" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Missing 'message' in request."}, status=400)

        # Set up OpenAI client
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        TRIP_PLANNER_URL = "http://localhost:8000/api/trip-planner-tool/"

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
        
        amadeus_trip_planner_function = {
            "name": "amadeus_trip_planner",
            "description": "Plan a trip using the Amadeus API to get real flight and hotel options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The user's natural language query about trip planning"}
                },
                "required": ["query"]
            }
        }

        def trip_planner(params):
            resp = requests.post(TRIP_PLANNER_URL, json=params)
            resp.raise_for_status()
            return resp.json()
            
        def amadeus_trip_planner(params):
            from .utils.amadeus_trip_planner_tool import process_trip_query
            return process_trip_query(params["query"])

        messages = [
            {"role": "system", "content": "You are a helpful travel assistant providing advice and information "
                                                "about travel planning. Be concise but informative."},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=[
                {"type": "function", "function": trip_planner_function},
                {"type": "function", "function": amadeus_trip_planner_function}
            ],
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", [])

        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "trip_planner":
                    args = json.loads(tool_call.function.arguments)
                    try:
                        trip_result = trip_planner(args)
                        summary_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "Format the following trip plan as a beautiful, helpful, and concise travel summary for the user. Use headers and bullet points."},
                                {"role": "user", "content": json.dumps(trip_result)}
                            ],
                            temperature=0.6,
                        )
                        return Response({"response": summary_response.choices[0].message.content})
                    except Exception as e:
                        return Response({"error": f"Error calling trip planner tool: {e}"}, status=500)
                elif tool_call.function.name == "amadeus_trip_planner":
                    args = json.loads(tool_call.function.arguments)
                    try:
                        amadeus_result = amadeus_trip_planner(args)
                        summary_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "Format the following Amadeus trip plan as a beautiful, helpful, and concise travel summary for the user. Highlight the best flight and hotel options. Use headers and bullet points to organize the information."},
                                {"role": "user", "content": json.dumps(amadeus_result)}
                            ],
                            temperature=0.6,
                        )
                        return Response({"response": summary_response.choices[0].message.content})
                    except Exception as e:
                        return Response({"error": f"Error calling Amadeus trip planner: {e}"}, status=500)
        else:
            return Response({"response": message.content})


# Add a dedicated endpoint for direct access to the Amadeus Trip Planner
class AmadeusAgentAPIView(APIView):
    """
    REST API endpoint for the Amadeus Trip Planner.
    
    POST { "query": "your trip planning query here" }
    Returns: { "response": "formatted trip plan" }
    """
    # Temporarily removed authentication requirement for development
    # permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        user_query = request.data.get("query")
        if not user_query:
            return Response({"error": "Missing 'query' in request."}, status=400)
            
        try:
            # Process the query using the Amadeus Trip Planner
            from .utils.amadeus_trip_planner_tool import process_trip_query
            result = process_trip_query(user_query)
            
            # Format the response
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            summary_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Format the following Amadeus trip plan as a beautiful, helpful, and concise travel summary for the user. Highlight the best flight and hotel options. Use markdown formatting with headers and bullet points to organize the information."},
                    {"role": "user", "content": json.dumps(result)}
                ],
                temperature=0.6,
            )
            
            return Response({
                "raw_data": result,  # Include raw data for frontend processing if needed
                "response": summary_response.choices[0].message.content
            })
        except Exception as e:
            return Response({"error": f"Error processing trip planning query: {str(e)}"}, status=500)

class AmadeusAgentAPIView(APIView):
    """
    REST API endpoint for the Amadeus Trip Planner Agent.
    Handles trip planning using the Amadeus APIs and DuckDuckGo for additional data.
    POST { "message": "your message here" }
    Returns: { "response": "agent's reply", "raw_data": { ... } }
    """
    permission_classes = []  # No authentication required for now
    
    def post(self, request, format=None):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Missing 'message' in request."}, status=400)

        try:
            # Import here to avoid circular imports
            from .utils.amadeus_trip_planner_tool import AmadeusTripPlannerTool
            
            # Initialize the trip planner tool
            trip_planner = AmadeusTripPlannerTool()
            
            # Process the user query and get results
            results = trip_planner.plan_trip(user_message)
            
            # Format the response
            response_data = {
                "response": results.get("summary", "I couldn't generate a trip plan at this time."),
                "raw_data": results
            }
            
            return Response(response_data)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in AmadeusAgentAPIView: {str(e)}\n{error_details}")
            return Response({"error": f"Error processing request: {str(e)}"}, status=500)


class TripPlannerToolView(APIView):
    """
    REST API endpoint for the OpenAI function calling Trip Planner Tool.
    POST with parameters from the OpenAI function schema.
    Returns structured trip planning data.
    """
    permission_classes = []  # No authentication required for now
    
    def post(self, request, format=None):
        try:
            # Import here to avoid circular imports
            from .utils.amadeus_trip_planner_tool import AmadeusTripPlannerTool
            
            # Initialize the trip planner tool
            trip_planner = AmadeusTripPlannerTool()
            
            # Extract parameters from request data
            query = ""
            if "origin_city" in request.data and "destination_city" in request.data:
                query = f"Plan a trip from {request.data.get('origin_city')} to {request.data.get('destination_city')}"
                
                if "start_date" in request.data and "end_date" in request.data:
                    query += f" from {request.data.get('start_date')} to {request.data.get('end_date')}"
                    
                if "budget_level" in request.data:
                    query += f", {request.data.get('budget_level')} budget"
                
                if "travelers" in request.data:
                    query += f", {request.data.get('travelers')} travelers"
                    
                if "flight_class" in request.data:
                    query += f", {request.data.get('flight_class')} class"
                    
                if "accommodation_type" in request.data:
                    query += f", {request.data.get('accommodation_type')} accommodation"
            
            # Process the query
            results = trip_planner.plan_trip(query)
            
            return Response(results)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in TripPlannerToolView: {str(e)}\n{error_details}")
            return Response({"error": f"Error processing request: {str(e)}"}, status=500)


class AgentChatAPIView(APIView):
    """
    REST API endpoint for the Trip Planner Agent (LLM tool-calling agent).
    Requires JWT authentication.
    POST { "message": "your message here" }
    Returns: { "response": "agent's reply" }
    """
    permission_classes = []  # Authentication temporarily disabled for development

    def post(self, request, format=None):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Missing 'message' in request."}, status=400)

        # Set up OpenAI client
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        TRIP_PLANNER_URL = "http://localhost:8000/api/trip-planner-tool/"

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
            resp = requests.post(TRIP_PLANNER_URL, json=params)
            resp.raise_for_status()
            return resp.json()
            
        messages = [
            {"role": "system", "content": "You are a helpful travel assistant that can plan trips for users."},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=[{"type": "function", "function": trip_planner_function}],
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", [])

        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "trip_planner":
                    args = json.loads(tool_call.function.arguments)
                    try:
                        trip_result = trip_planner(args)
                        summary_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "Format the following trip plan as a beautiful, helpful, and concise travel summary for the user. Use headers and bullet points."},
                                {"role": "user", "content": json.dumps(trip_result)}
                            ],
                            temperature=0.6,
                        )
                        return Response({"response": summary_response.choices[0].message.content})
                    except Exception as e:
                        return Response({"error": f"Error calling trip planner tool: {e}"}, status=500)
        else:
            return Response({"response": message.content})
