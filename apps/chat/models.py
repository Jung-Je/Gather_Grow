from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class ChatMessage(BaseModel):
    """채팅 메시지 모델

    모임 내에서 주고받는 채팅 메시지를 저장합니다.
    """

    gathering = models.ForeignKey(
        "gatherings.Gathering",
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name="모임",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name="작성자",
    )
    message = models.TextField(verbose_name="메시지 내용")

    class Meta:
        db_table = "chat_messages"
        verbose_name = "채팅 메시지"
        verbose_name_plural = "채팅 메시지"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gathering", "-created_at"], name="idx_chat_gathering_created"),
            models.Index(fields=["user"], name="idx_chat_user"),
        ]

    def __str__(self):
        return f"[{self.gathering.title}] {self.user.username}: {self.message[:30]}"
