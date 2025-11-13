import logging

from apps.chat.models import ChatMessage
from apps.gatherings.models import Gathering, GatheringMember

logger = logging.getLogger(__name__)


class ChatMessageService:
    """채팅 메시지 관련 비즈니스 로직"""

    @staticmethod
    def check_member_permission(gathering_id: int, user):
        """모임 멤버 권한 확인

        Args:
            gathering_id: 모임 ID
            user: 현재 사용자

        Raises:
            ValueError: 존재하지 않는 모임
            PermissionError: 모임 멤버가 아니거나 승인되지 않음
        """
        try:
            gathering = Gathering.objects.get(id=gathering_id)
        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

        # 모임장은 무조건 허용
        if gathering.user == user:
            return

        # 승인된 멤버인지 확인
        try:
            GatheringMember.objects.get(
                gathering=gathering, user=user, status=GatheringMember.MemberStatus.APPROVED, is_active=True
            )
        except GatheringMember.DoesNotExist:
            logger.warning(f"Unauthorized chat access attempt: user_id={user.id}, gathering_id={gathering_id}")
            raise PermissionError("채팅방에 접근할 권한이 없습니다. 모임에 먼저 가입해주세요.")

    @staticmethod
    def get_messages(gathering_id: int):
        """채팅 메시지 목록 조회

        Args:
            gathering_id: 모임 ID

        Returns:
            QuerySet: 채팅 메시지 목록 (최신순)
        """
        messages = (
            ChatMessage.objects.filter(gathering_id=gathering_id)
            .select_related("user", "gathering")
            .order_by("-created_at")
        )

        logger.info(f"Chat messages retrieved: gathering_id={gathering_id}, count={messages.count()}")
        return messages

    @staticmethod
    def create_message(gathering_id: int, user, message_text: str = None, image=None):
        """채팅 메시지 생성

        Args:
            gathering_id: 모임 ID
            user: 작성자
            message_text: 메시지 내용
            image: 이미지 파일

        Returns:
            ChatMessage: 생성된 메시지

        Raises:
            ValueError: 존재하지 않는 모임 또는 텍스트/이미지 모두 없음
        """
        try:
            gathering = Gathering.objects.get(id=gathering_id)
        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

        # 텍스트 또는 이미지 중 하나는 필수
        if not message_text and not image:
            raise ValueError("메시지 내용 또는 이미지 중 최소 하나는 입력해야 합니다.")

        message = ChatMessage.objects.create(gathering=gathering, user=user, message=message_text, image=image)

        logger.info(
            f"Chat message created: message_id={message.id}, gathering_id={gathering_id}, "
            f"user_id={user.id}, has_text={bool(message_text)}, has_image={bool(image)}"
        )

        return message
