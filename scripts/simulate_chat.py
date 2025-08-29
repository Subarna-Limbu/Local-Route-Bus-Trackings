import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_transport.settings')
django.setup()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from core.models import Bus

User = get_user_model()

# find a user and a bus with a driver
u = User.objects.filter(is_staff=False).exclude(username='').first()
b = Bus.objects.exclude(driver__isnull=True).first()
print('Using user id, bus id:', getattr(u,'id',None), getattr(b,'id',None))
if u and b and b.driver and getattr(b.driver,'user',None):
    channel_layer = get_channel_layer()
    # build both chat room and driver group
    chat_room = f'user_{u.id}_driver_{b.driver.user.id}'
    chat_group = f'chat_{chat_room}'
    driver_group = f'driver_{b.driver.user.id}'
    payload = {
        'type': 'chat_message_forward',
        'sender_id': u.id,
        'sender_name': u.username,
        'recipient_id': b.driver.user.id,
        'content': 'Hello from simulated user',
        'bus_id': b.id,
    }
    async_to_sync(channel_layer.group_send)(chat_group, payload)
    async_to_sync(channel_layer.group_send)(driver_group, payload)
    print('Sent to', chat_group, 'and', driver_group)
else:
    print('No suitable user/bus found')
