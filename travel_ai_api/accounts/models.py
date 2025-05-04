from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
import uuid

class User(AbstractUser):
    """
    Custom User model with additional fields for travel preferences
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    # Travel preferences
    preferred_destinations = models.JSONField(default=dict, blank=True, null=True)
    travel_preferences = models.JSONField(default=dict, blank=True, null=True)
    
    # Passport information
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    passport_expiry_date = models.DateField(blank=True, null=True)
    passport_country = models.CharField(max_length=100, blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
