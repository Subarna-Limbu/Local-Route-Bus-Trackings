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
    # Live location fields (optional)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)

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


class Bookmark(models.Model):
    """A bookmark created by a user for a specific bus."""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='bookmarks')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'bus')

    def __str__(self):
        return f"{self.user.username} -> {self.bus.number_plate}"


class PickupRequest(models.Model):
    """A user's pickup request/notification to a driver for a bus."""
    STATUS_PENDING = 'pending'
    STATUS_ACK = 'acknowledged'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACK, 'Acknowledged'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='pickup_requests')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='pickup_requests')
    stop = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    seen_by_driver = models.BooleanField(default=False)

    def __str__(self):
        return f"PickupRequest({self.user.username} -> {self.bus.number_plate} @ {self.stop})"


class Message(models.Model):
    """Simple chat message between user and driver (both are User objects).

    Message.sender is the Django User who sent the message. recipient is the target User.
    Optionally associated with a bus.
    """
    sender = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='received_messages')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message({self.sender.username} -> {self.recipient.username})"
