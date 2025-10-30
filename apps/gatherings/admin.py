from django.contrib import admin

from .models import Category, Gathering, GatheringMember


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """카테고리 모델 관리자 페이지"""

    # 목록 페이지 설정
    list_display = (
        "id",
        "name",
        "parent",
        "description_short",
        "is_active",
        "depth_display",
        "created_at",
    )
    list_filter = ("is_active", "parent", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("name", "parent", "description")}),
        ("활성화", {"fields": ("is_active",)}),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 목록 페이지 컬럼명 한글화
    @admin.display(description="ID")
    def id(self, obj):
        return obj.id

    @admin.display(description="카테고리명")
    def name(self, obj):
        return obj.name

    @admin.display(description="부모 카테고리")
    def parent(self, obj):
        return obj.parent.name if obj.parent else "-"

    @admin.display(description="설명 (요약)")
    def description_short(self, obj):
        if obj.description:
            return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
        return "-"

    @admin.display(description="활성화", boolean=True)
    def is_active(self, obj):
        return obj.is_active

    @admin.display(description="깊이")
    def depth_display(self, obj):
        return f"Lv.{obj.depth}"

    @admin.display(description="생성일")
    def created_at(self, obj):
        return obj.created_at


@admin.register(Gathering)
class GatheringAdmin(admin.ModelAdmin):
    """모임 모델 관리자 페이지"""

    # 목록 페이지 설정
    list_display = (
        "id",
        "title",
        "user",
        "category",
        "type",
        "status",
        "current_members",
        "max_members",
        "study_type",
        "target_level",
        "has_cost",
        "recruitment_end",
        "start_date",
        "created_at",
    )
    list_filter = (
        "type",
        "status",
        "study_type",
        "target_level",
        "has_cost",
        "category",
        "created_at",
    )
    search_fields = ("title", "description", "user__username", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("current_members", "created_at", "updated_at")
    date_hierarchy = "start_date"

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("user", "category", "type", "title", "description")}),
        (
            "모집 정보",
            {
                "fields": (
                    "max_members",
                    "current_members",
                    "recruitment_end",
                )
            },
        ),
        (
            "일정 정보",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "meeting_schedule",
                )
            },
        ),
        (
            "진행 방식",
            {
                "fields": (
                    "study_type",
                    "location",
                    "target_level",
                )
            },
        ),
        ("참가비", {"fields": ("has_cost", "cost_description")}),
        ("상태", {"fields": ("status",)}),
        ("프로젝트 정보", {"fields": ("required_skills", "project_goal")}),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 목록 페이지 컬럼명 한글화
    @admin.display(description="ID")
    def id(self, obj):
        return obj.id

    @admin.display(description="제목")
    def title(self, obj):
        return obj.title

    @admin.display(description="작성자")
    def user(self, obj):
        return obj.user.username

    @admin.display(description="카테고리")
    def category(self, obj):
        return obj.category.name

    @admin.display(description="유형")
    def type(self, obj):
        return obj.get_type_display()

    @admin.display(description="상태")
    def status(self, obj):
        return obj.get_status_display()

    @admin.display(description="현재인원")
    def current_members(self, obj):
        return f"{obj.current_members}명"

    @admin.display(description="모집인원")
    def max_members(self, obj):
        return f"{obj.max_members}명"

    @admin.display(description="진행방식")
    def study_type(self, obj):
        return obj.get_study_type_display()

    @admin.display(description="대상수준")
    def target_level(self, obj):
        return obj.get_target_level_display()

    @admin.display(description="참가비", boolean=True)
    def has_cost(self, obj):
        return obj.has_cost

    @admin.display(description="모집마감일")
    def recruitment_end(self, obj):
        return obj.recruitment_end

    @admin.display(description="시작일")
    def start_date(self, obj):
        return obj.start_date

    @admin.display(description="생성일")
    def created_at(self, obj):
        return obj.created_at


@admin.register(GatheringMember)
class GatheringMemberAdmin(admin.ModelAdmin):
    """모임 멤버 모델 관리자 페이지"""

    # 목록 페이지 설정
    list_display = (
        "id",
        "user",
        "gathering_title",
        "role",
        "status",
        "is_active",
        "joined_at",
        "created_at",
    )
    list_filter = (
        "role",
        "status",
        "is_active",
        "joined_at",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "gathering__title",
    )
    ordering = ("-joined_at",)
    readonly_fields = ("joined_at", "created_at", "updated_at")
    date_hierarchy = "joined_at"

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("user", "gathering", "role")}),
        ("상태", {"fields": ("status", "is_active")}),
        ("참여 일시", {"fields": ("joined_at",)}),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 목록 페이지 컬럼명 한글화
    @admin.display(description="ID")
    def id(self, obj):
        return obj.id

    @admin.display(description="사용자")
    def user(self, obj):
        return obj.user.username

    @admin.display(description="모임")
    def gathering_title(self, obj):
        return obj.gathering.title

    @admin.display(description="역할")
    def role(self, obj):
        return obj.get_role_display()

    @admin.display(description="상태")
    def status(self, obj):
        return obj.get_status_display()

    @admin.display(description="활동중", boolean=True)
    def is_active(self, obj):
        return obj.is_active

    @admin.display(description="참여일")
    def joined_at(self, obj):
        return obj.joined_at

    @admin.display(description="생성일")
    def created_at(self, obj):
        return obj.created_at
