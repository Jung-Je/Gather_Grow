from rest_framework import serializers

from apps.gatherings.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 조회용 Serializer

    계층 구조를 지원하며, 부모-자식 관계를 표시합니다.
    """

    parent_name = serializers.CharField(source="parent.name", read_only=True, allow_null=True)
    depth = serializers.IntegerField(read_only=True)
    is_parent = serializers.BooleanField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "parent",
            "parent_name",
            "name",
            "description",
            "is_active",
            "depth",
            "is_parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_parent(self, value):
        """부모 카테고리 유효성 검증

        - 자기 자신을 부모로 설정할 수 없음
        - 2단계 이상의 계층 구조는 지원하지 않음
        """
        if not value:
            return value

        # 수정 시 자기 자신을 부모로 설정하는지 확인
        if self.instance and value.id == self.instance.id:
            raise serializers.ValidationError("자기 자신을 부모 카테고리로 설정할 수 없습니다.")

        # 2단계 이상의 계층 구조 방지
        if value.parent is not None:
            raise serializers.ValidationError("2단계 이상의 계층 구조는 지원하지 않습니다.")

        return value


class CategoryListSerializer(serializers.ModelSerializer):
    """카테고리 목록 조회용 간단한 Serializer"""

    parent_name = serializers.CharField(source="parent.name", read_only=True, allow_null=True)

    class Meta:
        model = Category
        fields = ["id", "parent", "parent_name", "name", "is_active"]
