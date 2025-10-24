from rest_framework import serializers

from apps.gatherings.models import GatheringMember


class GatheringMemberSerializer(serializers.ModelSerializer):
    """모임 멤버 조회용 Serializer"""

    username = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    gathering_title = serializers.CharField(source="gathering.title", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_leader = serializers.BooleanField(read_only=True)
    is_approved = serializers.BooleanField(read_only=True)

    class Meta:
        model = GatheringMember
        fields = [
            "id",
            "user",
            "username",
            "user_email",
            "gathering",
            "gathering_title",
            "role",
            "role_display",
            "status",
            "status_display",
            "is_leader",
            "is_approved",
            "is_active",
            "joined_at",
            "created_at",
        ]
        read_only_fields = ["id", "role", "status", "joined_at", "created_at"]


class MemberJoinSerializer(serializers.ModelSerializer):
    """모임 가입 신청용 Serializer"""

    class Meta:
        model = GatheringMember
        fields = ["gathering"]

    def validate_gathering(self, value):
        """모임 가입 가능 여부 검증"""
        user = self.context["request"].user

        # 이미 가입된 모임인지 확인
        if GatheringMember.objects.filter(user=user, gathering=value, is_active=True).exists():
            raise serializers.ValidationError("이미 가입된 모임입니다.")

        # 모임장은 자신의 모임에 다시 가입할 수 없음
        if value.user == user:
            raise serializers.ValidationError("자신이 만든 모임에는 가입 신청할 수 없습니다.")

        # 모집 중인지 확인
        if not value.is_recruiting:
            raise serializers.ValidationError("현재 모집 중이 아닙니다.")

        # 정원 마감 확인
        if value.is_full:
            raise serializers.ValidationError("모집 정원이 마감되었습니다.")

        return value

    def create(self, validated_data):
        """모임 가입 신청"""
        user = self.context["request"].user
        validated_data["user"] = user
        validated_data["status"] = GatheringMember.MemberStatus.PENDING
        validated_data["role"] = GatheringMember.MemberRole.PARTICIPANT

        return super().create(validated_data)


class MemberApprovalSerializer(serializers.Serializer):
    """모임 멤버 승인/거절용 Serializer"""

    action = serializers.ChoiceField(choices=["approve", "reject"], required=True)

    def validate(self, attrs):
        """승인/거절 가능 여부 검증"""
        member = self.instance
        user = self.context["request"].user

        # 모임장만 승인/거절 가능
        if member.gathering.user != user:
            raise serializers.ValidationError("모임장만 멤버를 승인/거절할 수 있습니다.")

        # 대기 중인 멤버만 처리 가능
        if member.status != GatheringMember.MemberStatus.PENDING:
            raise serializers.ValidationError("대기 중인 멤버만 승인/거절할 수 있습니다.")

        # 승인 시 정원 확인
        if attrs["action"] == "approve" and member.gathering.is_full:
            raise serializers.ValidationError("모집 정원이 마감되어 승인할 수 없습니다.")

        return attrs

    def save(self, **kwargs):
        """승인/거절 처리"""
        member = self.instance
        action = self.validated_data["action"]

        if action == "approve":
            member.approve()
        elif action == "reject":
            member.reject()

        return member
