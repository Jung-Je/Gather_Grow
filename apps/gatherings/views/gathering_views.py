from typing import Any

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.gatherings.serializers.gathering_serializer import (
    GatheringCreateSerializer,
    GatheringDetailSerializer,
    GatheringListSerializer,
    GatheringUpdateSerializer,
)
from apps.gatherings.services.gathering_service import GatheringService


class GatheringPagination(PageNumberPagination):
    """모임 목록 페이지네이션"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class GatheringListView(APIView):
    """모임 목록 조회 및 생성 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="모임 목록 조회",
        description="모임 목록을 조회합니다. 다양한 필터링 옵션을 지원합니다.",
        parameters=[
            OpenApiParameter(name="type", type=str, description="모임 유형 (study/project)"),
            OpenApiParameter(name="category", type=int, description="카테고리 ID"),
            OpenApiParameter(
                name="status", type=str, description="모집 상태 (recruiting/recruitment_complete/in_progress/finished)"
            ),
            OpenApiParameter(name="study_type", type=str, description="진행 방식 (online/offline/mixed)"),
            OpenApiParameter(
                name="target_level", type=str, description="대상 수준 (beginner/intermediate/advanced/all)"
            ),
            OpenApiParameter(name="is_recruiting", type=bool, description="모집 중 여부"),
            OpenApiParameter(name="search", type=str, description="검색어 (제목/설명)"),
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 20, 최대: 100)"),
        ],
        responses={
            200: GatheringListSerializer(many=True),
            400: OpenApiResponse(description="잘못된 필터 값"),
        },
        tags=["모임"],
    )
    def get(self, request: Any) -> APIResponse:
        """모임 목록 조회 (필터링 지원)

        Query Parameters:
            type (str): 모임 유형 (study/project)
            category (int): 카테고리 ID
            status (str): 모집 상태 (recruiting/recruitment_complete/in_progress/finished)
            study_type (str): 진행 방식 (online/offline/mixed)
            target_level (str): 대상 수준 (beginner/intermediate/advanced/all)
            is_recruiting (bool): 모집 중 여부
            search (str): 검색어 (제목/설명)
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 20, max: 100)

        Returns:
            APIResponse:
                - 200: 모임 목록 (페이지네이션)
                - 400: 잘못된 필터 값
        """
        # 필터 파라미터 추출
        gathering_type = request.query_params.get("type")
        category_id = request.query_params.get("category")
        status = request.query_params.get("status")
        study_type = request.query_params.get("study_type")
        target_level = request.query_params.get("target_level")
        is_recruiting = request.query_params.get("is_recruiting")
        search = request.query_params.get("search")

        # 필터 값 검증
        from apps.gatherings.models import Gathering

        if gathering_type and gathering_type not in dict(Gathering.GatheringType.choices):
            return APIResponse.bad_request(
                message=f"잘못된 모임 유형입니다. 허용된 값: {', '.join(dict(Gathering.GatheringType.choices).keys())}"
            )

        if status and status not in dict(Gathering.GatheringStatus.choices):
            return APIResponse.bad_request(
                message=f"잘못된 모집 상태입니다. 허용된 값: {', '.join(dict(Gathering.GatheringStatus.choices).keys())}"
            )

        if study_type and study_type not in dict(Gathering.StudyType.choices):
            return APIResponse.bad_request(
                message=f"잘못된 진행 방식입니다. 허용된 값: {', '.join(dict(Gathering.StudyType.choices).keys())}"
            )

        if target_level and target_level not in dict(Gathering.TargetLevel.choices):
            return APIResponse.bad_request(
                message=f"잘못된 대상 수준입니다. 허용된 값: {', '.join(dict(Gathering.TargetLevel.choices).keys())}"
            )

        # is_recruiting을 boolean으로 변환
        if is_recruiting is not None:
            is_recruiting = is_recruiting.lower() == "true"

        # category_id를 int로 변환
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                return APIResponse.bad_request(message="잘못된 카테고리 ID입니다.")

        # 서비스 호출
        gatherings = GatheringService.get_gathering_list(
            gathering_type=gathering_type,
            category_id=category_id,
            status=status,
            study_type=study_type,
            target_level=target_level,
            is_recruiting=is_recruiting,
            search=search,
        )

        paginator = GatheringPagination()
        paginated_gatherings = paginator.paginate_queryset(gatherings, request)
        serializer = GatheringListSerializer(paginated_gatherings, many=True)

        return APIResponse.success(
            message="모임 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )

    @extend_schema(
        summary="모임 생성",
        description="새로운 모임을 생성합니다. 인증이 필요합니다.",
        request=GatheringCreateSerializer,
        responses={
            201: GatheringDetailSerializer,
            400: OpenApiResponse(description="잘못된 입력 데이터"),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임"],
    )
    def post(self, request: Any) -> APIResponse:
        """모임 생성

        Args:
            request: HTTP 요청 객체 (인증 필요)
                - category (int): 카테고리 ID
                - type (str): 모임 유형
                - title (str): 제목
                - description (str): 상세 설명
                - max_members (int): 모집 인원
                - recruitment_end (date): 모집 마감일
                - start_date (date): 시작일
                - end_date (date, optional): 종료일
                - meeting_schedule (str, optional): 모임 일정
                - study_type (str): 진행 방식
                - location (str, optional): 모임 장소
                - target_level (str): 대상 수준
                - has_cost (bool): 참가비 여부
                - cost_description (str, optional): 참가비 설명
                - required_skills (str, optional): 필요 기술 스택
                - project_goal (str, optional): 프로젝트 목표

        Returns:
            APIResponse:
                - 201: 모임 생성 성공
                - 400: 잘못된 입력 데이터
                - 401: 인증 필요
        """
        try:
            serializer = GatheringCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            gathering = GatheringService.create_gathering(user=request.user, data=serializer.validated_data)

            result_serializer = GatheringDetailSerializer(gathering)
            return APIResponse.created(message="모임이 생성되었습니다.", data=result_serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="모임 생성에 실패했습니다.")


class GatheringDetailView(APIView):
    """모임 상세 조회, 수정, 삭제 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="모임 상세 조회",
        description="특정 모임의 상세 정보를 조회합니다.",
        responses={
            200: GatheringDetailSerializer,
            404: OpenApiResponse(description="존재하지 않는 모임"),
        },
        tags=["모임"],
    )
    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 상세 조회

        Args:
            gathering_id: 모임 ID

        Returns:
            APIResponse:
                - 200: 모임 상세 정보
                - 404: 존재하지 않는 모임
        """
        gathering = GatheringService.get_gathering_detail(gathering_id)

        if not gathering:
            return APIResponse.not_found(message="존재하지 않는 모임입니다.")

        serializer = GatheringDetailSerializer(gathering)
        return APIResponse.success(message="모임 조회 성공", data=serializer.data)

    @extend_schema(
        summary="모임 수정",
        description="모임 정보를 수정합니다. 모임장만 수정할 수 있습니다.",
        request=GatheringUpdateSerializer,
        responses={
            200: GatheringDetailSerializer,
            400: OpenApiResponse(description="잘못된 입력 또는 권한 없음"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 모임"),
        },
        tags=["모임"],
    )
    def patch(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 수정

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (모임장만 가능)

        Returns:
            APIResponse:
                - 200: 모임 수정 성공
                - 400: 잘못된 입력 또는 권한 없음
                - 401: 인증 필요
                - 404: 존재하지 않는 모임
        """
        try:
            # 인스턴스를 먼저 가져와서 검증
            gathering = GatheringService.get_gathering_detail(gathering_id)
            if not gathering:
                return APIResponse.not_found(message="존재하지 않는 모임입니다.")

            # instance를 전달하여 serializer 생성 (validate에서 instance.status 접근 필요)
            serializer = GatheringUpdateSerializer(instance=gathering, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # 서비스 호출
            updated_gathering = GatheringService.update_gathering(
                gathering_id=gathering_id, user=request.user, data=serializer.validated_data
            )

            result_serializer = GatheringDetailSerializer(updated_gathering)
            return APIResponse.success(message="모임이 수정되었습니다.", data=result_serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="모임 수정에 실패했습니다.")

    @extend_schema(
        summary="모임 삭제",
        description="모임을 삭제합니다. 모임장만 삭제할 수 있습니다.",
        responses={
            200: OpenApiResponse(description="모임 삭제 성공"),
            400: OpenApiResponse(description="권한 없음 또는 삭제 불가 상태"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 모임"),
        },
        tags=["모임"],
    )
    def delete(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 삭제

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (모임장만 가능)

        Returns:
            APIResponse:
                - 200: 모임 삭제 성공
                - 400: 권한 없음 또는 삭제 불가 상태
                - 401: 인증 필요
                - 404: 존재하지 않는 모임
        """
        try:
            GatheringService.delete_gathering(gathering_id=gathering_id, user=request.user)
            return APIResponse.success(message="모임이 삭제되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="모임 삭제에 실패했습니다.")


class GatheringStatusView(APIView):
    """모임 상태 변경 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="모임 상태 변경",
        description="모임의 상태를 변경합니다. 모임장만 변경할 수 있습니다.",
        request=inline_serializer(
            name="GatheringStatusChangeRequest",
            fields={"status": serializers.CharField()},
        ),
        responses={
            200: GatheringDetailSerializer,
            400: OpenApiResponse(description="잘못된 상태 또는 권한 없음"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 모임"),
        },
        tags=["모임"],
    )
    def patch(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 상태 변경

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (모임장만 가능)
                - status (str): 새 상태

        Returns:
            APIResponse:
                - 200: 상태 변경 성공
                - 400: 잘못된 상태 또는 권한 없음
                - 401: 인증 필요
                - 404: 존재하지 않는 모임
        """
        try:
            new_status = request.data.get("status")

            if not new_status:
                return APIResponse.bad_request(message="변경할 상태를 입력해주세요.")

            gathering = GatheringService.change_gathering_status(
                gathering_id=gathering_id, user=request.user, new_status=new_status
            )

            serializer = GatheringDetailSerializer(gathering)
            return APIResponse.success(message="모임 상태가 변경되었습니다.", data=serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="상태 변경에 실패했습니다.")


class MyGatheringListView(APIView):
    """내가 참여한 모임 목록 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내가 참여한 모임 목록 조회",
        description="내가 참여 중인 모임 목록을 조회합니다. 역할별로 필터링할 수 있습니다.",
        parameters=[
            OpenApiParameter(name="role", type=str, description="역할 필터 (leader/participant)"),
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 20, 최대: 100)"),
        ],
        responses={
            200: GatheringListSerializer(many=True),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임"],
    )
    def get(self, request: Any) -> APIResponse:
        """내가 참여한 모임 목록 조회

        Query Parameters:
            role (str, optional): 역할 필터 (leader/participant)
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 20, max: 100)

        Returns:
            APIResponse:
                - 200: 참여 중인 모임 목록 (페이지네이션)
                - 401: 인증 필요
        """
        role = request.query_params.get("role")

        gatherings = GatheringService.get_my_gatherings(user=request.user, role=role)

        paginator = GatheringPagination()
        paginated_gatherings = paginator.paginate_queryset(gatherings, request)
        serializer = GatheringListSerializer(paginated_gatherings, many=True)

        return APIResponse.success(
            message="내 모임 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )


class GatheringStatisticsView(APIView):
    """모임 통계 조회 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="모임 통계 조회",
        description="모임의 통계 정보를 조회합니다. 참여 인원, 활동 통계 등을 포함합니다.",
        responses={
            200: OpenApiResponse(description="모임 통계 정보"),
            404: OpenApiResponse(description="존재하지 않는 모임"),
        },
        tags=["모임"],
    )
    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 통계 조회

        Args:
            gathering_id: 모임 ID

        Returns:
            APIResponse:
                - 200: 모임 통계 정보
                - 404: 존재하지 않는 모임
        """
        stats = GatheringService.get_gathering_statistics(gathering_id)

        if not stats:
            return APIResponse.not_found(message="존재하지 않는 모임입니다.")

        return APIResponse.success(message="모임 통계 조회 성공", data=stats)
