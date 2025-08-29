import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Bus, Message, PickupRequest, Driver
import logging

logger = logging.getLogger(__name__)


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
        try:
            user = self.scope.get('user')
            logger.info('LocationConsumer.connect: bus_id=%s group=%s channel=%s user_id=%s', self.bus_id, self.group_name, self.channel_name, getattr(user, 'id', None))
        except Exception:
            logger.exception('LocationConsumer.connect logging failed')

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
    """Simpler chat consumer.

    Behavior:
    - On connect, subscribe the socket to a personal group: 'user_<id>' or 'driver_<id>'.
    - Also subscribe to the legacy chat_<room_name> group for backward compatibility.
    - When receiving a 'chat_message', persist it and forward it as a text JSON frame
      to the recipient's personal group and to the sender's personal group (echo).
    This guarantees the driver and the passenger will both receive the message.
    """

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name')
        # Add legacy chat room subscription (keeps compatibility with existing templates)
        if self.room_name:
            try:
                await self.channel_layer.group_add(f'chat_{self.room_name}', self.channel_name)
            except Exception:
                logger.exception('Failed to add to legacy chat group chat_%s', self.room_name)

        user = self.scope.get('user')
        if user and getattr(user, 'is_authenticated', False):
            # subscribe to personal group depending on role; perform DB check in thread
            try:
                is_driver = await database_sync_to_async(lambda uid: Driver.objects.filter(user__id=uid).exists())(user.id)
                # If this socket connected via a legacy room like 'user_<uid>_driver_<did>',
                # we avoid adding the duplicate personal 'user_<uid>' group to prevent double delivery.
                connected_via_legacy_user_room = False
                if self.room_name and str(self.room_name).startswith('user_'):
                    connected_via_legacy_user_room = True

                if is_driver:
                    await self.channel_layer.group_add(f'driver_{user.id}', self.channel_name)
                else:
                    if not connected_via_legacy_user_room:
                        await self.channel_layer.group_add(f'user_{user.id}', self.channel_name)
                    else:
                        logger.info('ChatConsumer: user %s connected via legacy room %s, skipping user_%s personal group', user.id, self.room_name, user.id)
            except Exception:
                logger.exception('Failed to add user %s to personal group', getattr(user, 'id', None))

        await self.accept()
        try:
            logger.info('ChatConsumer.connect: user_id=%s room_name=%s channel=%s', getattr(user, 'id', None), self.room_name, self.channel_name)
        except Exception:
            logger.exception('ChatConsumer.connect logging failed')

    async def disconnect(self, close_code):
        # Attempt to remove from both legacy and personal groups
        if self.room_name:
            try:
                await self.channel_layer.group_discard(f'chat_{self.room_name}', self.channel_name)
            except Exception:
                pass
        user = self.scope.get('user')
        try:
            logger.info('ChatConsumer.disconnect: user_id=%s room_name=%s channel=%s code=%s', getattr(user, 'id', None), self.room_name, self.channel_name, close_code)
        except Exception:
            logger.exception('ChatConsumer.disconnect logging failed')
        if user and getattr(user, 'is_authenticated', False):
            try:
                if hasattr(user, 'driver_profile'):
                    await self.channel_layer.group_discard(f'driver_{user.id}', self.channel_name)
                else:
                    await self.channel_layer.group_discard(f'user_{user.id}', self.channel_name)
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        # Only accept textual JSON frames
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except Exception:
            return
        try:
            logger.info('ChatConsumer.receive: user=%s data=%s', getattr(self.scope.get('user'), 'id', None), data)
        except Exception:
            logger.exception('ChatConsumer.receive logging failed')

        msg_type = data.get('type')
        if msg_type != 'chat_message':
            return

        sender = self.scope.get('user') if self.scope.get('user') and self.scope.get('user').is_authenticated else None
        if not sender:
            return

        content = data.get('content')
        recipient_id = data.get('recipient_id')
        bus_id = data.get('bus_id')

        # If recipient not provided, try to resolve from bus -> driver user id
        if not recipient_id and bus_id:
            try:
                # Only use bus->driver mapping when the sender is NOT a driver (i.e., passenger sending to driver)
                is_sender_driver = await database_sync_to_async(lambda uid: Driver.objects.filter(user__id=uid).exists())(sender.id)
                if not is_sender_driver:
                    bus_obj = await database_sync_to_async(Bus.objects.select_related('driver__user').get)(id=bus_id)
                    if bus_obj and bus_obj.driver and bus_obj.driver.user:
                        recipient_id = bus_obj.driver.user.id
                        logger.info('ChatConsumer.resolved_recipient_from_bus: sender=%s bus=%s recipient=%s', sender.id, bus_id, recipient_id)
                else:
                    # skip bus->driver resolution for drivers; they'll use last-contact fallback below
                    logger.info('ChatConsumer.skipping_bus_resolution_for_driver_sender=%s', sender.id)
            except Exception:
                recipient_id = None

        # If still no recipient and sender is a driver, try to pick the most recent user who messaged this driver
        if not recipient_id:
            try:
                # determine if sender is a driver
                is_sender_driver = await database_sync_to_async(lambda uid: Driver.objects.filter(user__id=uid).exists())(sender.id)
                if is_sender_driver:
                    def _get_last_user_to_driver(sid):
                        last = Message.objects.filter(recipient__id=sid).exclude(sender__id=sid).order_by('-created_at').first()
                        return last.sender.id if last else None
                    last_user = await database_sync_to_async(_get_last_user_to_driver)(sender.id)
                    if last_user:
                        recipient_id = last_user
                        logger.info('ChatConsumer resolved recipient for driver %s -> user %s (last contact)', sender.id, recipient_id)
            except Exception:
                pass

        if not recipient_id or not content:
            return

        # persist the message
        await self._create_message(sender.id, recipient_id, bus_id, content)

        sender_name = getattr(sender, 'username', None)
        payload = {
            'type': 'chat_message',
            'sender_id': sender.id,
            'sender_name': sender_name,
            'recipient_id': recipient_id,
            'content': content,
            'bus_id': bus_id,
        }

        # forward to recipient personal group (user_<id>)
        try:
            await self.channel_layer.group_send(f'user_{recipient_id}', {
                'type': 'chat_message_forward',
                **payload,
            })
            logger.info('ChatConsumer.forwarded to user_%s payload=%s', recipient_id, {'sender_id': sender.id, 'content': content})
        except Exception:
            logger.exception('Failed to forward chat to user_%s', recipient_id)

        # Also forward to legacy chat room name so clients connected to chat_user_<rid>_driver_<sid> receive it
        try:
            legacy_room = f'chat_user_{recipient_id}_driver_{sender.id}'
            await self.channel_layer.group_send(legacy_room, {
                'type': 'chat_message_forward',
                **payload,
            })
            logger.info('ChatConsumer.forwarded to legacy %s payload=%s', legacy_room, {'sender_id': sender.id, 'content': content})
        except Exception:
            logger.exception('Failed to forward to legacy room for recipient %s', recipient_id)

        # if recipient is a driver, also forward to driver_<id> group (but avoid duplicate when recipient==sender)
        try:
            if recipient_id != sender.id:
                await self.channel_layer.group_send(f'driver_{recipient_id}', {
                    'type': 'chat_message_forward',
                    **payload,
                })
                logger.info('ChatConsumer.forwarded to driver_%s payload=%s', recipient_id, {'sender_id': sender.id, 'content': content})
            else:
                logger.info('ChatConsumer.skipped_driver_forward_to_self for %s', recipient_id)
        except Exception:
            # not fatal if group doesn't exist
            logger.exception('ChatConsumer.failed_forward_driver_%s', recipient_id)

        # echo back to sender's personal group so sender's UI shows the sent message
        try:
            # Drivers should see their own message in driver_<sender.id>
            is_sender_driver = await database_sync_to_async(lambda uid: Driver.objects.filter(user__id=uid).exists())(sender.id)
            if is_sender_driver:
                await self.channel_layer.group_send(f'driver_{sender.id}', {
                    'type': 'chat_message_forward',
                    **payload,
                })
            else:
                await self.channel_layer.group_send(f'user_{sender.id}', {
                    'type': 'chat_message_forward',
                    **payload,
                })
                # also send to legacy room so users connected via chat_user_<uid>_driver_<did> receive their own echo
                try:
                    legacy_echo = f'chat_user_{sender.id}_driver_{recipient_id}'
                    await self.channel_layer.group_send(legacy_echo, {
                        'type': 'chat_message_forward',
                        **payload,
                    })
                    logger.info('ChatConsumer.echoed to legacy %s for sender %s', legacy_echo, sender.id)
                except Exception:
                    logger.exception('ChatConsumer.failed_legacy_echo for sender %s', sender.id)
            logger.info('ChatConsumer.echoed to sender %s payload=%s', sender.id, {'recipient_id': recipient_id, 'content': content})
        except Exception:
            logger.exception('ChatConsumer.failed_echo_sender %s', sender.id)

    async def chat_message_forward(self, event):
        # Always send text JSON frames
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'recipient_id': event.get('recipient_id'),
            'content': event.get('content'),
            'bus_id': event.get('bus_id'),
        }))

    # Backwards-compatible handler for events with type 'chat_message'
    # Some producers may send events with 'type': 'chat_message' to legacy groups.
    async def chat_message(self, event):
        # delegate to the same forwarder
        await self.chat_message_forward(event)

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

