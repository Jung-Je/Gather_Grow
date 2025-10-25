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
        """모임 가입 신청

        Args:
            user: 가입 신청자
            gathering_id: 모임 ID

        Returns:
            생성된 멤버 객체

        Raises:
            ValueError: 가입 불가 조건
        """
        try:
            gathering = Gathering.objects.select_for_update().get(id=gathering_id)

            # 이미 가입된 모임인지 확인
            if GatheringMember.objects.filter(user=user, gathering=gathering, is_active=True).exists():
                raise ValueError("이미 가입된 모임입니다.")

            # 모임장은 자신의 모임에 다시 가입할 수 없음
            if gathering.user == user:
                raise ValueError("자신이 만든 모임에는 가입 신청할 수 없습니다.")

            # 모집 중인지 확인
            if not gathering.is_recruiting:
                raise ValueError("현재 모집 중이 아닙니다.")

            # 정원 마감 확인
            if gathering.is_full:
                raise ValueError("모집 정원이 마감되었습니다.")

            # 멤버 생성
            member = GatheringMember.objects.create(
                user=user,
                gathering=gathering,
                role=GatheringMember.MemberRole.PARTICIPANT,
                status=GatheringMember.MemberStatus.PENDING,
            )

            logger.info(f"User {user.id} joined gathering {gathering_id} (pending approval)")
            return member

        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

    @staticmethod
    @transaction.atomic
    def approve_member(member_id: int, user) -> GatheringMember:
        """멤버 승인

        Args:
            member_id: 멤버 ID
            user: 승인 요청자 (모임장)

        Returns:
            승인된 멤버 객체

        Raises:
            ValueError: 승인 불가 조건
        """
        try:
            member = GatheringMember.objects.select_related("gathering").select_for_update().get(id=member_id)

            # 모임장만 승인 가능
            if member.gathering.user != user:
                raise ValueError("모임장만 멤버를 승인할 수 있습니다.")

            # 대기 중인 멤버만 처리 가능
            if member.status != GatheringMember.MemberStatus.PENDING:
                raise ValueError("대기 중인 멤버만 승인할 수 있습니다.")

            # 정원 확인
            if member.gathering.is_full:
                raise ValueError("모집 정원이 마감되어 승인할 수 없습니다.")

            # 승인 처리 (모델 메서드 사용)
            member.approve()

            logger.info(f"Member {member.id} approved in gathering {member.gathering.id}")
            return member

        except GatheringMember.DoesNotExist:
            raise ValueError("존재하지 않는 멤버입니다.")

    @staticmethod
    @transaction.atomic
    def reject_member(member_id: int, user) -> GatheringMember:
        """멤버 거절

        Args:
            member_id: 멤버 ID
            user: 거절 요청자 (모임장)

        Returns:
            거절된 멤버 객체

        Raises:
            ValueError: 거절 불가 조건
        """
        try:
            member = GatheringMember.objects.select_related("gathering").get(id=member_id)

            # 모임장만 거절 가능
            if member.gathering.user != user:
                raise ValueError("모임장만 멤버를 거절할 수 있습니다.")

            # 대기 중인 멤버만 처리 가능
            if member.status != GatheringMember.MemberStatus.PENDING:
                raise ValueError("대기 중인 멤버만 거절할 수 있습니다.")

            # 거절 처리 (모델 메서드 사용)
            member.reject()

            logger.info(f"Member {member.id} rejected in gathering {member.gathering.id}")
            return member

        except GatheringMember.DoesNotExist:
            raise ValueError("존재하지 않는 멤버입니다.")

    @staticmethod
    @transaction.atomic
    def leave_gathering(user, gathering_id: int) -> bool:
        """모임 탈퇴

        Args:
            user: 탈퇴 요청자
            gathering_id: 모임 ID

        Returns:
            탈퇴 성공 여부

        Raises:
            ValueError: 탈퇴 불가 조건
        """
        try:
            member = (
                GatheringMember.objects.select_related("gathering")
                .select_for_update()
                .get(user=user, gathering_id=gathering_id, is_active=True)
            )

            # 모임장은 탈퇴 불가
            if member.is_leader:
                raise ValueError("모임장은 탈퇴할 수 없습니다. 모임을 삭제하거나 다른 멤버에게 모임장을 위임해주세요.")

            # 승인된 멤버만 탈퇴 가능 (대기 중인 멤버는 cancel_join_request 사용)
            if not member.is_approved:
                raise ValueError("승인되지 않은 멤버는 탈퇴할 수 없습니다. 가입 신청 취소를 이용해주세요.")

            # 탈퇴 처리 (모델 메서드 사용)
            member.leave()

            logger.info(f"User {user.id} left gathering {gathering_id}")
            return True

        except GatheringMember.DoesNotExist:
            raise ValueError("가입되지 않은 모임이거나 이미 탈퇴한 상태입니다.")

    @staticmethod
    @transaction.atomic
    def cancel_join_request(user, gathering_id: int) -> bool:
        """가입 신청 취소

        Args:
            user: 취소 요청자
            gathering_id: 모임 ID

        Returns:
            취소 성공 여부

        Raises:
            ValueError: 취소 불가 조건
        """
        try:
            member = GatheringMember.objects.get(
                user=user,
                gathering_id=gathering_id,
                status=GatheringMember.MemberStatus.PENDING,
                is_active=True,
            )

            # 대기 중인 상태만 취소 가능
            member.delete()

            logger.info(f"User {user.id} cancelled join request for gathering {gathering_id}")
            return True

        except GatheringMember.DoesNotExist:
            raise ValueError("대기 중인 가입 신청이 없습니다.")

    @staticmethod
    @transaction.atomic
    def remove_member(gathering_id: int, member_id: int, user) -> bool:
        """멤버 강제 탈퇴 (모임장 권한)

        Args:
            gathering_id: 모임 ID
            member_id: 멤버 ID
            user: 요청자 (모임장)

        Returns:
            성공 여부

        Raises:
            ValueError: 강제 탈퇴 불가 조건
        """
        try:
            gathering = Gathering.objects.get(id=gathering_id)

            # 모임장만 강제 탈퇴 가능
            if gathering.user != user:
                raise ValueError("모임장만 멤버를 강제 탈퇴시킬 수 있습니다.")

            member = GatheringMember.objects.select_for_update().get(id=member_id, gathering=gathering, is_active=True)

            # 모임장 자신은 강제 탈퇴 불가
            if member.is_leader:
                raise ValueError("모임장은 강제 탈퇴할 수 없습니다.")

            # 승인된 멤버만 강제 탈퇴 가능
            if member.is_approved:
                member.leave()
            else:
                member.delete()

            logger.info(f"Member {member_id} removed from gathering {gathering_id} by leader {user.id}")
            return True

        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")
        except GatheringMember.DoesNotExist:
            raise ValueError("존재하지 않는 멤버입니다.")

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
