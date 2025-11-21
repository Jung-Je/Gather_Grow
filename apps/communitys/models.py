from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Question(BaseModel):
    """Q&A 질문 모델

    사용자들이 작성하는 질문을 관리합니다.
    카테고리별로 분류되며, 조회수와 답변 여부를 추적합니다.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="작성자",
    )
    category = models.ForeignKey(
        "gatherings.Category",
        on_delete=models.PROTECT,
        related_name="questions",
        verbose_name="카테고리",
    )
    title = models.CharField(max_length=255, verbose_name="질문 제목")
    content = models.TextField(verbose_name="질문 내용")
    view_count = models.IntegerField(default=0, verbose_name="조회수")
    is_solved = models.BooleanField(default=False, verbose_name="답변 여부")

    class Meta:
        db_table = "questions"
        verbose_name = "질문"
        verbose_name_plural = "질문"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"], name="idx_question_user"),
            models.Index(fields=["category"], name="idx_question_category"),
            models.Index(fields=["is_solved"], name="idx_question_solved"),
            models.Index(fields=["-created_at"], name="idx_question_created"),
            models.Index(fields=["-view_count"], name="idx_question_views"),
        ]

    def __str__(self):
        """질문의 문자열 표현을 반환합니다.

        Returns:
            str: "[답변여부] 제목" 형식의 문자열
        """
        status = "✓" if self.is_solved else "?"
        return f"[{status}] {self.title}"

    @property
    def answer_count(self):
        """답변 개수를 반환합니다.

        Returns:
            int: 해당 질문에 달린 답변 개수
        """
        return self.answers.count()

    def increment_views(self):
        """조회수를 1 증가시킵니다."""
        self.view_count += 1
        self.save(update_fields=["view_count"])

    def mark_as_solved(self):
        """질문을 해결됨으로 표시합니다."""
        self.is_solved = True
        self.save(update_fields=["is_solved"])

    def mark_as_unsolved(self):
        """질문을 미해결로 표시합니다."""
        self.is_solved = False
        self.save(update_fields=["is_solved"])


class Answer(BaseModel):
    """Q&A 답변 모델

    질문에 대한 답변을 관리합니다.
    관리자 또는 일반 사용자가 작성할 수 있습니다.
    """

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="질문",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="답변 작성자",
    )
    content = models.TextField(verbose_name="답변 내용")

    class Meta:
        db_table = "answers"
        verbose_name = "답변"
        verbose_name_plural = "답변"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["question", "created_at"], name="idx_answer_question_created"),
            models.Index(fields=["user"], name="idx_answer_user"),
        ]

    def __str__(self):
        """답변의 문자열 표현을 반환합니다.

        Returns:
            str: "작성자명 - 질문 제목 (답변 미리보기)" 형식의 문자열
        """
        content_preview = self.content[:30] if len(self.content) > 30 else self.content
        return f"{self.user.username} - {self.question.title} ({content_preview}...)"

    @property
    def is_author_admin(self):
        """답변 작성자가 관리자인지 확인합니다.

        Returns:
            bool: 관리자인 경우 True, 아니면 False
        """
        return self.user.is_staff or self.user.is_superuser
