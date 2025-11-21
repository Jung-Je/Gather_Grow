from rest_framework import serializers

from apps.communitys.models import Question
from apps.gatherings.serializers.category_serializer import CategoryListSerializer


class QuestionListSerializer(serializers.ModelSerializer):
    """질문 목록 조회용 Serializer

    목록에서는 간단한 정보만 표시합니다.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    answer_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "user",
            "username",
            "category",
            "category_name",
            "title",
            "view_count",
            "is_solved",
            "answer_count",
            "created_at",
        ]
        read_only_fields = ["id", "user", "view_count", "is_solved", "created_at"]


class QuestionDetailSerializer(serializers.ModelSerializer):
    """질문 상세 조회용 Serializer

    모든 정보를 포함합니다.
    """

    category = CategoryListSerializer(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    answer_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "user",
            "username",
            "category",
            "title",
            "content",
            "view_count",
            "is_solved",
            "answer_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "view_count", "is_solved", "created_at", "updated_at"]


class QuestionCreateSerializer(serializers.ModelSerializer):
    """질문 생성용 Serializer"""

    class Meta:
        model = Question
        fields = [
            "category",
            "title",
            "content",
        ]

    def validate_title(self, value):
        """제목 유효성을 검증합니다.

        Args:
            value (str): 질문 제목

        Returns:
            str: 검증된 제목

        Raises:
            serializers.ValidationError: 제목이 너무 짧거나 긴 경우
        """
        if len(value.strip()) < 5:
            raise serializers.ValidationError("제목은 최소 5자 이상이어야 합니다.")
        if len(value) > 255:
            raise serializers.ValidationError("제목은 최대 255자까지 가능합니다.")
        return value.strip()

    def validate_content(self, value):
        """내용 유효성을 검증합니다.

        Args:
            value (str): 질문 내용

        Returns:
            str: 검증된 내용

        Raises:
            serializers.ValidationError: 내용이 너무 짧은 경우
        """
        if len(value.strip()) < 10:
            raise serializers.ValidationError("내용은 최소 10자 이상이어야 합니다.")
        return value.strip()


class QuestionUpdateSerializer(serializers.ModelSerializer):
    """질문 수정용 Serializer"""

    class Meta:
        model = Question
        fields = [
            "category",
            "title",
            "content",
        ]

    def validate_title(self, value):
        """제목 유효성을 검증합니다."""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("제목은 최소 5자 이상이어야 합니다.")
        if len(value) > 255:
            raise serializers.ValidationError("제목은 최대 255자까지 가능합니다.")
        return value.strip()

    def validate_content(self, value):
        """내용 유효성을 검증합니다."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("내용은 최소 10자 이상이어야 합니다.")
        return value.strip()

    def validate(self, attrs):
        """답변이 달린 질문은 수정 제한"""
        instance = self.instance

        # 답변이 이미 달린 질문은 수정 불가
        if instance.answer_count > 0:
            raise serializers.ValidationError("답변이 달린 질문은 수정할 수 없습니다.")

        return attrs
