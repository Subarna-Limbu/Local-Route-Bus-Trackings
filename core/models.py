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


class Bus(models.Model):
    number_plate = models.CharField(max_length=50)
    total_seats = models.PositiveIntegerField(default=25)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='buses')

    def __str__(self):
        return f"{self.number_plate} ({self.total_seats} seats)"

    def create_seats(self):
        # Create seats if not already created
        if not self.seats.exists():
            for i in range(1, self.total_seats + 1):
                Seat.objects.create(bus=self, seat_number=i)


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.PositiveIntegerField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Bus {self.bus.number_plate} - Seat {self.seat_number}"


class BusRoute(models.Model):
    name = models.CharField(max_length=100)
    bus = models.OneToOneField(Bus, on_delete=models.CASCADE, related_name='route', null=True, blank=True)
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='routes')
    stops = models.TextField(
        help_text='Comma-separated stops (e.g., "Stop1,Stop2,Stop3")')
    is_active = models.BooleanField(default=False)

    def get_stops_list(self):
        return [stop.strip() for stop in self.stops.split(",")]

    def __str__(self):
        return self.name
