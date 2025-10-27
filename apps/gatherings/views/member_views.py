from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.gatherings.serializers.member_serializer import (
    GatheringMemberSerializer,
    MemberApprovalSerializer,
    MemberCancelSerializer,
    MemberJoinSerializer,
    MemberLeaveSerializer,
    MemberRemoveSerializer,
)
from apps.gatherings.services.member_service import MemberService
from apps.gatherings.models import GatheringMember


class GatheringMemberListView(APIView):
    """모임 멤버 목록 조회 API"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """모임 멤버 목록 조회

        Query Parameters:
            status (str, optional): 멤버 상태 필터 (pending/approved/rejected)
            role (str, optional): 역할 필터 (leader/participant)

        Args:
            gathering_id: 모임 ID

        Returns:
            APIResponse:
                - 200: 멤버 목록
                - 401: 인증 필요
        """
        status = request.query_params.get("status")
        role = request.query_params.get("role")

        members = MemberService.get_gathering_members(gathering_id=gathering_id, status=status, role=role)

        serializer = GatheringMemberSerializer(members, many=True)
        return APIResponse.success(message="멤버 목록 조회 성공", data=serializer.data)


class MemberJoinView(APIView):
    """모임 가입 신청 API"""

    permission_classes = [IsAuthenticated]

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

    def get(self, request: Any, gathering_id: int) -> APIResponse:
        """승인 대기 중인 멤버 목록 조회

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체 (인증 필요)

        Returns:
            APIResponse:
                - 200: 대기 중인 멤버 목록
                - 401: 인증 필요
        """
        members = MemberService.get_pending_members(gathering_id=gathering_id)

        serializer = GatheringMemberSerializer(members, many=True)
        return APIResponse.success(message="대기 중인 멤버 목록 조회 성공", data=serializer.data)


class MemberStatusCheckView(APIView):
    """사용자의 모임 참여 상태 확인 API"""

    permission_classes = [IsAuthenticated]

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
