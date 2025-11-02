import logging
from datetime import date
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Count, Q, QuerySet

from apps.gatherings.models import Gathering, GatheringMember

logger = logging.getLogger(__name__)


class GatheringService:
    """모임 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    @staticmethod
    def get_gathering_list(
        gathering_type: str = None,
        category_id: int = None,
        status: str = None,
        study_type: str = None,
        target_level: str = None,
        is_recruiting: bool = None,
        search: str = None,
    ) -> QuerySet[Gathering]:
        """모임 목록 조회 (필터링 지원)

        Args:
            gathering_type: 모임 유형 (study/project)
            category_id: 카테고리 ID
            status: 모집 상태
            study_type: 진행 방식 (online/offline/mixed)
            target_level: 대상 수준
            is_recruiting: 모집 중 여부
            search: 검색어 (제목/설명)

        Returns:
            필터링된 모임 QuerySet
        """
        queryset = Gathering.objects.select_related("category", "user").all()

        if gathering_type:
            queryset = queryset.filter(type=gathering_type)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if status:
            queryset = queryset.filter(status=status)

        if study_type:
            queryset = queryset.filter(study_type=study_type)

        if target_level:
            queryset = queryset.filter(target_level=target_level)

        if is_recruiting is not None:
            if is_recruiting:
                queryset = queryset.filter(status=Gathering.GatheringStatus.RECRUITING)
            else:
                queryset = queryset.exclude(status=Gathering.GatheringStatus.RECRUITING)

        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return queryset.order_by("-created_at")

    @staticmethod
    def get_gathering_detail(gathering_id: int) -> Optional[Gathering]:
        """모임 상세 조회

        Args:
            gathering_id: 모임 ID

        Returns:
            모임 객체
        """
        try:
            return Gathering.objects.select_related("category", "user").get(id=gathering_id)
        except Gathering.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_gathering(user, data: Dict) -> Gathering:
        """모임 생성

        Args:
            user: 모임 생성자
            data: 모임 데이터

        Returns:
            생성된 모임

        Raises:
            ValueError: 유효성 검증 실패
        """
        # 작성자 설정
        data["user"] = user

        # 모임 생성
        gathering = Gathering.objects.create(**data)

        # 모임장을 자동으로 멤버에 추가
        GatheringMember.objects.create(
            user=user,
            gathering=gathering,
            role=GatheringMember.MemberRole.LEADER,
            status=GatheringMember.MemberStatus.APPROVED,
        )

        logger.info(f"Gathering created: {gathering.title} (ID: {gathering.id}) by user {user.id}")
        return gathering

    @staticmethod
    def update_gathering(gathering_id: int, user, data: Dict) -> Gathering:
        """모임 수정

        Args:
            gathering_id: 모임 ID
            user: 수정 요청자
            data: 수정할 데이터

        Returns:
            수정된 모임

        Raises:
            ValueError: 권한 없음 또는 유효성 검증 실패
        """
        try:
            gathering = Gathering.objects.get(id=gathering_id)

            # 모임장만 수정 가능
            if gathering.user != user:
                raise ValueError("모임장만 모임을 수정할 수 있습니다.")

            # 종료된 모임은 수정 불가
            if gathering.status == Gathering.GatheringStatus.FINISHED:
                raise ValueError("종료된 모임은 수정할 수 없습니다.")

            # 진행 중인 모임은 제한적 수정만 가능
            if gathering.status == Gathering.GatheringStatus.IN_PROGRESS:
                allowed_fields = {"description", "meeting_schedule", "location", "end_date"}
                if not set(data.keys()).issubset(allowed_fields):
                    raise ValueError(f"진행 중인 모임은 {', '.join(allowed_fields)}만 수정할 수 있습니다.")

            # 데이터 업데이트
            for key, value in data.items():
                setattr(gathering, key, value)

            gathering.save()

            logger.info(f"Gathering updated: {gathering.title} (ID: {gathering.id})")
            return gathering

        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

    @staticmethod
    def delete_gathering(gathering_id: int, user) -> bool:
        """모임 삭제

        Args:
            gathering_id: 모임 ID
            user: 삭제 요청자

        Returns:
            삭제 성공 여부

        Raises:
            ValueError: 권한 없음 또는 삭제 불가 상태
        """
        try:
            gathering = Gathering.objects.get(id=gathering_id)

            # 모임장만 삭제 가능
            if gathering.user != user:
                logger.warning(
                    f"Unauthorized gathering deletion attempt: user_id={user.id} tried to delete gathering_id={gathering_id} (owner: user_id={gathering.user_id})"
                )
                raise ValueError("모임장만 모임을 삭제할 수 있습니다.")

            # 진행 중이거나 종료된 모임은 삭제 불가
            if gathering.status in [Gathering.GatheringStatus.IN_PROGRESS, Gathering.GatheringStatus.FINISHED]:
                logger.warning(
                    f"Cannot delete gathering in {gathering.status} status: gathering_id={gathering_id}, user_id={user.id}"
                )
                raise ValueError("진행 중이거나 종료된 모임은 삭제할 수 없습니다.")

            # 참여 인원이 2명 이상이면 삭제 불가
            if gathering.current_members > 1:
                logger.warning(
                    f"Cannot delete gathering with members: gathering_id={gathering_id}, current_members={gathering.current_members}, user_id={user.id}"
                )
                raise ValueError("참여 인원이 있는 모임은 삭제할 수 없습니다. 먼저 멤버를 삭제해주세요.")

            # 삭제 전 정보 기록
            logger.info(
                f"Gathering deleted: gathering_id={gathering_id}, title='{gathering.title}', "
                f"type={gathering.type}, status={gathering.status}, deleted_by_user_id={user.id}"
            )

            gathering.delete()
            return True

        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

    @staticmethod
    def change_gathering_status(gathering_id: int, user, new_status: str) -> Gathering:
        """모임 상태 변경

        Args:
            gathering_id: 모임 ID
            user: 변경 요청자
            new_status: 새 상태

        Returns:
            수정된 모임

        Raises:
            ValueError: 권한 없음 또는 잘못된 상태 변경
        """
        try:
            gathering = Gathering.objects.get(id=gathering_id)

            # 모임장만 상태 변경 가능
            if gathering.user != user:
                logger.warning(
                    f"Unauthorized status change attempt: user_id={user.id} tried to change gathering_id={gathering_id} status (owner: user_id={gathering.user_id})"
                )
                raise ValueError("모임장만 모임 상태를 변경할 수 있습니다.")

            # 상태 변경 유효성 검증
            valid_transitions = {
                Gathering.GatheringStatus.RECRUITING: [
                    Gathering.GatheringStatus.RECRUITMENT_COMPLETE,
                    Gathering.GatheringStatus.IN_PROGRESS,
                ],
                Gathering.GatheringStatus.RECRUITMENT_COMPLETE: [
                    Gathering.GatheringStatus.RECRUITING,
                    Gathering.GatheringStatus.IN_PROGRESS,
                ],
                Gathering.GatheringStatus.IN_PROGRESS: [Gathering.GatheringStatus.FINISHED],
                Gathering.GatheringStatus.FINISHED: [],  # 종료 상태는 변경 불가
            }

            if new_status not in valid_transitions.get(gathering.status, []):
                logger.warning(
                    f"Invalid status transition: gathering_id={gathering_id}, from={gathering.status} to={new_status}, user_id={user.id}"
                )
                raise ValueError(f"현재 상태({gathering.get_status_display()})에서 변경할 수 없는 상태입니다.")

            old_status = gathering.status
            gathering.status = new_status
            gathering.save()

            logger.info(
                f"Gathering status changed: gathering_id={gathering_id}, title='{gathering.title}', "
                f"from={old_status} to={new_status}, changed_by_user_id={user.id}"
            )
            return gathering

        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

    @staticmethod
    def get_my_gatherings(user, role: str = None) -> QuerySet[Gathering]:
        """내가 참여한 모임 목록 조회

        Args:
            user: 사용자
            role: 역할 필터 (leader/participant)

        Returns:
            참여 중인 모임 목록
        """
        # 내가 참여 중인 모임 ID 목록
        member_queryset = GatheringMember.objects.filter(
            user=user, is_active=True, status=GatheringMember.MemberStatus.APPROVED
        )

        if role == "leader":
            member_queryset = member_queryset.filter(role=GatheringMember.MemberRole.LEADER)
        elif role == "participant":
            member_queryset = member_queryset.filter(role=GatheringMember.MemberRole.PARTICIPANT)

        gathering_ids = member_queryset.values_list("gathering_id", flat=True)

        return Gathering.objects.filter(id__in=gathering_ids).select_related("category", "user").order_by("-created_at")

    @staticmethod
    def check_recruitment_deadlines():
        """모집 마감일 자동 처리

        모집 마감일이 지난 모임을 자동으로 '모집완료' 상태로 변경합니다.
        이 메서드는 스케줄러를 통해 주기적으로 실행되어야 합니다.
        """
        today = date.today()
        expired_gatherings = Gathering.objects.filter(
            status=Gathering.GatheringStatus.RECRUITING, recruitment_end__lt=today
        )

        count = expired_gatherings.update(status=Gathering.GatheringStatus.RECRUITMENT_COMPLETE)

        if count > 0:
            logger.info(f"Updated {count} gatherings to RECRUITMENT_COMPLETE status")

        return count

    @staticmethod
    def get_gathering_statistics(gathering_id: int) -> Optional[Dict]:
        """모임 통계 조회

        Args:
            gathering_id: 모임 ID

        Returns:
            모임 통계 정보
        """
        try:
            gathering = Gathering.objects.annotate(
                total_members=Count("members", filter=Q(members__is_active=True)),
                pending_members=Count(
                    "members", filter=Q(members__status=GatheringMember.MemberStatus.PENDING, members__is_active=True)
                ),
                approved_members=Count(
                    "members",
                    filter=Q(members__status=GatheringMember.MemberStatus.APPROVED, members__is_active=True),
                ),
            ).get(id=gathering_id)

            return {
                "gathering_id": gathering.id,
                "title": gathering.title,
                "max_members": gathering.max_members,
                "current_members": gathering.current_members,
                "remaining_seats": gathering.remaining_seats,
                "total_members": gathering.total_members,
                "pending_members": gathering.pending_members,
                "approved_members": gathering.approved_members,
                "is_full": gathering.is_full,
                "is_recruiting": gathering.is_recruiting,
            }

        except Gathering.DoesNotExist:
            return None
