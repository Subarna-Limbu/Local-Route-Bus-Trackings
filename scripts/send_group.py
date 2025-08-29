import asyncio
from channels.layers import get_channel_layer

async def main():
    cl = get_channel_layer()
    await cl.group_send('driver_8', {
        'type': 'chat_message_forward',
        'sender_id': 999,
        'sender_name': 'server_test',
        'recipient_id': 8,
        'content': 'hello from server group_send test',
        'bus_id': 2,
    })
    print('Sent group_send to driver_8')

if __name__ == '__main__':
    asyncio.run(main())
