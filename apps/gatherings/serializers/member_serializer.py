from rest_framework import serializers

from apps.gatherings.models import GatheringMember


class GatheringMemberSerializer(serializers.ModelSerializer):
    """모임 멤버 조회용 Serializer (개인정보 보호: 이메일 제외)"""

    username = serializers.CharField(source="user.username", read_only=True)
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


class MemberJoinSerializer(serializers.Serializer):
    """모임 가입 신청용 Serializer"""

    gathering = serializers.IntegerField(required=True)

    def validate_gathering(self, value):
        """모임 가입 가능 여부를 검증합니다.

        Args:
            value (int): 모임 ID

        Returns:
            int: 검증된 모임 ID

        Raises:
            serializers.ValidationError: 모임이 존재하지 않거나 가입 불가능한 경우
        """
        from apps.gatherings.models import Gathering

        user = self.context["request"].user

        # 모임 존재 확인
        try:
            gathering = Gathering.objects.get(id=value)
        except Gathering.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 모임입니다.")

        # 이미 가입된 모임인지 확인
        if GatheringMember.objects.filter(user=user, gathering=gathering, is_active=True).exists():
            raise serializers.ValidationError("이미 가입된 모임입니다.")

        # 모임장은 자신의 모임에 다시 가입할 수 없음
        if gathering.user == user:
            raise serializers.ValidationError("자신이 만든 모임에는 가입 신청할 수 없습니다.")

        # 모집 중인지 확인
        if not gathering.is_recruiting:
            raise serializers.ValidationError("현재 모집 중이 아닙니다.")

        # 정원 마감 확인
        if gathering.is_full:
            raise serializers.ValidationError("모집 정원이 마감되었습니다.")

        return value


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

        # 정원 체크는 Service layer에서 수행 (race condition 방지)

        return attrs


class MemberLeaveSerializer(serializers.Serializer):
    """모임 탈퇴용 Serializer"""

    gathering = serializers.IntegerField(required=True)

    def validate_gathering(self, value):
        """탈퇴 가능 여부 검증"""
        user = self.context["request"].user

        # 가입된 멤버인지 확인
        try:
            member = GatheringMember.objects.get(user=user, gathering_id=value, is_active=True)
        except GatheringMember.DoesNotExist:
            raise serializers.ValidationError("가입되지 않은 모임이거나 이미 탈퇴한 상태입니다.")

        # 모임장은 탈퇴 불가
        if member.is_leader:
            raise serializers.ValidationError(
                "모임장은 탈퇴할 수 없습니다. 모임을 삭제하거나 다른 멤버에게 모임장을 위임해주세요."
            )

        # 승인된 멤버만 탈퇴 가능
        if not member.is_approved:
            raise serializers.ValidationError("승인되지 않은 멤버는 탈퇴할 수 없습니다. 가입 신청 취소를 이용해주세요.")

        return value


class MemberCancelSerializer(serializers.Serializer):
    """가입 신청 취소용 Serializer"""

    gathering = serializers.IntegerField(required=True)

    def validate_gathering(self, value):
        """취소 가능 여부 검증"""
        user = self.context["request"].user

        # 대기 중인 가입 신청이 있는지 확인
        try:
            GatheringMember.objects.get(
                user=user, gathering_id=value, status=GatheringMember.MemberStatus.PENDING, is_active=True
            )
        except GatheringMember.DoesNotExist:
            raise serializers.ValidationError("대기 중인 가입 신청이 없습니다.")

        return value


class MemberRemoveSerializer(serializers.Serializer):
    """멤버 강제 탈퇴용 Serializer (모임장 전용)"""

    gathering = serializers.IntegerField(required=True)
    member = serializers.IntegerField(required=True)

    def validate(self, attrs):
        """강제 탈퇴 가능 여부 검증"""
        user = self.context["request"].user
        gathering_id = attrs["gathering"]
        member_id = attrs["member"]

        # 모임 존재 확인
        try:
            from apps.gatherings.models import Gathering

            gathering = Gathering.objects.get(id=gathering_id)
        except Gathering.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 모임입니다.")

        # 모임장인지 확인
        if gathering.user != user:
            raise serializers.ValidationError("모임장만 멤버를 강제 탈퇴시킬 수 있습니다.")

        # 멤버 존재 확인
        try:
            member = GatheringMember.objects.get(id=member_id, gathering=gathering, is_active=True)
        except GatheringMember.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 멤버입니다.")

        # 모임장 자신은 강제 탈퇴 불가
        if member.is_leader:
            raise serializers.ValidationError("모임장은 강제 탈퇴할 수 없습니다.")

        return attrs


class LeaderTransferSerializer(serializers.Serializer):
    """리더 위임용 Serializer"""

    new_leader_id = serializers.IntegerField(required=True)

    def validate_new_leader_id(self, value):
        """새 리더 유효성 검증

        Args:
            value (int): 새 리더의 user ID

        Returns:
            int: 검증된 user ID

        Raises:
            serializers.ValidationError: 유효하지 않은 새 리더인 경우
        """
        user = self.context["request"].user
        gathering_id = self.context.get("gathering_id")

        # 모임 존재 확인
        try:
            from apps.gatherings.models import Gathering

            gathering = Gathering.objects.get(id=gathering_id)
        except Gathering.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 모임입니다.")

        # 현재 사용자가 모임장인지 확인
        if gathering.user.id != user.id:
            raise serializers.ValidationError("모임장만 리더를 위임할 수 있습니다.")

        # 자기 자신에게는 위임 불가
        if value == user.id:
            raise serializers.ValidationError("자기 자신에게는 리더를 위임할 수 없습니다.")

        # 새 리더가 승인된 멤버인지 확인
        try:
            new_leader_member = GatheringMember.objects.get(
                user_id=value, gathering_id=gathering_id, status=GatheringMember.MemberStatus.APPROVED, is_active=True
            )
        except GatheringMember.DoesNotExist:
            raise serializers.ValidationError("새 리더는 승인된 멤버여야 합니다.")

        return value
