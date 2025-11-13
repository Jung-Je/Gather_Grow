from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """사용자 모델 관리자 페이지"""

    def get_queryset(self, request):
        """어드민에서는 탈퇴한 사용자도 모두 표시합니다.

        Args:
            request (HttpRequest): HTTP 요청 객체

        Returns:
            QuerySet: 탈퇴한 사용자를 포함한 모든 사용자 QuerySet
        """
        return super().get_queryset(request).with_deleted()

    # 목록 페이지 설정
    list_display = (
        "email",
        "username",
        "role",
        "joined_type",
        "education_level",
        "location",
        "is_active",
        "is_staff",
        "is_deleted",
        "failed_login_attempts",
        "last_login",
        "created_at",
    )
    list_filter = (
        "role",
        "joined_type",
        "education_level",
        "is_active",
        "is_staff",
        "is_deleted",
        "created_at",
    )
    search_fields = ("email", "username", "location")
    ordering = ("-created_at",)
    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
        "deleted_at",
        "deletion_scheduled_at",
        "last_failed_login",
        "profile_image_preview",
    )

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("email", "username", "password")}),
        (
            "프로필",
            {
                "fields": (
                    "profile",
                    "profile_image",
                    "profile_image_preview",
                    "education_level",
                    "location",
                )
            },
        ),
        ("권한", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("가입 정보", {"fields": ("joined_type",)}),
        (
            "보안 정보",
            {
                "fields": (
                    "failed_login_attempts",
                    "last_failed_login",
                    "last_login",
                )
            },
        ),
        (
            "탈퇴 정보",
            {
                "fields": (
                    "is_deleted",
                    "deleted_at",
                    "deletion_scheduled_at",
                )
            },
        ),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 추가 페이지 설정
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "role",
                    "joined_type",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    def profile_image_preview(self, obj):
        """프로필 이미지 미리보기를 HTML로 반환합니다.

        Args:
            obj (User): 사용자 객체

        Returns:
            str: 이미지 HTML 태그 또는 "이미지 없음" 문자열
        """
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 50%;" />',
                obj.profile_image.url,
            )
        return "이미지 없음"

    profile_image_preview.short_description = "프로필 이미지 미리보기"

    # 목록 페이지 컬럼명 한글화
    def get_list_display(self, request):
        return self.list_display

    @admin.display(description="이메일")
    def email(self, obj):
        return obj.email

    @admin.display(description="사용자명")
    def username(self, obj):
        return obj.username

    @admin.display(description="역할")
    def role(self, obj):
        return obj.get_role_display()

    @admin.display(description="가입유형")
    def joined_type(self, obj):
        return obj.get_joined_type_display()

    @admin.display(description="교육수준")
    def education_level(self, obj):
        return obj.get_education_level_display() if obj.education_level else "-"

    @admin.display(description="지역")
    def location(self, obj):
        return obj.location if obj.location else "-"

    @admin.display(description="활성", boolean=True)
    def is_active(self, obj):
        return obj.is_active

    @admin.display(description="스태프", boolean=True)
    def is_staff(self, obj):
        return obj.is_staff

    @admin.display(description="탈퇴", boolean=True)
    def is_deleted(self, obj):
        return obj.is_deleted

    @admin.display(description="로그인실패")
    def failed_login_attempts(self, obj):
        return obj.failed_login_attempts

    @admin.display(description="최근로그인")
    def last_login(self, obj):
        return obj.last_login

    @admin.display(description="가입일")
    def created_at(self, obj):
        return obj.created_at
