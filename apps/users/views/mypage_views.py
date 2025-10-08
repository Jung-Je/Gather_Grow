from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.users.serializers.mypage_serializer import ProfileSerializer, PasswordChangeSerializer
from apps.users.services.services import AuthenticationService


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
            serializer = ProfileSerializer(
                user, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success(message="프로필 수정 성공", data=serializer.data)
        except Exception as e:
            return APIResponse.from_exception(
                e, message="프로필 수정에 실패했습니다.", log_error=False
            )


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
            serializer = PasswordChangeSerializer(
                user, data=request.data, context={"request": request}
            )
            
            if not serializer.is_valid():
                return APIResponse.bad_request(
                    message="비밀번호 변경 실패",
                    data=serializer.errors
                )
            
            # 비밀번호 유효성 검증
            new_password = serializer.validated_data['new_password']
            import re

            if len(new_password) < 8:
                return APIResponse.bad_request(
                    message="비밀번호는 8자 이상이어야 합니다."
                )

            if len(new_password) > 50:
                return APIResponse.bad_request(
                    message="비밀번호는 50자를 초과할 수 없습니다."
                )

            if " " in new_password:
                return APIResponse.bad_request(
                    message="비밀번호에는 공백이 포함될 수 없습니다."
                )

            if not re.search(r"[a-zA-Z]", new_password):
                return APIResponse.bad_request(
                    message="비밀번호에는 영문자가 포함되어야 합니다."
                )

            if not re.search(r"[0-9]", new_password):
                return APIResponse.bad_request(
                    message="비밀번호에는 숫자가 포함되어야 합니다."
                )

            if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?`~]', new_password):
                return APIResponse.bad_request(
                    message="비밀번호에는 특수문자가 포함되어야 합니다."
                )

            if re.search(r"(.)\1{2,}", new_password):
                return APIResponse.bad_request(
                    message="동일한 문자를 3개 이상 연속으로 사용할 수 없습니다."
                )

            # 동일한 문자(숫자/특수문자) 3번 이상 사용 금지
            from collections import Counter

            char_count = Counter(new_password)
            for char, count in char_count.items():
                if count >= 3 and (char.isdigit() or not char.isalpha()):
                    return APIResponse.bad_request(
                        message=f"'{char}' 문자는 3번 이상 사용할 수 없습니다."
                    )

            # Serializer를 통해 비밀번호 변경
            serializer.save()
            return APIResponse.success(message="비밀번호가 성공적으로 변경되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(
                e, message="비밀번호 변경에 실패했습니다.", log_error=False
            )
