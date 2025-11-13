from rest_framework import serializers

from apps.gatherings.models import Gathering
from apps.gatherings.serializers.category_serializer import CategoryListSerializer


class GatheringListSerializer(serializers.ModelSerializer):
    """모임 목록 조회용 Serializer

    목록에서는 간단한 정보만 표시합니다.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_recruiting = serializers.BooleanField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    remaining_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Gathering
        fields = [
            "id",
            "user",
            "username",
            "category",
            "category_name",
            "type",
            "type_display",
            "title",
            "max_members",
            "current_members",
            "remaining_seats",
            "recruitment_end",
            "start_date",
            "study_type",
            "status",
            "status_display",
            "is_recruiting",
            "is_full",
            "created_at",
        ]


class GatheringDetailSerializer(serializers.ModelSerializer):
    """모임 상세 조회용 Serializer

    모든 정보를 포함합니다.
    """

    category = CategoryListSerializer(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    study_type_display = serializers.CharField(source="get_study_type_display", read_only=True)
    target_level_display = serializers.CharField(source="get_target_level_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_recruiting = serializers.BooleanField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    remaining_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Gathering
        fields = [
            "id",
            "user",
            "username",
            "category",
            "type",
            "type_display",
            "title",
            "description",
            "max_members",
            "current_members",
            "remaining_seats",
            "recruitment_end",
            "start_date",
            "end_date",
            "meeting_schedule",
            "study_type",
            "study_type_display",
            "location",
            "target_level",
            "target_level_display",
            "has_cost",
            "cost_description",
            "status",
            "status_display",
            "required_skills",
            "project_goal",
            "is_recruiting",
            "is_full",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "current_members", "status", "created_at", "updated_at"]


class GatheringCreateSerializer(serializers.ModelSerializer):
    """모임 생성용 Serializer"""

    class Meta:
        model = Gathering
        fields = [
            "category",
            "type",
            "title",
            "description",
            "max_members",
            "recruitment_end",
            "start_date",
            "end_date",
            "meeting_schedule",
            "study_type",
            "location",
            "target_level",
            "has_cost",
            "cost_description",
            "required_skills",
            "project_goal",
        ]

    def validate(self, attrs):
        """모임 유형과 진행 방식에 따른 필수 필드를 검증합니다.

        Args:
            attrs (dict): 검증할 데이터

        Returns:
            dict: 검증된 데이터

        Raises:
            serializers.ValidationError: 필수 필드 누락 또는 날짜 유효성 오류
        """
        gathering_type = attrs.get("type")

        # 프로젝트인 경우 필수 기술 스택 필수
        if gathering_type == Gathering.GatheringType.PROJECT:
            if not attrs.get("required_skills"):
                raise serializers.ValidationError({"required_skills": "프로젝트는 필요 기술 스택을 입력해야 합니다."})

        # 오프라인/혼합인 경우 장소 필수
        study_type = attrs.get("study_type")
        if study_type in [Gathering.StudyType.OFFLINE, Gathering.StudyType.MIXED]:
            if not attrs.get("location"):
                raise serializers.ValidationError({"location": "오프라인 또는 혼합 모임은 장소를 입력해야 합니다."})

        # 시작일이 모집 마감일보다 이후여야 함
        if attrs.get("start_date") and attrs.get("recruitment_end"):
            if attrs["start_date"] <= attrs["recruitment_end"]:
                raise serializers.ValidationError({"start_date": "시작일은 모집 마감일보다 이후여야 합니다."})

        # 종료일이 시작일보다 이후여야 함
        if attrs.get("end_date") and attrs.get("start_date"):
            if attrs["end_date"] <= attrs["start_date"]:
                raise serializers.ValidationError({"end_date": "종료일은 시작일보다 이후여야 합니다."})

        # 참가비 설명은 has_cost가 True일 때만
        if attrs.get("has_cost") and not attrs.get("cost_description"):
            raise serializers.ValidationError({"cost_description": "참가비가 있는 경우 설명을 입력해야 합니다."})

        return attrs

    def validate_max_members(self, value):
        """모집 인원 유효성을 검증합니다.

        Args:
            value (int): 모집 인원 수

        Returns:
            int: 검증된 모집 인원 수

        Raises:
            serializers.ValidationError: 인원이 2명 미만 또는 100명 초과인 경우
        """
        if value < 2:
            raise serializers.ValidationError("모집 인원은 최소 2명 이상이어야 합니다.")
        if value > 100:
            raise serializers.ValidationError("모집 인원은 최대 100명까지 가능합니다.")
        return value


class GatheringUpdateSerializer(serializers.ModelSerializer):
    """모임 수정용 Serializer

    모집 상태에 따라 수정 가능한 필드가 제한됩니다.
    """

    class Meta:
        model = Gathering
        fields = [
            "title",
            "description",
            "max_members",
            "recruitment_end",
            "start_date",
            "end_date",
            "meeting_schedule",
            "location",
            "has_cost",
            "cost_description",
            "required_skills",
            "project_goal",
        ]

    def validate_max_members(self, value):
        """모집 인원 수정 시 현재 참여 인원보다 적을 수 없음"""
        instance = self.instance
        if value < instance.current_members:
            raise serializers.ValidationError(
                f"모집 인원은 현재 참여 인원({instance.current_members}명)보다 적을 수 없습니다."
            )
        return value

    def validate(self, attrs):
        """모임 상태에 따른 수정 제한"""
        instance = self.instance

        # 종료된 모임은 수정 불가
        if instance.status == Gathering.GatheringStatus.FINISHED:
            raise serializers.ValidationError("종료된 모임은 수정할 수 없습니다.")

        # 진행 중인 모임은 제한적 수정만 가능
        if instance.status == Gathering.GatheringStatus.IN_PROGRESS:
            allowed_fields = {"description", "meeting_schedule", "location", "end_date"}
            requested_fields = set(attrs.keys())
            invalid_fields = requested_fields - allowed_fields

            if invalid_fields:
                raise serializers.ValidationError(f"진행 중인 모임은 {', '.join(allowed_fields)}만 수정할 수 있습니다.")

        return attrs
