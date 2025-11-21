from django.contrib import admin

from .models import Answer, Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """질문 모델 관리자 페이지"""

    # 목록 페이지 설정
    list_display = (
        "id",
        "title",
        "user",
        "category",
        "is_solved",
        "view_count",
        "answer_count_display",
        "created_at",
    )
    list_filter = ("is_solved", "category", "created_at")
    search_fields = ("title", "content", "user__username", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("view_count", "created_at", "updated_at")
    date_hierarchy = "created_at"

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("user", "category", "title", "content")}),
        ("상태", {"fields": ("is_solved", "view_count")}),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 목록 페이지 컬럼명 한글화
    @admin.display(description="ID")
    def id(self, obj):
        return obj.id

    @admin.display(description="질문 제목")
    def title(self, obj):
        return obj.title

    @admin.display(description="작성자")
    def user(self, obj):
        return obj.user.username

    @admin.display(description="카테고리")
    def category(self, obj):
        return obj.category.name

    @admin.display(description="답변 여부", boolean=True)
    def is_solved(self, obj):
        return obj.is_solved

    @admin.display(description="조회수")
    def view_count(self, obj):
        return f"{obj.view_count}회"

    @admin.display(description="답변 개수")
    def answer_count_display(self, obj):
        return f"{obj.answer_count}개"

    @admin.display(description="생성일")
    def created_at(self, obj):
        return obj.created_at


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """답변 모델 관리자 페이지"""

    # 목록 페이지 설정
    list_display = (
        "id",
        "question_title",
        "user",
        "content_short",
        "is_author_admin_display",
        "created_at",
    )
    list_filter = ("user__is_staff", "created_at")
    search_fields = (
        "content",
        "user__username",
        "user__email",
        "question__title",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    # 상세 페이지 설정
    fieldsets = (
        ("기본 정보", {"fields": ("question", "user", "content")}),
        ("생성/수정 일시", {"fields": ("created_at", "updated_at")}),
    )

    # 목록 페이지 컬럼명 한글화
    @admin.display(description="ID")
    def id(self, obj):
        return obj.id

    @admin.display(description="질문")
    def question_title(self, obj):
        return obj.question.title

    @admin.display(description="답변 작성자")
    def user(self, obj):
        return obj.user.username

    @admin.display(description="답변 내용 (요약)")
    def content_short(self, obj):
        if obj.content:
            return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        return "-"

    @admin.display(description="관리자 답변", boolean=True)
    def is_author_admin_display(self, obj):
        return obj.is_author_admin

    @admin.display(description="생성일")
    def created_at(self, obj):
        return obj.created_at
