from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    """사용자 프로필 Serializer

    사용자 프로필 정보를 조회하고 수정합니다.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "profile",
            "profile_image",
            "education_level",
            "location",
            "role",
            "joined_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "joined_type",
            "created_at",
            "updated_at",
        ]

    def validate_username(self, value):
        """사용자명 유효성을 검증합니다.

        Args:
            value (str): 검증할 사용자명

        Returns:
            str: 검증된 사용자명 (공백 제거)

        Raises:
            serializers.ValidationError: 사용자명이 비어있거나 20자를 초과하는 경우
        """
        # 공백 체크
        if not value or not value.strip():
            raise serializers.ValidationError("사용자 이름은 필수입니다.")

        # 길이 체크
        if len(value) > 20:
            raise serializers.ValidationError("사용자 이름은 20자 이하여야 합니다.")

        return value.strip()


class PasswordChangeSerializer(serializers.Serializer):
    """비밀번호 변경 Serializer

    현재 비밀번호를 확인하고 새 비밀번호로 변경합니다.
    """

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        """현재 비밀번호가 올바른지 검증합니다.

        Args:
            value (str): 검증할 현재 비밀번호

        Returns:
            str: 검증된 현재 비밀번호

        Raises:
            serializers.ValidationError: 현재 비밀번호가 일치하지 않는 경우
        """
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("현재 비밀번호가 일치하지 않습니다.")
        return value

    def validate(self, data):
        """새 비밀번호와 확인 비밀번호가 일치하는지 검증합니다.

        Args:
            data (dict): 검증할 데이터

        Returns:
            dict: 검증된 데이터

        Raises:
            serializers.ValidationError: 새 비밀번호가 일치하지 않는 경우
        """
        if data.get("new_password") != data.get("confirm_new_password"):
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        return data

    def update(self, instance, validated_data):
        """새 비밀번호로 업데이트합니다.

        Args:
            instance (User): 업데이트할 사용자 객체
            validated_data (dict): 검증된 데이터

        Returns:
            User: 비밀번호가 변경된 사용자 객체
        """
        instance.set_password(validated_data["new_password"])
        instance.save()
        return instance
