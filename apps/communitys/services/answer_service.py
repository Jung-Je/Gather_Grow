import logging
from typing import Optional

from apps.communitys.models import Answer, Question

logger = logging.getLogger(__name__)


class AnswerService:
    """답변 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    @staticmethod
    def check_answer_permission(answer: Answer, user, allow_question_author: bool = False) -> None:
        """답변 작성자 권한 확인

        Args:
            answer: 답변 객체
            user: 현재 사용자
            allow_question_author: 질문 작성자도 허용할지 여부 (삭제 시 True)

        Raises:
            PermissionError: 작성자가 아닌 경우
        """
        is_answer_author = answer.user == user
        is_question_author = allow_question_author and answer.question.user == user

        if not (is_answer_author or is_question_author):
            logger.warning(
                f"Unauthorized answer access attempt: user_id={user.id} tried to access answer_id={answer.id} (owner: user_id={answer.user_id})"
            )
            raise PermissionError("답변 작성자만 수정/삭제할 수 있습니다.")

    @staticmethod
    def can_answer_question(question: Question) -> tuple[bool, str]:
        """질문에 답변 가능 여부 확인

        Args:
            question: 질문 객체

        Returns:
            tuple[bool, str]: (가능 여부, 불가 사유)
        """
        if question.is_solved:
            return False, "이미 해결된 질문에는 답변을 작성할 수 없습니다."
        return True, ""

    @staticmethod
    def get_answer_with_validation(answer_id: int) -> Optional[Answer]:
        """답변 조회 및 존재 여부 검증

        Args:
            answer_id: 답변 ID

        Returns:
            Optional[Answer]: 답변 객체 또는 None
        """
        try:
            return Answer.objects.select_related("question", "user").get(id=answer_id)
        except Answer.DoesNotExist:
            logger.warning(f"Answer not found: answer_id={answer_id}")
            return None
