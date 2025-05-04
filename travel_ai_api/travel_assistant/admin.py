from django.contrib import admin
from .models import (
    TravelRequest, TripPlan, Document, Trip, Hotel, 
    Flight, Activity, Visa, Travelling
)

# Register your models here.

@admin.register(TravelRequest)
class TravelRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'origin', 'destination', 'start_date', 'end_date', 'travelers', 'created_at')
    search_fields = ('origin', 'destination', 'user_query')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'travel_request', 'estimated_cost', 'created_at')
    search_fields = ('title', 'summary')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'document_type', 'uploaded_at')
    search_fields = ('title', 'description')
    list_filter = ('document_type', 'uploaded_at')
    date_hierarchy = 'uploaded_at'


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'origin', 'destination', 'start_date', 'end_date', 'status')
    search_fields = ('title', 'description', 'origin', 'destination')
    list_filter = ('status', 'start_date')
    date_hierarchy = 'start_date'
    filter_horizontal = ('companions',)


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'trip', 'user', 'city', 'check_in_date', 'check_out_date', 'status')
    search_fields = ('name', 'address', 'city', 'booking_reference')
    list_filter = ('status', 'check_in_date')
    date_hierarchy = 'check_in_date'
    filter_horizontal = ('documents',)


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('id', 'airline', 'flight_number', 'trip', 'user', 'departure_city', 'arrival_city', 
                  'departure_datetime', 'status')
    search_fields = ('airline', 'flight_number', 'departure_city', 'arrival_city', 'booking_reference')
    list_filter = ('status', 'departure_datetime', 'seat_class')
    date_hierarchy = 'departure_datetime'
    filter_horizontal = ('documents',)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'trip', 'user', 'location', 'start_datetime', 'activity_type', 'status')
    search_fields = ('name', 'description', 'location', 'booking_reference')
    list_filter = ('status', 'start_datetime', 'activity_type')
    date_hierarchy = 'start_datetime'
    filter_horizontal = ('documents',)


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'visa_type', 'country_of_issue', 'expiry_date', 'status')
    search_fields = ('visa_type', 'country_of_issue', 'visa_number')
    list_filter = ('status', 'expiry_date', 'entries')
    date_hierarchy = 'expiry_date'
    filter_horizontal = ('trips', 'documents')


@admin.register(Travelling)
class TravellingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'trip', 'current_location', 'current_country', 'status', 'last_update_datetime')
    search_fields = ('current_location', 'current_country', 'next_destination')
    list_filter = ('status', 'last_update_datetime')
    date_hierarchy = 'last_update_datetime'
