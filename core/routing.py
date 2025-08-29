from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/location/(?P<bus_id>\w+)/$', consumers.LocationConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<room_name>[A-Za-z0-9_\-]+)/$', consumers.ChatConsumer.as_asgi()),
]
