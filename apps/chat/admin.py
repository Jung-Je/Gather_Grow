from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """채팅 메시지 모델 관리자 페이지"""

    # 목록 페이지 설정
    list_display = (
        "id",
        "gathering_title",
        "user_name",
        "message_preview",
        "has_image_display",
        "created_at",
    )
    list_filter = (
        "gathering",
        "created_at",
    )
    search_fields = (
        "message",
        "user__username",
        "user__email",
        "gathering__title",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("gathering", "user")}),
        ("메시지 내용", {"fields": ("message", "image")}),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 목록 페이지 컬럼명 한글화
    @admin.display(description="ID")
    def id(self, obj):
        return obj.id

    @admin.display(description="모임")
    def gathering_title(self, obj):
        return obj.gathering.title

    @admin.display(description="작성자")
    def user_name(self, obj):
        return obj.user.username

    @admin.display(description="메시지 내용")
    def message_preview(self, obj):
        if obj.message:
            return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
        return "[이미지만]"

    @admin.display(description="이미지", boolean=True)
    def has_image_display(self, obj):
        return obj.has_image

    @admin.display(description="생성일")
    def created_at(self, obj):
        return obj.created_at
