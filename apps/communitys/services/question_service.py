import logging
from typing import Optional

from django.db.models import Count

from apps.communitys.models import Question

logger = logging.getLogger(__name__)


class QuestionService:
    """질문 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    @staticmethod
    def check_question_permission(question: Question, user) -> None:
        """질문 작성자 권한 확인

        Args:
            question: 질문 객체
            user: 현재 사용자

        Raises:
            PermissionError: 작성자가 아닌 경우
        """
        if question.user != user:
            logger.warning(
                f"Unauthorized question access attempt: user_id={user.id} tried to access question_id={question.id} (owner: user_id={question.user_id})"
            )
            raise PermissionError("질문 작성자만 수정/삭제할 수 있습니다.")

    @staticmethod
    def can_modify_question(question: Question) -> bool:
        """질문 수정/삭제 가능 여부 확인

        Args:
            question: 질문 객체

        Returns:
            bool: 수정/삭제 가능 여부
        """
        # 답변이 달린 질문은 수정/삭제 불가
        # annotate된 answer_count가 있으면 사용, 없으면 직접 카운트
        if hasattr(question, "answer_count"):
            return question.answer_count == 0
        return question.answers.count() == 0

    @staticmethod
    def get_question_with_validation(question_id: int) -> Optional[Question]:
        """질문 조회 및 존재 여부 검증 (answer_count 포함)

        Args:
            question_id: 질문 ID

        Returns:
            Optional[Question]: 질문 객체 또는 None
        """
        try:
            return (
                Question.objects.select_related("category", "user")
                .annotate(answer_count=Count("answers"))
                .get(id=question_id)
            )
        except Question.DoesNotExist:
            logger.warning(f"Question not found: question_id={question_id}")
            return None
