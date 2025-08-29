from django.contrib import admin
from .models import Driver, BusRoute, Bus, Seat

admin.site.register(Driver)
admin.site.register(BusRoute)
admin.site.register(Bus)
admin.site.register(Seat)
