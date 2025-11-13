from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.gatherings.models import GatheringMember
from apps.gatherings.serializers.member_serializer import (
    GatheringMemberSerializer,
    MemberApprovalSerializer,
    MemberCancelSerializer,
    MemberJoinSerializer,
    MemberLeaveSerializer,
    MemberRemoveSerializer,
)
from apps.gatherings.services.member_service import MemberService


class MemberPagination(PageNumberPagination):
    """멤버 목록 페이지네이션"""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class GatheringMemberListView(APIView):
    """모임 멤버 목록 조회 API (승인된 멤버만)"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="모임 멤버 목록 조회",
        description="모임의 승인된 멤버 목록을 조회합니다. 역할별로 필터링할 수 있습니다.",
        parameters=[
            OpenApiParameter(name="role", type=str, description="역할 필터 (leader/participant)"),
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 50, 최대: 200)"),
        ],
        responses={
            200: GatheringMemberSerializer(many=True),
        },
        tags=["모임 멤버"],
    )
    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 멤버 목록 조회 (승인된 멤버만 공개)

        Query Parameters:
            role (str, optional): 역할 필터 (leader/participant)
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 50, max: 200)

        Args:
            gathering_id: 모임 ID

        Returns:
            APIResponse:
                - 200: 승인된 멤버 목록 (누구나 조회 가능, 페이지네이션)
        """
        role = request.query_params.get("role")

        # 승인된 멤버만 조회 (개인정보 보호)
        members = MemberService.get_gathering_members(
            gathering_id=gathering_id, status=GatheringMember.MemberStatus.APPROVED, role=role
        )

        # 페이지네이션 적용
        paginator = MemberPagination()
        paginated_members = paginator.paginate_queryset(members, request)
        serializer = GatheringMemberSerializer(paginated_members, many=True)

        return APIResponse.success(
            message="멤버 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )


class MemberJoinView(APIView):
    """모임 가입 신청 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="모임 가입 신청",
        description="모임 가입을 신청합니다. 승인 후 모임에 참여할 수 있습니다.",
        request=MemberJoinSerializer,
        responses={
            201: GatheringMemberSerializer,
            400: OpenApiResponse(description="가입 불가 조건 (정원 초과, 중복 신청 등)"),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임 멤버"],
    )
    def post(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 가입 신청

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (인증 필요)

        Returns:
            APIResponse:
                - 201: 가입 신청 성공
                - 400: 가입 불가 조건
                - 401: 인증 필요
        """
        try:
            serializer = MemberJoinSerializer(data={"gathering": gathering_id}, context={"request": request})
            serializer.is_valid(raise_exception=True)

            # 서비스 레이어에서 비즈니스 로직 처리
            member = MemberService.join_gathering(user=request.user, gathering_id=gathering_id)

            result_serializer = GatheringMemberSerializer(member)
            return APIResponse.created(message="모임 가입 신청이 완료되었습니다.", data=result_serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="가입 신청에 실패했습니다.")


class MemberApprovalView(APIView):
    """모임 멤버 승인/거절 API (모임장 전용)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="멤버 승인/거절 (모임장)",
        description="가입 신청한 멤버를 승인하거나 거절합니다. 모임장만 사용할 수 있습니다.",
        request=MemberApprovalSerializer,
        responses={
            200: GatheringMemberSerializer,
            400: OpenApiResponse(description="권한 없음 또는 잘못된 요청"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 멤버"),
        },
        tags=["모임 멤버"],
    )
    def patch(self, request: Any, member_id: int) -> APIResponse:
        """멤버 승인 또는 거절

        Args:
            member_id: 멤버 ID
            request: HTTP 요청 객체 (모임장만 가능)
                - action (str): "approve" 또는 "reject"

        Returns:
            APIResponse:
                - 200: 처리 성공
                - 400: 권한 없음 또는 잘못된 요청
                - 401: 인증 필요
        """
        try:
            try:
                member = GatheringMember.objects.get(id=member_id)
            except GatheringMember.DoesNotExist:
                return APIResponse.not_found(message="존재하지 않는 멤버입니다.")

            # Serializer로 검증
            serializer = MemberApprovalSerializer(instance=member, data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            # 서비스 레이어에서 비즈니스 로직 처리
            action = serializer.validated_data["action"]
            if action == "approve":
                member = MemberService.approve_member(member_id=member_id)
                message = "멤버가 승인되었습니다."
            else:
                member = MemberService.reject_member(member_id=member_id)
                message = "멤버가 거절되었습니다."

            result_serializer = GatheringMemberSerializer(member)
            return APIResponse.success(message=message, data=result_serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="멤버 처리에 실패했습니다.")


class MemberLeaveView(APIView):
    """모임 탈퇴 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="모임 탈퇴",
        description="모임에서 탈퇴합니다. 모임장은 탈퇴할 수 없습니다.",
        request=MemberLeaveSerializer,
        responses={
            200: OpenApiResponse(description="탈퇴 성공"),
            400: OpenApiResponse(description="탈퇴 불가 조건 (모임장, 승인되지 않은 멤버 등)"),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임 멤버"],
    )
    def delete(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 탈퇴

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (인증 필요)

        Returns:
            APIResponse:
                - 200: 탈퇴 성공
                - 400: 탈퇴 불가 조건
                - 401: 인증 필요
        """
        try:
            serializer = MemberLeaveSerializer(data={"gathering": gathering_id}, context={"request": request})
            serializer.is_valid(raise_exception=True)

            # 서비스 레이어에서 비즈니스 로직 처리
            MemberService.leave_gathering(user=request.user, gathering_id=gathering_id)
            return APIResponse.success(message="모임에서 탈퇴했습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="탈퇴 처리에 실패했습니다.")


class MemberCancelJoinView(APIView):
    """가입 신청 취소 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="가입 신청 취소",
        description="대기 중인 가입 신청을 취소합니다.",
        request=MemberCancelSerializer,
        responses={
            200: OpenApiResponse(description="취소 성공"),
            400: OpenApiResponse(description="대기 중인 신청 없음"),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임 멤버"],
    )
    def delete(self, request: Any, gathering_id: int) -> APIResponse:
        """가입 신청 취소 (대기 중인 상태만)

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (인증 필요)

        Returns:
            APIResponse:
                - 200: 취소 성공
                - 400: 대기 중인 신청 없음
                - 401: 인증 필요
        """
        try:
            serializer = MemberCancelSerializer(data={"gathering": gathering_id}, context={"request": request})
            serializer.is_valid(raise_exception=True)

            # 서비스 레이어에서 비즈니스 로직 처리
            MemberService.cancel_join_request(user=request.user, gathering_id=gathering_id)
            return APIResponse.success(message="가입 신청이 취소되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="취소 처리에 실패했습니다.")


class MemberRemoveView(APIView):
    """멤버 강제 탈퇴 API (모임장 전용)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="멤버 강제 탈퇴 (모임장)",
        description="모임 멤버를 강제로 탈퇴시킵니다. 모임장만 사용할 수 있습니다.",
        request=MemberRemoveSerializer,
        responses={
            200: OpenApiResponse(description="강제 탈퇴 성공"),
            400: OpenApiResponse(description="권한 없음 또는 강제 탈퇴 불가 (모임장 강퇴 불가 등)"),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임 멤버"],
    )
    def delete(self, request: Any, gathering_id: int, member_id: int) -> APIResponse:
        """멤버 강제 탈퇴

        Args:
            gathering_id: 모임 ID
            member_id: 멤버 ID
            request: HTTP 요청 객체 (모임장만 가능)

        Returns:
            APIResponse:
                - 200: 강제 탈퇴 성공
                - 400: 권한 없음 또는 강제 탈퇴 불가
                - 401: 인증 필요
        """
        try:
            serializer = MemberRemoveSerializer(
                data={"gathering": gathering_id, "member": member_id}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)

            # 서비스 레이어에서 비즈니스 로직 처리
            MemberService.remove_member(gathering_id=gathering_id, member_id=member_id)
            return APIResponse.success(message="멤버가 강제 탈퇴되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="강제 탈퇴 처리에 실패했습니다.")


class PendingMemberListView(APIView):
    """승인 대기 중인 멤버 목록 API (모임장 전용)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="승인 대기 멤버 목록 조회 (모임장)",
        description="승인 대기 중인 멤버 목록을 조회합니다. 모임장만 사용할 수 있습니다.",
        parameters=[
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 50, 최대: 200)"),
        ],
        responses={
            200: GatheringMemberSerializer(many=True),
            401: OpenApiResponse(description="인증 필요"),
            403: OpenApiResponse(description="권한 없음 (모임장 아님)"),
        },
        tags=["모임 멤버"],
    )
    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """승인 대기 중인 멤버 목록 조회 (모임장만 가능)

        Query Parameters:
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 50, max: 200)

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (모임장만 가능)

        Returns:
            APIResponse:
                - 200: 대기 중인 멤버 목록 (페이지네이션)
                - 401: 인증 필요
                - 403: 권한 없음 (모임장 아님)
        """
        # 모임장 권한 확인
        if not MemberService.is_gathering_leader(user=request.user, gathering_id=gathering_id):
            return APIResponse.forbidden(message="모임장만 대기 중인 멤버 목록을 조회할 수 있습니다.")

        members = MemberService.get_pending_members(gathering_id=gathering_id)

        # 페이지네이션 적용
        paginator = MemberPagination()
        paginated_members = paginator.paginate_queryset(members, request)
        serializer = GatheringMemberSerializer(paginated_members, many=True)

        return APIResponse.success(
            message="대기 중인 멤버 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )


class MemberStatusCheckView(APIView):
    """사용자의 모임 참여 상태 확인 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="모임 참여 상태 확인",
        description="현재 사용자의 모임 참여 상태를 확인합니다. 가입 여부, 승인 상태, 모임장 여부 등을 반환합니다.",
        responses={
            200: OpenApiResponse(
                description="참여 상태 정보 (status: pending/approved/rejected/not_member, is_leader: boolean)"
            ),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["모임 멤버"],
    )
    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """현재 사용자의 모임 참여 상태 확인

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (인증 필요)

        Returns:
            APIResponse:
                - 200: 참여 상태 정보
                  - status: pending/approved/rejected/not_member
                  - is_leader: 모임장 여부
                - 401: 인증 필요
        """
        status = MemberService.check_member_status(user=request.user, gathering_id=gathering_id)
        is_leader = MemberService.is_gathering_leader(user=request.user, gathering_id=gathering_id)

        data = {
            "gathering_id": gathering_id,
            "status": status,
            "is_leader": is_leader,
        }

        return APIResponse.success(message="참여 상태 조회 성공", data=data)
