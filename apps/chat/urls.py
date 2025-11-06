from django.urls import path

from apps.chat.views.message_views import ChatMessageListView

app_name = "chat"

urlpatterns = [
    # 채팅 메시지 API
    path("<int:gathering_id>/messages/", ChatMessageListView.as_view(), name="message-list"),
]
