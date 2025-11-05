from rest_framework import serializers

from apps.chat.models import ChatMessage


class ChatMessageListSerializer(serializers.ModelSerializer):
    """채팅 메시지 목록 조회용 Serializer

    채팅방 메시지 목록을 조회할 때 사용합니다.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    user_profile_image = serializers.ImageField(source="user.profile_image", read_only=True)
    has_image = serializers.BooleanField(read_only=True)
    has_text = serializers.BooleanField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "user",
            "username",
            "user_profile_image",
            "message",
            "image",
            "has_image",
            "has_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """채팅 메시지 생성용 Serializer

    텍스트 메시지와 이미지를 함께 보낼 수 있습니다.
    """

    class Meta:
        model = ChatMessage
        fields = [
            "gathering",
            "message",
            "image",
        ]

    def validate(self, attrs):
        """메시지 또는 이미지 중 최소 하나는 필수"""
        message = attrs.get("message")
        image = attrs.get("image")

        if not message and not image:
            raise serializers.ValidationError("메시지 내용 또는 이미지 중 최소 하나는 입력해야 합니다.")

        return attrs


class ChatMessageDetailSerializer(serializers.ModelSerializer):
    """채팅 메시지 상세 조회용 Serializer

    메시지의 모든 정보를 포함합니다.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    user_profile_image = serializers.ImageField(source="user.profile_image", read_only=True)
    gathering_title = serializers.CharField(source="gathering.title", read_only=True)
    has_image = serializers.BooleanField(read_only=True)
    has_text = serializers.BooleanField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "gathering",
            "gathering_title",
            "user",
            "username",
            "user_profile_image",
            "message",
            "image",
            "has_image",
            "has_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "gathering", "created_at", "updated_at"]
