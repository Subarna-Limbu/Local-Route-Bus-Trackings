import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Bus, Message, PickupRequest


User = get_user_model()


class LocationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for bus location updates.

    Clients connect to ws/location/<bus_id>/ and receive broadcasts about location.
    Drivers may send messages of type {"type":"location","lat":...,"lng":...}
    which are persisted (to Bus if fields exist, otherwise to Driver) and broadcasted.
    """

    async def connect(self):
        self.bus_id = self.scope['url_route']['kwargs'].get('bus_id')
        self.group_name = f'bus_{self.bus_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
        except Exception:
            return

        if data.get('type') == 'location':
            lat = data.get('lat')
            lng = data.get('lng')
            await self._save_bus_location(self.bus_id, lat, lng)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'location_update',
                    'lat': lat,
                    'lng': lng,
                }
            )

    async def location_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'lat': event.get('lat'),
            'lng': event.get('lng'),
        }))

    @database_sync_to_async
    def _save_bus_location(self, bus_id, lat, lng):
        try:
            bus = Bus.objects.filter(id=bus_id).first()
            if not bus:
                return
            # Prefer storing on Bus if fields exist
            if hasattr(bus, 'current_lat') and hasattr(bus, 'current_lng'):
                bus.current_lat = lat
                bus.current_lng = lng
                bus.save()
            else:
                # Fallback: update the driver profile
                if bus.driver:
                    bus.driver.current_lat = lat
                    bus.driver.current_lng = lng
                    bus.driver.save()
        except Exception:
            pass


class ChatConsumer(AsyncWebsocketConsumer):
    """Chat and pickup notification consumer.

    Connect to ws/chat/<room_name>/, where room_name can be like 'user_<uid>_driver_<did>'
    or any identifier shared by both participants.
    """

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name')
        self.group_name = f'chat_{self.room_name}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # If the connecting user is a driver, also add them to their driver-specific group
        user = self.scope.get('user')
        try:
            if user and getattr(user, 'is_authenticated', False) and hasattr(user, 'driver_profile'):
                driver_group = f'driver_{user.id}'
                await self.channel_layer.group_add(driver_group, self.channel_name)
        except Exception:
            pass
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
        except Exception:
            return

        msg_type = data.get('type')
        if msg_type == 'chat_message':
            content = data.get('content')
            sender = self.scope.get('user') if self.scope.get('user').is_authenticated else None
            recipient_id = data.get('recipient_id')
            bus_id = data.get('bus_id')
            if sender and recipient_id and content:
                await self._create_message(sender.id, recipient_id, bus_id, content)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message_forward',
                    'sender_id': sender.id if sender else None,
                    'recipient_id': recipient_id,
                    'content': content,
                    'bus_id': bus_id,
                }
            )

            # Additionally forward to recipient's driver/user groups so both ends receive messages
            try:
                # If recipient_id provided and recipient is a driver, notify their driver group
                if recipient_id:
                    await self.channel_layer.group_send(
                        f'driver_{recipient_id}',
                        {
                            'type': 'chat_message_forward',
                            'sender_id': sender.id if sender else None,
                            'recipient_id': recipient_id,
                            'content': content,
                            'bus_id': bus_id,
                        }
                    )

                # If message is related to a bus, notify the bus driver group as well
                if bus_id:
                    try:
                        bus_obj = await database_sync_to_async(Bus.objects.get)(id=bus_id)
                        if bus_obj and bus_obj.driver and bus_obj.driver.user:
                            driver_user_id = bus_obj.driver.user.id
                            await self.channel_layer.group_send(
                                f'driver_{driver_user_id}',
                                {
                                    'type': 'chat_message_forward',
                                    'sender_id': sender.id if sender else None,
                                    'recipient_id': recipient_id,
                                    'content': content,
                                    'bus_id': bus_id,
                                }
                            )
                    except Exception:
                        pass
                # Also forward to the user's chat room so the connected passenger receives it
                if recipient_id and sender:
                    try:
                        user_room = f'chat_user_{recipient_id}_driver_{sender.id}'
                        await self.channel_layer.group_send(
                            f'{user_room}',
                            {
                                'type': 'chat_message_forward',
                                'sender_id': sender.id if sender else None,
                                'recipient_id': recipient_id,
                                'content': content,
                                'bus_id': bus_id,
                            }
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        elif msg_type == 'pickup_request':
            user = self.scope.get('user') if self.scope.get('user').is_authenticated else None
            bus_id = data.get('bus_id')
            stop = data.get('stop')
            message = data.get('message', '')
            if user and bus_id and stop:
                pickup = await self._create_pickup_request(user.id, bus_id, stop, message)
                # Notify driver's personal group if we can resolve driver user id
                if pickup and pickup.bus and pickup.bus.driver and pickup.bus.driver.user:
                    driver_user_id = pickup.bus.driver.user.id
                    driver_group = f'driver_{driver_user_id}'
                    await self.channel_layer.group_send(
                        driver_group,
                        {
                            'type': 'pickup_notification',
                                'pickup_id': pickup.id,
                                'user_id': pickup.user.id,
                                'user_username': getattr(pickup.user, 'username', None),
                            'bus_id': pickup.bus.id,
                            'stop': pickup.stop,
                            'message': pickup.message,
                        }
                    )

    async def chat_message_forward(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'sender_id': event.get('sender_id'),
            'recipient_id': event.get('recipient_id'),
            'content': event.get('content'),
            'bus_id': event.get('bus_id'),
        }))

    async def pickup_notification(self, event):
        pickup_id = event.get('pickup_id')
        await self.send(text_data=json.dumps({
            'type': 'pickup_notification',
            'pickup_id': pickup_id,
            'user_id': event.get('user_id'),
            'bus_id': event.get('bus_id'),
            'stop': event.get('stop'),
            'message': event.get('message'),
        }))
        # mark as seen by driver in DB
        try:
            if pickup_id:
                await database_sync_to_async(self._mark_pickup_seen)(pickup_id)
        except Exception:
            pass

    @database_sync_to_async
    def _create_message(self, sender_id, recipient_id, bus_id, content):
        try:
            sender = User.objects.get(id=sender_id)
            recipient = User.objects.get(id=recipient_id)
            bus = Bus.objects.filter(id=bus_id).first() if bus_id else None
            return Message.objects.create(sender=sender, recipient=recipient, bus=bus, content=content)
        except Exception:
            return None

    @database_sync_to_async
    def _create_pickup_request(self, user_id, bus_id, stop, message):
        try:
            user = User.objects.get(id=user_id)
            bus = Bus.objects.get(id=bus_id)
            return PickupRequest.objects.create(user=user, bus=bus, stop=stop, message=message)
        except Exception:
            return None

    def _mark_pickup_seen(self, pickup_id):
        try:
            p = PickupRequest.objects.filter(id=pickup_id).first()
            if p:
                p.seen_by_driver = True
                p.save(update_fields=['seen_by_driver'])
                return True
        except Exception:
            return False

