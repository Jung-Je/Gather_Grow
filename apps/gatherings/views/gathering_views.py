from typing import Any

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


class GatheringListView(APIView):
    """모임 목록 조회 및 생성 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request: Any) -> APIResponse:
        """모임 목록 조회 (필터링 지원)

        Query Parameters:
            type (str): 모임 유형 (study/project)
            category (int): 카테고리 ID
            status (str): 모집 상태
            study_type (str): 진행 방식 (online/offline/mixed)
            target_level (str): 대상 수준
            is_recruiting (bool): 모집 중 여부
            search (str): 검색어 (제목/설명)

        Returns:
            APIResponse:
                - 200: 모임 목록
        """
        # 필터 파라미터 추출
        gathering_type = request.query_params.get("type")
        category_id = request.query_params.get("category")
        status = request.query_params.get("status")
        study_type = request.query_params.get("study_type")
        target_level = request.query_params.get("target_level")
        is_recruiting = request.query_params.get("is_recruiting")
        search = request.query_params.get("search")

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

        serializer = GatheringListSerializer(gatherings, many=True)
        return APIResponse.success(message="모임 목록 조회 성공", data=serializer.data)

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

    def get(self, request: Any) -> APIResponse:
        """내가 참여한 모임 목록 조회

        Query Parameters:
            role (str, optional): 역할 필터 (leader/participant)

        Returns:
            APIResponse:
                - 200: 참여 중인 모임 목록
                - 401: 인증 필요
        """
        role = request.query_params.get("role")

        gatherings = GatheringService.get_my_gatherings(user=request.user, role=role)

        serializer = GatheringListSerializer(gatherings, many=True)
        return APIResponse.success(message="내 모임 목록 조회 성공", data=serializer.data)


class GatheringStatisticsView(APIView):
    """모임 통계 조회 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

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
