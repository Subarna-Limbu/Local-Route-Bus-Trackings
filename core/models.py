from django.db import models
from django.contrib.auth.models import User


class Driver(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='driver_profile')
    phone = models.CharField(max_length=15)
    vehicle_number = models.CharField(max_length=20)
    verified = models.BooleanField(default=False)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.user.username


class BusRoute(models.Model):
    name = models.CharField(max_length=100)
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='routes')
    stops = models.TextField(
        help_text='Comma-separated stops (e.g., "Stop1,Stop2,Stop3")')
    is_active = models.BooleanField(default=False)

    def get_stops_list(self):
        return [stop.strip() for stop in self.stops.split(",")]

    def __str__(self):
        return self.name
