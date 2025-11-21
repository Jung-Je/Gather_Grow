from rest_framework import serializers

from apps.communitys.models import Answer


class AnswerListSerializer(serializers.ModelSerializer):
    """답변 목록 조회용 Serializer

    질문에 달린 답변 목록을 조회할 때 사용합니다.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    user_profile_image = serializers.ImageField(source="user.profile_image", read_only=True)
    is_author_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = Answer
        fields = [
            "id",
            "user",
            "username",
            "user_profile_image",
            "content",
            "is_author_admin",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class AnswerDetailSerializer(serializers.ModelSerializer):
    """답변 상세 조회용 Serializer

    답변의 모든 정보를 포함합니다.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    user_profile_image = serializers.ImageField(source="user.profile_image", read_only=True)
    question_title = serializers.CharField(source="question.title", read_only=True)
    is_author_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = Answer
        fields = [
            "id",
            "question",
            "question_title",
            "user",
            "username",
            "user_profile_image",
            "content",
            "is_author_admin",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "question", "created_at", "updated_at"]


class AnswerCreateSerializer(serializers.ModelSerializer):
    """답변 생성용 Serializer"""

    class Meta:
        model = Answer
        fields = [
            "question",
            "content",
        ]

    def validate_content(self, value):
        """내용 유효성을 검증합니다.

        Args:
            value (str): 답변 내용

        Returns:
            str: 검증된 내용

        Raises:
            serializers.ValidationError: 내용이 너무 짧은 경우
        """
        if len(value.strip()) < 10:
            raise serializers.ValidationError("답변 내용은 최소 10자 이상이어야 합니다.")
        return value.strip()

    def validate_question(self, value):
        """질문 유효성을 검증합니다.

        Args:
            value: 질문 인스턴스

        Returns:
            Question: 검증된 질문 인스턴스

        Raises:
            serializers.ValidationError: 이미 해결된 질문인 경우
        """
        if value.is_solved:
            raise serializers.ValidationError("이미 해결된 질문에는 답변을 작성할 수 없습니다.")
        return value


class AnswerUpdateSerializer(serializers.ModelSerializer):
    """답변 수정용 Serializer"""

    class Meta:
        model = Answer
        fields = [
            "content",
        ]

    def validate_content(self, value):
        """내용 유효성을 검증합니다."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("답변 내용은 최소 10자 이상이어야 합니다.")
        return value.strip()
