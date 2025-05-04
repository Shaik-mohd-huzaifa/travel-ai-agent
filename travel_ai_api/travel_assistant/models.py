from django.db import models
import uuid
import json
from django.utils import timezone
from django.conf import settings

class TravelRequest(models.Model):
    """Model to store travel planning requests from users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_query = models.TextField(help_text="The original query from the user")
    
    # Travel details
    origin = models.CharField(max_length=100, blank=True, null=True)
    destination = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    budget = models.CharField(max_length=50, blank=True, null=True)
    travelers = models.PositiveIntegerField(default=1)
    preferences = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Travel Request: {self.origin} to {self.destination}"
    
    class Meta:
        ordering = ['-created_at']


class TripPlan(models.Model):
    """Model to store generated trip plans"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    travel_request = models.ForeignKey(TravelRequest, on_delete=models.CASCADE, related_name='trip_plans')
    
    # Plan details
    title = models.CharField(max_length=255)
    summary = models.TextField()
    itinerary = models.TextField(help_text="Detailed day-by-day itinerary")
    
    # Accommodations, transportation, activities
    accommodations = models.TextField(blank=True, null=True)
    transportation = models.TextField(blank=True, null=True)
    activities = models.TextField(blank=True, null=True)
    
    # Cost estimates
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_breakdown = models.TextField(blank=True, null=True, help_text="JSON string of cost breakdown")
    
    # References
    references = models.TextField(blank=True, null=True, help_text="JSON string of reference URLs")
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Trip Plan: {self.title}"
    
    def get_cost_breakdown(self):
        """Returns cost breakdown as a dictionary"""
        if self.cost_breakdown:
            try:
                return json.loads(self.cost_breakdown)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_references(self):
        """Returns references as a list"""
        if self.references:
            try:
                return json.loads(self.references)
            except json.JSONDecodeError:
                return []
        return []
    
    class Meta:
        ordering = ['-created_at']


class Document(models.Model):
    """Model for storing document files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    document_type = models.CharField(max_length=50, choices=[
        ('passport', 'Passport'),
        ('visa', 'Visa'),
        ('ticket', 'Ticket'),
        ('booking', 'Booking Confirmation'),
        ('insurance', 'Travel Insurance'),
        ('other', 'Other')
    ])
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.get_document_type_display()}"
    
    class Meta:
        ordering = ['-uploaded_at']


class Trip(models.Model):
    """Model for storing trip information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    trip_plan = models.ForeignKey(TripPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='associated_trips')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Trip details
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Budget
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('planning', 'Planning'),
        ('booked', 'Booked'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='planning')
    
    # Travelers
    number_of_adults = models.PositiveIntegerField(default=1)
    number_of_children = models.PositiveIntegerField(default=0)
    
    # Travel companions
    companions = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='companion_trips')
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"
    
    class Meta:
        ordering = ['-start_date']


class Hotel(models.Model):
    """Model for storing hotel booking information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='hotels')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hotel_bookings')
    
    # Hotel details
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    
    # Booking details
    booking_reference = models.CharField(max_length=100, blank=True, null=True)
    confirmation_number = models.CharField(max_length=100, blank=True, null=True)
    booking_platform = models.CharField(max_length=100, blank=True, null=True)
    
    # Room details
    room_type = models.CharField(max_length=100, blank=True, null=True)
    number_of_rooms = models.PositiveIntegerField(default=1)
    
    # Cost
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Contact information
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    
    # Amenities and notes
    amenities = models.JSONField(default=list, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('reserved', 'Reserved'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], default='reserved')
    
    # Documents
    documents = models.ManyToManyField(Document, blank=True, related_name='hotel_documents')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.check_in_date} to {self.check_out_date}"
    
    class Meta:
        ordering = ['check_in_date']


class Flight(models.Model):
    """Model for storing flight booking information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='flights')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='flight_bookings')
    
    # Flight details
    airline = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=20)
    departure_airport = models.CharField(max_length=100)
    departure_city = models.CharField(max_length=100)
    arrival_airport = models.CharField(max_length=100)
    arrival_city = models.CharField(max_length=100)
    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()
    
    # Booking details
    booking_reference = models.CharField(max_length=100, blank=True, null=True)
    confirmation_number = models.CharField(max_length=100, blank=True, null=True)
    booking_platform = models.CharField(max_length=100, blank=True, null=True)
    
    # Seat details
    seat_class = models.CharField(max_length=50, choices=[
        ('economy', 'Economy'),
        ('premium_economy', 'Premium Economy'),
        ('business', 'Business'),
        ('first', 'First Class')
    ], default='economy')
    seat_number = models.CharField(max_length=10, blank=True, null=True)
    
    # Cost
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Flight type
    flight_type = models.CharField(max_length=20, choices=[
        ('outbound', 'Outbound'),
        ('return', 'Return'),
        ('connection', 'Connection'),
        ('one_way', 'One Way')
    ])
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('reserved', 'Reserved'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('missed', 'Missed')
    ], default='reserved')
    
    # Documents
    documents = models.ManyToManyField(Document, blank=True, related_name='flight_documents')
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.airline} {self.flight_number} - {self.departure_city} to {self.arrival_city}"
    
    class Meta:
        ordering = ['departure_datetime']


class Activity(models.Model):
    """Model for storing activity booking information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_bookings')
    
    # Activity details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(blank=True, null=True)
    
    # Booking details
    booking_reference = models.CharField(max_length=100, blank=True, null=True)
    confirmation_number = models.CharField(max_length=100, blank=True, null=True)
    booking_platform = models.CharField(max_length=100, blank=True, null=True)
    
    # Cost
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Activity type
    activity_type = models.CharField(max_length=50, choices=[
        ('tour', 'Tour'),
        ('attraction', 'Attraction'),
        ('event', 'Event'),
        ('transportation', 'Transportation'),
        ('dining', 'Dining'),
        ('other', 'Other')
    ], default='tour')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('planned', 'Planned'),
        ('booked', 'Booked'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='planned')
    
    # Documents
    documents = models.ManyToManyField(Document, blank=True, related_name='activity_documents')
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.start_datetime.date()}"
    
    class Meta:
        ordering = ['start_datetime']
        verbose_name_plural = 'Activities'


class Visa(models.Model):
    """Model for storing visa information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visas')
    trips = models.ManyToManyField(Trip, blank=True, related_name='visas')
    
    # Visa details
    visa_type = models.CharField(max_length=100)
    country_of_issue = models.CharField(max_length=100)
    visa_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Validity
    issue_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField()
    entries = models.CharField(max_length=20, choices=[
        ('single', 'Single Entry'),
        ('double', 'Double Entry'),
        ('multiple', 'Multiple Entry')
    ], default='single')
    
    # Application
    application_date = models.DateField(blank=True, null=True)
    processing_time = models.PositiveIntegerField(blank=True, null=True, help_text="Processing time in days")
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('planning', 'Planning to Apply'),
        ('applied', 'Applied'),
        ('in_process', 'In Process'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired')
    ], default='planning')
    
    # Documents
    documents = models.ManyToManyField(Document, blank=True, related_name='visa_documents')
    
    # Notes
    requirements = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.country_of_issue} Visa - {self.visa_type} - Expires: {self.expiry_date}"
    
    class Meta:
        ordering = ['-expiry_date']


class Travelling(models.Model):
    """Model for tracking ongoing travel"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='travel_history')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='travel_logs')
    
    # Current location
    current_location = models.CharField(max_length=255)
    current_country = models.CharField(max_length=100)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('not_started', 'Not Started'),
        ('en_route', 'En Route'),
        ('at_destination', 'At Destination'),
        ('returning', 'Returning'),
        ('completed', 'Completed')
    ], default='not_started')
    
    # Travel progress
    progress_percentage = models.PositiveIntegerField(default=0)
    
    # Updates
    last_update_datetime = models.DateTimeField()
    next_destination = models.CharField(max_length=255, blank=True, null=True)
    next_activity = models.ForeignKey(Activity, on_delete=models.SET_NULL, null=True, blank=True, related_name='travellers')
    
    # Emergency information
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_email = models.EmailField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.current_location} - {self.status}"
    
    class Meta:
        ordering = ['-last_update_datetime']
        verbose_name_plural = 'Travelling Records'


class SearchQuery(models.Model):
    """Search query for flights, hotels, or activities."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name="search_queries",
        null=True, blank=True
    )
    query_type = models.CharField(
        max_length=20,
        choices=[
            ('hotels', 'Hotels'),
            ('flights', 'Flights'),
            ('activities', 'Activities'),
            ('trip', 'Trip')
        ]
    )
    query_params = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.query_type} search: {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        verbose_name_plural = "Search queries"
        ordering = ['-created_at']


class HotelResult(models.Model):
    """Hotel search result from a search query."""
    search_query = models.ForeignKey(
        SearchQuery, 
        on_delete=models.CASCADE, 
        related_name="hotel_results"
    )
    hotel_name = models.CharField(max_length=255)
    source = models.CharField(max_length=50)  # e.g., "Booking.com", "Airbnb"
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    location = models.CharField(max_length=255)
    url = models.URLField(max_length=1000, blank=True)
    result_data = models.JSONField(default=dict)  # Full result data
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.hotel_name} ({self.source})"
    
    class Meta:
        ordering = ['-rating', 'price']


class FlightResult(models.Model):
    """Flight search result from a search query."""
    search_query = models.ForeignKey(
        SearchQuery, 
        on_delete=models.CASCADE, 
        related_name="flight_results"
    )
    airline = models.CharField(max_length=255)
    source = models.CharField(max_length=50)  # e.g., "Skyscanner", "Kayak"
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration = models.CharField(max_length=50, blank=True)
    stops = models.CharField(max_length=50, default="Direct")
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    result_data = models.JSONField(default=dict)  # Full result data
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.airline}: {self.origin} to {self.destination}"
    
    class Meta:
        ordering = ['price']


class ActivityResult(models.Model):
    """Activity search result from a search query."""
    search_query = models.ForeignKey(
        SearchQuery, 
        on_delete=models.CASCADE, 
        related_name="activity_results"
    )
    activity_name = models.CharField(max_length=255)
    source = models.CharField(max_length=50)  # e.g., "TripAdvisor", "Viator"
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(max_length=1000, blank=True)
    result_data = models.JSONField(default=dict)  # Full result data
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.activity_name} ({self.source})"
    
    class Meta:
        ordering = ['-rating']
