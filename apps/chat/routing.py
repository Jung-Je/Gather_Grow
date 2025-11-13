from django.urls import path

from apps.chat.consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/chat/<int:gathering_id>/", ChatConsumer.as_asgi()),
]
