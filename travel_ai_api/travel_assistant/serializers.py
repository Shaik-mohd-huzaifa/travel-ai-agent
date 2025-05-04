from rest_framework import serializers
from .models import (
    TravelRequest,
    TripPlan,
    SearchQuery,
    HotelResult,
    FlightResult,
    ActivityResult,
)


class TravelRequestSerializer(serializers.ModelSerializer):
    """Serializer for TravelRequest model"""
    
    class Meta:
        model = TravelRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class TripPlanSerializer(serializers.ModelSerializer):
    """Serializer for TripPlan model"""
    cost_breakdown = serializers.SerializerMethodField()
    references = serializers.SerializerMethodField()
    
    class Meta:
        model = TripPlan
        fields = '__all__'
        read_only_fields = ('id', 'created_at')
    
    def get_cost_breakdown(self, obj):
        """Return cost breakdown as a dictionary"""
        return obj.get_cost_breakdown()
    
    def get_references(self, obj):
        """Return references as a list"""
        return obj.get_references()


class TravelPlanningRequestSerializer(serializers.Serializer):
    """Serializer for handling travel planning requests"""
    query = serializers.CharField(required=True, help_text="Natural language query describing the travel plans")
    
    # Optional fields for structured input
    origin = serializers.CharField(required=False, allow_blank=True)
    destination = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    budget = serializers.CharField(required=False, allow_blank=True)
    travelers = serializers.IntegerField(required=False, default=1)
    preferences = serializers.CharField(required=False, allow_blank=True)


class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = '__all__'


class HotelResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelResult
        fields = '__all__'


class FlightResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightResult
        fields = '__all__'


class ActivityResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityResult
        fields = '__all__'
