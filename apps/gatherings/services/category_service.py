import logging
from typing import Dict, List, Optional

from django.db.models import Count, Q

from apps.gatherings.models import Category

logger = logging.getLogger(__name__)


class CategoryService:
    """카테고리 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    @staticmethod
    def get_active_categories() -> List[Category]:
        """활성화된 카테고리 목록 조회

        Returns:
            활성화된 카테고리 리스트
        """
        return Category.objects.filter(is_active=True).select_related("parent").order_by("name")

    @staticmethod
    def get_parent_categories() -> List[Category]:
        """최상위(부모) 카테고리만 조회

        Returns:
            부모 카테고리 리스트
        """
        return Category.objects.filter(parent__isnull=True, is_active=True).order_by("name")

    @staticmethod
    def get_child_categories(parent_id: int) -> List[Category]:
        """특정 부모의 자식 카테고리 조회

        Args:
            parent_id: 부모 카테고리 ID

        Returns:
            자식 카테고리 리스트
        """
        return Category.objects.filter(parent_id=parent_id, is_active=True).select_related("parent").order_by("name")

    @staticmethod
    def get_category_with_stats(category_id: int) -> Optional[Dict]:
        """카테고리 정보와 통계 조회

        Args:
            category_id: 카테고리 ID

        Returns:
            카테고리 정보 및 모임 수 통계
        """
        try:
            from apps.gatherings.models import Gathering

            category = (
                Category.objects.filter(id=category_id)
                .select_related("parent")
                .annotate(
                    total_gatherings=Count("gatherings"),
                    recruiting_gatherings=Count(
                        "gatherings", filter=Q(gatherings__status=Gathering.GatheringStatus.RECRUITING)
                    ),
                )
                .first()
            )

            if not category:
                return None

            return {
                "id": category.id,
                "parent": category.parent_id,
                "parent_name": category.parent.name if category.parent else None,
                "name": category.name,
                "description": category.description,
                "is_active": category.is_active,
                "total_gatherings": category.total_gatherings,
                "recruiting_gatherings": category.recruiting_gatherings,
            }
        except Category.DoesNotExist:
            return None

    @staticmethod
    def get_hierarchical_categories() -> List[Dict]:
        """계층 구조로 카테고리 조회 (부모-자식 관계)

        Returns:
            계층 구조의 카테고리 리스트
        """
        parents = Category.objects.filter(parent__isnull=True, is_active=True).prefetch_related("children")

        result = []
        for parent in parents:
            children = [
                {"id": child.id, "name": child.name, "description": child.description}
                for child in parent.children.filter(is_active=True)
            ]

            result.append(
                {
                    "id": parent.id,
                    "name": parent.name,
                    "description": parent.description,
                    "children": children,
                }
            )

        return result

    @staticmethod
    def create_category(name: str, description: str = None, parent_id: int = None) -> Category:
        """카테고리 생성

        Args:
            name: 카테고리 이름
            description: 카테고리 설명
            parent_id: 부모 카테고리 ID (선택)

        Returns:
            생성된 카테고리

        Raises:
            ValueError: 잘못된 부모 카테고리
        """
        if parent_id:
            try:
                parent = Category.objects.get(id=parent_id)
                if parent.parent is not None:
                    raise ValueError("2단계 이상의 계층 구조는 지원하지 않습니다.")
            except Category.DoesNotExist:
                raise ValueError("존재하지 않는 부모 카테고리입니다.")
        else:
            parent = None

        category = Category.objects.create(name=name, description=description, parent=parent)

        logger.info(f"Category created: {category.name} (ID: {category.id})")
        return category

    @staticmethod
    def update_category(category_id: int, name: str = None, description: str = None) -> Category:
        """카테고리 수정

        Args:
            category_id: 카테고리 ID
            name: 새 이름
            description: 새 설명

        Returns:
            수정된 카테고리

        Raises:
            ValueError: 존재하지 않는 카테고리
        """
        try:
            category = Category.objects.get(id=category_id)

            if name:
                category.name = name
            if description is not None:
                category.description = description

            category.save()

            logger.info(f"Category updated: {category.name} (ID: {category.id})")
            return category

        except Category.DoesNotExist:
            raise ValueError("존재하지 않는 카테고리입니다.")

    @staticmethod
    def deactivate_category(category_id: int) -> bool:
        """카테고리 비활성화

        자식 카테고리도 함께 비활성화됩니다.

        Args:
            category_id: 카테고리 ID

        Returns:
            성공 여부

        Raises:
            ValueError: 존재하지 않는 카테고리 또는 모임이 있는 경우
        """
        try:
            from apps.gatherings.models import Gathering

            category = Category.objects.get(id=category_id)

            # 해당 카테고리의 모임이 있는지 확인
            if category.gatherings.filter(
                status__in=[Gathering.GatheringStatus.RECRUITING, Gathering.GatheringStatus.IN_PROGRESS]
            ).exists():
                raise ValueError("진행 중인 모임이 있는 카테고리는 비활성화할 수 없습니다.")

            category.is_active = False
            category.save()

            # 자식 카테고리도 비활성화
            if category.children.exists():
                category.children.update(is_active=False)

            logger.info(f"Category deactivated: {category.name} (ID: {category.id})")
            return True

        except Category.DoesNotExist:
            raise ValueError("존재하지 않는 카테고리입니다.")
