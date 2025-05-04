from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TravelRequestViewSet,
    TripPlanViewSet, 
    TravelPlannerAPIView,
    TravelAIAssistantView,
    HotelSearchAPIView,
    FlightSearchAPIView,
    TravelScraperView,
    TripPlannerToolView,
    AgentChatAPIView,
    AmadeusAgentAPIView
)

# Create a router and register our ViewSets
router = DefaultRouter()
router.register(r'travel-requests', TravelRequestViewSet)
router.register(r'trip-plans', TripPlanViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('plan-trip/', TravelPlannerAPIView.as_view(), name='plan-trip'),
    path('ask-assistant/', TravelAIAssistantView.as_view(), name='ask-assistant'),
    path('search-hotels/', HotelSearchAPIView.as_view(), name='search-hotels'),
    path('search-flights/', FlightSearchAPIView.as_view(), name='search-flights'),
    path('travel-scraper/', TravelScraperView.as_view(), name='travel-scraper'),
    path('trip-planner-tool/', TripPlannerToolView.as_view(), name='trip-planner-tool'),
    path('agent/', AgentChatAPIView.as_view(), name='agent-chat'),
    path('amadeus-agent/', AmadeusAgentAPIView.as_view(), name='amadeus-agent'),
]
