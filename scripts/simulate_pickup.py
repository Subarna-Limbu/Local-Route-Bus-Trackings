from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from core.models import Bus, PickupRequest
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_transport.settings')
django.setup()

User = get_user_model()

u = User.objects.filter(is_staff=False).exclude(username='').first()
b = Bus.objects.exclude(driver__isnull=True).first()
print('User,Bus:', getattr(u,'id',None), getattr(b,'id',None))
if u and b and b.driver and getattr(b.driver,'user',None):
    p = PickupRequest.objects.create(user=u, bus=b, stop='balkhu', message='wait about 5 min.')
    ch = get_channel_layer()
    dg = f'driver_{b.driver.user.id}'
    async_to_sync(ch.group_send)(dg, {
        'type': 'pickup_notification',
        'pickup_id': p.id,
        'user_id': u.id,
        'user_username': u.username,
        'bus_id': b.id,
        'stop': p.stop,
        'message': p.message,
    })
    print('Sent pickup', p.id, 'to', dg)
else:
    print('No suitable user or bus found to simulate pickup')
