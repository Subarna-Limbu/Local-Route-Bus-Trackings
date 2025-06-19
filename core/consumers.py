import json
from channels.generic.websocket import AsyncWebsocketConsumer


class LocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.bus_id = self.scope['url_route']['kwargs']['bus_id']
        self.group_name = f'bus_{self.bus_id}'
        # Join the bus group so that we can broadcast location updates.
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Expect JSON data from driver with latitude and longitude.
        data = json.loads(text_data)
        latitude = data.get('lat')
        longitude = data.get('lng')
        # Broadcast the location update to all connected websocket clients in this bus group.
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'location_update',
                'lat': latitude,
                'lng': longitude,
            }
        )

    async def location_update(self, event):
        # Send the update event with location data.
        await self.send(text_data=json.dumps({
            'lat': event['lat'],
            'lng': event['lng']
        }))
