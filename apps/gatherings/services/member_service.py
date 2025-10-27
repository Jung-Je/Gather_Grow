import logging
from typing import List, Optional

from django.db import transaction
from django.db.models import QuerySet

from apps.gatherings.models import Gathering, GatheringMember

logger = logging.getLogger(__name__)


class MemberService:
    """모임 멤버 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    @staticmethod
    def get_gathering_members(
        gathering_id: int, status: str = None, role: str = None, is_active: bool = True
    ) -> QuerySet[GatheringMember]:
        """모임의 멤버 목록 조회

        Args:
            gathering_id: 모임 ID
            status: 멤버 상태 필터 (pending/approved/rejected)
            role: 역할 필터 (leader/participant)
            is_active: 활동 여부

        Returns:
            멤버 QuerySet
        """
        queryset = GatheringMember.objects.filter(gathering_id=gathering_id).select_related("user", "gathering")

        if status:
            queryset = queryset.filter(status=status)

        if role:
            queryset = queryset.filter(role=role)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.order_by("-joined_at")

    @staticmethod
    def get_pending_members(gathering_id: int) -> QuerySet[GatheringMember]:
        """승인 대기 중인 멤버 목록 조회

        Args:
            gathering_id: 모임 ID

        Returns:
            대기 중인 멤버 QuerySet
        """
        return GatheringMember.objects.filter(
            gathering_id=gathering_id, status=GatheringMember.MemberStatus.PENDING, is_active=True
        ).select_related("user")

    @staticmethod
    @transaction.atomic
    def join_gathering(user, gathering_id: int) -> GatheringMember:
        """모임 가입 신청 (검증은 Serializer에서 완료됨)

        Args:
            user: 가입 신청자
            gathering_id: 모임 ID

        Returns:
            생성된 멤버 객체
        """
        gathering = Gathering.objects.select_for_update().get(id=gathering_id)

        # 멤버 생성
        member = GatheringMember.objects.create(
            user=user,
            gathering=gathering,
            role=GatheringMember.MemberRole.PARTICIPANT,
            status=GatheringMember.MemberStatus.PENDING,
        )

        logger.info(f"User {user.id} joined gathering {gathering_id} (pending approval)")
        return member

    @staticmethod
    @transaction.atomic
    def approve_member(member_id: int) -> GatheringMember:
        """멤버 승인 (검증은 Serializer에서 완료됨)

        Args:
            member_id: 멤버 ID

        Returns:
            승인된 멤버 객체
        """
        member = GatheringMember.objects.select_related("gathering").select_for_update().get(id=member_id)

        # 승인 처리 (모델 메서드 사용)
        member.approve()

        logger.info(f"Member {member.id} approved in gathering {member.gathering.id}")
        return member

    @staticmethod
    @transaction.atomic
    def reject_member(member_id: int) -> GatheringMember:
        """멤버 거절 (검증은 Serializer에서 완료됨)

        Args:
            member_id: 멤버 ID

        Returns:
            거절된 멤버 객체
        """
        member = GatheringMember.objects.select_related("gathering").get(id=member_id)

        # 거절 처리 (모델 메서드 사용)
        member.reject()

        logger.info(f"Member {member.id} rejected in gathering {member.gathering.id}")
        return member

    @staticmethod
    @transaction.atomic
    def leave_gathering(user, gathering_id: int) -> GatheringMember:
        """모임 탈퇴 (검증은 Serializer에서 완료됨)

        Args:
            user: 탈퇴 요청자
            gathering_id: 모임 ID

        Returns:
            탈퇴 처리된 멤버 객체
        """
        member = (
            GatheringMember.objects.select_related("gathering")
            .select_for_update()
            .get(user=user, gathering_id=gathering_id, is_active=True)
        )

        # 탈퇴 처리 (모델 메서드 사용)
        member.leave()

        logger.info(f"User {user.id} left gathering {gathering_id}")
        return member

    @staticmethod
    @transaction.atomic
    def cancel_join_request(user, gathering_id: int) -> None:
        """가입 신청 취소 (검증은 Serializer에서 완료됨)

        Args:
            user: 취소 요청자
            gathering_id: 모임 ID
        """
        member = GatheringMember.objects.get(
            user=user,
            gathering_id=gathering_id,
            status=GatheringMember.MemberStatus.PENDING,
            is_active=True,
        )

        member.delete()

        logger.info(f"User {user.id} cancelled join request for gathering {gathering_id}")

    @staticmethod
    @transaction.atomic
    def remove_member(gathering_id: int, member_id: int) -> GatheringMember:
        """멤버 강제 탈퇴 (검증은 Serializer에서 완료됨)

        Args:
            gathering_id: 모임 ID
            member_id: 멤버 ID

        Returns:
            제거된 멤버 객체
        """
        member = GatheringMember.objects.select_for_update().get(
            id=member_id, gathering_id=gathering_id, is_active=True
        )

        # 승인된 멤버는 leave() 사용, 그 외는 delete()
        if member.is_approved:
            member.leave()
        else:
            member.delete()

        logger.info(f"Member {member_id} removed from gathering {gathering_id}")
        return member

    @staticmethod
    def check_member_status(user, gathering_id: int) -> Optional[str]:
        """사용자의 모임 참여 상태 확인

        Args:
            user: 사용자
            gathering_id: 모임 ID

        Returns:
            멤버 상태 (pending/approved/rejected/not_member)
        """
        try:
            member = GatheringMember.objects.get(user=user, gathering_id=gathering_id, is_active=True)
            return member.status
        except GatheringMember.DoesNotExist:
            return "not_member"

    @staticmethod
    def is_gathering_leader(user, gathering_id: int) -> bool:
        """사용자가 모임장인지 확인

        Args:
            user: 사용자
            gathering_id: 모임 ID

        Returns:
            모임장 여부
        """
        return GatheringMember.objects.filter(
            user=user,
            gathering_id=gathering_id,
            role=GatheringMember.MemberRole.LEADER,
            is_active=True,
        ).exists()
