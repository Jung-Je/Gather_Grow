from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class ChatMessage(BaseModel):
    """채팅 메시지 모델

    모임 내에서 주고받는 채팅 메시지를 저장합니다.
    텍스트 메시지와 이미지를 함께 보낼 수 있습니다.
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
    message = models.TextField(blank=True, null=True, verbose_name="메시지 내용")
    image = models.ImageField(
        upload_to="chat_images/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name="이미지",
    )

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
        """채팅 메시지의 문자열 표현을 반환합니다.

        Returns:
            str: '[모임명] 사용자명: 메시지 미리보기' 형식의 문자열
        """
        msg_preview = self.message[:30] if self.message else "[이미지]"
        return f"[{self.gathering.title}] {self.user.username}: {msg_preview}"

    @property
    def has_image(self):
        """이미지 첨부 여부"""
        return bool(self.image)

    @property
    def has_text(self):
        """텍스트 내용 여부"""
        return bool(self.message)
