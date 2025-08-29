import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','smart_transport.settings')
import django
django.setup()
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
layer = get_channel_layer()
payload = {'type':'chat_message','sender_id':8,'sender_name':'Ash Ketchum','recipient_id':None,'content':'thik xa','bus_id':2}
async_to_sync(layer.group_send)('driver_8',{'type':'chat_message','sender_id':8,'sender_name':'Ash Ketchum','recipient_id':None,'content':'thik xa','bus_id':2})
print('Sent payload to driver_8 group')
