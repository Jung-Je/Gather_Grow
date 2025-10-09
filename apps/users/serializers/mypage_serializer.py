from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
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
            "username",
            "email",
            "role",
            "joined_type",
            "created_at",
            "updated_at",
        ]


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("현재 비밀번호가 일치하지 않습니다.")
        return value

    def validate(self, data):
        """새 비밀번호와 확인 비밀번호 일치 검증"""
        if data.get("new_password") != data.get("confirm_new_password"):
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data["new_password"])
        instance.save()
        return instance
