from channels.routing import ProtocolTypeRouter, URLRouter
import core.routing

application = ProtocolTypeRouter({
    'websocket': URLRouter(
        core.routing.websocket_urlpatterns
    )
})
