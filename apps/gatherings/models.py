from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Category(BaseModel):
    """카테고리 모델 (계층 구조 지원)

    스터디/프로젝트 및 Q&A의 카테고리를 관리합니다.
    대분류/소분류 구조를 위해 자기 참조 관계를 가집니다.
    """

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="부모 카테고리",
    )
    name = models.CharField(max_length=100, verbose_name="카테고리명")
    description = models.TextField(blank=True, null=True, verbose_name="카테고리 설명")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")

    class Meta:
        db_table = "categories"
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["parent"], name="idx_category_parent"),
            models.Index(fields=["is_active"], name="idx_category_active"),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_parent(self):
        """대분류(부모) 카테고리 여부"""
        return self.parent is None

    @property
    def depth(self):
        """카테고리 깊이"""
        if self.parent is None:
            return 0
        return 1 + self.parent.depth


class Gathering(BaseModel):
    """모임(스터디/프로젝트) 모델"""

    class GatheringType(models.TextChoices):
        STUDY = "study", "스터디"
        PROJECT = "project", "프로젝트"

    class StudyType(models.TextChoices):
        ONLINE = "online", "온라인"
        OFFLINE = "offline", "오프라인"
        MIXED = "mixed", "혼합"

    class TargetLevel(models.TextChoices):
        BEGINNER = "beginner", "초급자"
        INTERMEDIATE = "intermediate", "중급자"
        ADVANCED = "advanced", "고급자"
        ALL = "all", "누구나"

    class GatheringStatus(models.TextChoices):
        RECRUITING = "recruiting", "모집중"
        RECRUITMENT_COMPLETE = "recruitment_complete", "모집완료"
        IN_PROGRESS = "in_progress", "진행중"
        FINISHED = "finished", "종료"

    # 기본 정보
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_gatherings",
        verbose_name="작성자",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="gatherings",
        verbose_name="카테고리",
    )
    type = models.CharField(
        max_length=20,
        choices=GatheringType.choices,
        verbose_name="모임 유형",
    )
    title = models.CharField(max_length=255, verbose_name="제목")
    description = models.TextField(verbose_name="상세 설명")

    # 모집 정보
    max_members = models.IntegerField(verbose_name="모집 인원")
    current_members = models.IntegerField(default=1, verbose_name="현재 참여 인원")
    recruitment_end = models.DateField(verbose_name="모집 마감일")

    # 일정 정보
    start_date = models.DateField(verbose_name="시작일")
    end_date = models.DateField(null=True, blank=True, verbose_name="종료일")
    meeting_schedule = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="모임 일정",
    )

    # 진행 방식
    study_type = models.CharField(
        max_length=20,
        choices=StudyType.choices,
        verbose_name="진행 방식",
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="모임 장소",
    )
    target_level = models.CharField(
        max_length=20,
        choices=TargetLevel.choices,
        verbose_name="대상 수준",
    )

    # 참가비
    has_cost = models.BooleanField(default=False, verbose_name="참가비 여부")
    cost_description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="참가비 설명",
    )

    # 상태
    status = models.CharField(
        max_length=30,
        choices=GatheringStatus.choices,
        default=GatheringStatus.RECRUITING,
        verbose_name="모집 상태",
    )

    # 프로젝트 전용 필드
    required_skills = models.TextField(
        blank=True,
        null=True,
        verbose_name="필요 기술 스택",
    )
    project_goal = models.TextField(
        blank=True,
        null=True,
        verbose_name="프로젝트 목표",
    )

    class Meta:
        db_table = "gatherings"
        verbose_name = "모임"
        verbose_name_plural = "모임"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"], name="idx_gathering_user"),
            models.Index(fields=["category"], name="idx_gathering_category"),
            models.Index(fields=["type"], name="idx_gathering_type"),
            models.Index(fields=["status"], name="idx_gathering_status"),
            models.Index(fields=["recruitment_end"], name="idx_gathering_recruit_end"),
            models.Index(fields=["start_date"], name="idx_gathering_start_date"),
            models.Index(fields=["-created_at"], name="idx_gathering_created"),
        ]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title}"

    @property
    def is_recruiting(self):
        """모집 중 여부"""
        return self.status == self.GatheringStatus.RECRUITING

    @property
    def is_full(self):
        """정원 마감 여부"""
        return self.current_members >= self.max_members

    @property
    def remaining_seats(self):
        """남은 자리 수"""
        return max(0, self.max_members - self.current_members)

    def increment_members(self):
        """참여 인원 증가"""
        self.current_members += 1
        if self.is_full:
            self.status = self.GatheringStatus.RECRUITMENT_COMPLETE
        self.save(update_fields=["current_members", "status"])

    def decrement_members(self):
        """참여 인원 감소"""
        if self.current_members > 0:
            self.current_members -= 1
            if self.status == self.GatheringStatus.RECRUITMENT_COMPLETE:
                self.status = self.GatheringStatus.RECRUITING
            self.save(update_fields=["current_members", "status"])


class GatheringMember(BaseModel):
    """모임 멤버 모델"""

    class MemberRole(models.TextChoices):
        LEADER = "leader", "모임장"
        PARTICIPANT = "participant", "참여자"

    class MemberStatus(models.TextChoices):
        PENDING = "pending", "대기중"
        APPROVED = "approved", "승인됨"
        REJECTED = "rejected", "거절됨"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gathering_memberships",
        verbose_name="사용자",
    )
    gathering = models.ForeignKey(
        Gathering,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="모임",
    )
    role = models.CharField(
        max_length=20,
        choices=MemberRole.choices,
        default=MemberRole.PARTICIPANT,
        verbose_name="역할",
    )
    status = models.CharField(
        max_length=20,
        choices=MemberStatus.choices,
        default=MemberStatus.PENDING,
        verbose_name="참여 상태",
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="참여일")
    is_active = models.BooleanField(default=True, verbose_name="활동 여부")

    class Meta:
        db_table = "gathering_members"
        verbose_name = "모임 멤버"
        verbose_name_plural = "모임 멤버"
        ordering = ["-joined_at"]
        unique_together = [["user", "gathering"]]
        indexes = [
            models.Index(fields=["user"], name="idx_member_user"),
            models.Index(fields=["gathering"], name="idx_member_gathering"),
            models.Index(fields=["status"], name="idx_member_status"),
            models.Index(fields=["is_active"], name="idx_member_active"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.gathering.title} ({self.get_role_display()})"

    @property
    def is_leader(self):
        """모임장 여부"""
        return self.role == self.MemberRole.LEADER

    @property
    def is_approved(self):
        """승인된 멤버 여부"""
        return self.status == self.MemberStatus.APPROVED

    def approve(self):
        """멤버 승인"""
        if self.status == self.MemberStatus.PENDING:
            self.status = self.MemberStatus.APPROVED
            self.save(update_fields=["status"])
            self.gathering.increment_members()

    def reject(self):
        """멤버 거절"""
        if self.status == self.MemberStatus.PENDING:
            self.status = self.MemberStatus.REJECTED
            self.save(update_fields=["status"])

    def leave(self):
        """모임 탈퇴"""
        if self.is_approved:
            self.is_active = False
            self.save(update_fields=["is_active"])
            self.gathering.decrement_members()
