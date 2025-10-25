from typing import Any

from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.gatherings.serializers.category_serializer import (
    CategoryListSerializer,
    CategorySerializer,
)
from apps.gatherings.services.category_service import CategoryService


class CategoryListView(APIView):
    """카테고리 목록 조회 API

    모든 사용자가 접근 가능하며, 활성화된 카테고리만 반환합니다.
    """

    permission_classes = [AllowAny]

    def get(self, request: Any) -> APIResponse:
        """카테고리 목록 조회

        Query Parameters:
            hierarchical (bool): True일 경우 계층 구조로 반환

        Returns:
            APIResponse:
                - 200: 카테고리 목록
        """
        hierarchical = request.query_params.get("hierarchical", "false").lower() == "true"

        if hierarchical:
            # 계층 구조로 반환
            categories = CategoryService.get_hierarchical_categories()
            return APIResponse.success(message="카테고리 목록 조회 성공", data=categories)
        else:
            # 평면 목록으로 반환
            categories = CategoryService.get_active_categories()
            serializer = CategoryListSerializer(categories, many=True)
            return APIResponse.success(message="카테고리 목록 조회 성공", data=serializer.data)


class CategoryDetailView(APIView):
    """카테고리 상세 조회 API"""

    permission_classes = [AllowAny]

    def get(self, request: Any, category_id: int) -> APIResponse:
        """카테고리 상세 정보 및 통계 조회

        Args:
            category_id: 카테고리 ID

        Returns:
            APIResponse:
                - 200: 카테고리 상세 정보
                - 404: 존재하지 않는 카테고리
        """
        category_data = CategoryService.get_category_with_stats(category_id)

        if not category_data:
            return APIResponse.not_found(message="존재하지 않는 카테고리입니다.")

        return APIResponse.success(message="카테고리 조회 성공", data=category_data)


class CategoryManageView(APIView):
    """카테고리 생성/수정/삭제 API (관리자 전용)"""

    permission_classes = [IsAdminUser]

    def post(self, request: Any) -> APIResponse:
        """카테고리 생성

        Args:
            request: HTTP 요청 객체
                - name (str): 카테고리 이름
                - description (str, optional): 카테고리 설명
                - parent (int, optional): 부모 카테고리 ID

        Returns:
            APIResponse:
                - 201: 카테고리 생성 성공
                - 400: 잘못된 입력 데이터
        """
        try:
            serializer = CategorySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            name = serializer.validated_data["name"]
            description = serializer.validated_data.get("description")
            parent_id = serializer.validated_data.get("parent")

            category = CategoryService.create_category(
                name=name, description=description, parent_id=parent_id.id if parent_id else None
            )

            result_serializer = CategorySerializer(category)
            return APIResponse.created(message="카테고리가 생성되었습니다.", data=result_serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="카테고리 생성에 실패했습니다.")

    def patch(self, request: Any, category_id: int) -> APIResponse:
        """카테고리 수정

        Args:
            category_id: 카테고리 ID
            request: HTTP 요청 객체
                - name (str, optional): 새 이름
                - description (str, optional): 새 설명

        Returns:
            APIResponse:
                - 200: 카테고리 수정 성공
                - 400: 잘못된 입력 데이터
                - 404: 존재하지 않는 카테고리
        """
        try:
            name = request.data.get("name")
            description = request.data.get("description")

            category = CategoryService.update_category(category_id=category_id, name=name, description=description)

            serializer = CategorySerializer(category)
            return APIResponse.success(message="카테고리가 수정되었습니다.", data=serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="카테고리 수정에 실패했습니다.")

    def delete(self, request: Any, category_id: int) -> APIResponse:
        """카테고리 비활성화

        Args:
            category_id: 카테고리 ID

        Returns:
            APIResponse:
                - 200: 카테고리 비활성화 성공
                - 400: 진행 중인 모임이 있는 경우
                - 404: 존재하지 않는 카테고리
        """
        try:
            CategoryService.deactivate_category(category_id)
            return APIResponse.success(message="카테고리가 비활성화되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="카테고리 비활성화에 실패했습니다.")


class ParentCategoryListView(APIView):
    """최상위 카테고리 목록 조회 API"""

    permission_classes = [AllowAny]

    def get(self, request: Any) -> APIResponse:
        """최상위(부모) 카테고리만 조회

        Returns:
            APIResponse:
                - 200: 부모 카테고리 목록
        """
        categories = CategoryService.get_parent_categories()
        serializer = CategoryListSerializer(categories, many=True)
        return APIResponse.success(message="부모 카테고리 목록 조회 성공", data=serializer.data)


class ChildCategoryListView(APIView):
    """자식 카테고리 목록 조회 API"""

    permission_classes = [AllowAny]

    def get(self, request: Any, parent_id: int) -> APIResponse:
        """특정 부모의 자식 카테고리 조회

        Args:
            parent_id: 부모 카테고리 ID

        Returns:
            APIResponse:
                - 200: 자식 카테고리 목록
        """
        categories = CategoryService.get_child_categories(parent_id)
        serializer = CategoryListSerializer(categories, many=True)
        return APIResponse.success(message="자식 카테고리 목록 조회 성공", data=serializer.data)
