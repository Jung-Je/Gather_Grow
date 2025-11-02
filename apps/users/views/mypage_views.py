import logging
from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.users.serializers.mypage_serializer import (
    PasswordChangeSerializer,
    ProfileSerializer,
)
from apps.users.services.services import AuthenticationService
from apps.users.services.validators import PasswordValidator

logger = logging.getLogger(__name__)


class ProfileView(APIView):
    """사용자 프로필 관리 API

    인증된 사용자의 프로필 정보를 조회하고 수정합니다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Any) -> APIResponse:
        """프로필 조회

        Args:
            request: HTTP 요청 객체 (인증된 사용자 필요)

        Returns:
            APIResponse:
                - 200: 프로필 정보 반환
                - 401: 인증 필요
        """
        user = request.user
        serializer = ProfileSerializer(user)
        return APIResponse.success(message="프로필 조회 성공", data=serializer.data)

    def patch(self, request: Any) -> APIResponse:
        """프로필 수정

        Args:
            request: HTTP 요청 객체
                - username (str, optional): 사용자명
                - profile (str, optional): 프로필 설명
                - profile_image (file, optional): 프로필 이미지
                - education_level (str, optional): 학력
                - location (str, optional): 지역

        Returns:
            APIResponse:
                - 200: 프로필 수정 성공
                - 400: 잘못된 입력 데이터
                - 401: 인증 필요
        """
        try:
            user = request.user

            # 변경된 필드 추적
            changed_fields = []
            for field in ["username", "profile", "profile_image", "education_level", "location"]:
                if field in request.data:
                    old_value = getattr(user, field)
                    new_value = request.data.get(field)
                    if old_value != new_value:
                        changed_fields.append(field)

            serializer = ProfileSerializer(user, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # 로깅 (변경된 필드만 기록)
            if changed_fields:
                logger.info(
                    f"Profile updated: user_id={user.id}, username={user.username}, "
                    f"changed_fields={', '.join(changed_fields)}"
                )

            return APIResponse.success(message="프로필 수정 성공", data=serializer.data)
        except Exception as e:
            return APIResponse.from_exception(e, message="프로필 수정에 실패했습니다.", log_error=False)


class PasswordChangeView(APIView):
    """비밀번호 변경 API

    인증된 사용자의 비밀번호를 변경합니다.
    현재 비밀번호 확인 후 새 비밀번호로 변경합니다.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request: Any) -> APIResponse:
        """비밀번호 변경 처리

        마이페이지에서 현재 비밀번호 확인 후 새 비밀번호로 변경.
        로그인한 상태에서만 사용 가능합니다.

        Args:
            request: HTTP 요청 객체
                - old_password (str): 현재 비밀번호
                - new_password (str): 새 비밀번호
                - confirm_new_password (str): 새 비밀번호 확인

        Returns:
            APIResponse:
                - 200: 비밀번호 변경 성공
                - 400: 현재 비밀번호 불일치 또는 잘못된 입력
                - 401: 인증 필요
        """
        try:
            user = request.user
            serializer = PasswordChangeSerializer(user, data=request.data, context={"request": request})

            if not serializer.is_valid():
                return APIResponse.bad_request(message="비밀번호 변경 실패", data=serializer.errors)

            # 비밀번호 유효성 검증
            new_password = serializer.validated_data["new_password"]
            error_message = PasswordValidator.validate(new_password)
            if error_message:
                return APIResponse.bad_request(message=error_message)

            # Serializer를 통해 비밀번호 변경
            serializer.save()
            return APIResponse.success(message="비밀번호가 성공적으로 변경되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="비밀번호 변경에 실패했습니다.", log_error=False)


class AccountDeleteView(APIView):
    """회원 탈퇴 API

    개인정보보호법에 따라 즉시 삭제하지 않고 90일간 보관 후 완전 삭제됩니다.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Any) -> APIResponse:
        """회원 탈퇴 처리

        Args:
            request: HTTP 요청 객체
                - password (str, optional): 비밀번호 (일반 가입자만 필요)

        Returns:
            APIResponse:
                - 200: 탈퇴 성공
                - 400: 비밀번호 불일치
                - 401: 인증 필요
        """
        try:
            user = request.user
            password = request.data.get("password")

            AuthenticationService.delete_account(user, password)

            # 쿠키 삭제
            response = APIResponse.success(
                message="회원 탈퇴가 완료되었습니다. 90일 후 모든 데이터가 완전히 삭제됩니다."
            )
            response.delete_cookie("refresh_token")
            response.delete_cookie("access_token")

            return response

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="회원 탈퇴 처리 중 오류가 발생했습니다.")
