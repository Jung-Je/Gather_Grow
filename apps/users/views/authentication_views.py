import logging
from typing import Any

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.users.services.services import AuthenticationService

logger = logging.getLogger(__name__)


class UserSignUpView(APIView):
    """사용자 회원가입 API

    새로운 사용자를 등록하는 엔드포인트입니다.
    이메일 인증이 완료된 사용자만 회원가입이 가능합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """회원가입 처리

        Args:
            request: HTTP 요청 객체
                - email (str): 사용자 이메일
                - password (str): 비밀번호
                - username (str): 사용자명
                - role (str): 사용자 역할 (user/admin)
                - joined_type (str): 가입 유형 (normal/kakao/naver/google)
                - agreed_policy (bool): 약관 동의 여부

        Returns:
            APIResponse:
                - 201: 회원가입 성공 시 사용자 정보 반환
                - 400: 잘못된 입력 데이터 또는 이메일 중복
                - 500: 서버 오류
        """
        try:
            user_data = AuthenticationService.signup(request.data)
            return APIResponse.created(
                message="회원가입이 완료되었습니다.", data=user_data
            )
        except ValueError as e:
            return APIResponse.from_exception(
                e, message="회원가입에 실패했습니다.", log_error=False
            )
        except Exception as e:
            return APIResponse.from_exception(
                e, message="회원가입 중 오류가 발생했습니다."
            )


class UserLoginView(APIView):
    """사용자 로그인 API

    이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.
    토큰은 HttpOnly 쿠키로 설정됩니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """로그인 처리

        Args:
            request: HTTP 요청 객체
                - email (str): 사용자 이메일
                - password (str): 비밀번호

        Returns:
            APIResponse:
                - 200: 로그인 성공, 쿠키로 access_token과 refresh_token 설정
                - 400: 잘못된 이메일 또는 비밀번호
                - 500: 서버 오류
        """
        try:
            user_data, access_token, refresh_token = AuthenticationService.login(
                request.data
            )

            response = APIResponse.success(
                message="로그인에 성공했습니다.", data=user_data
            )

            # 쿠키 설정
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                secure=not settings.DEBUG,
                samesite="Lax",
            )
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                secure=not settings.DEBUG,
                samesite="Lax",
            )

            return response
        except ValueError as e:
            return APIResponse.from_exception(
                e, message="로그인에 실패했습니다.", log_error=False
            )
        except Exception as e:
            return APIResponse.from_exception(
                e, message="로그인 중 오류가 발생했습니다."
            )


class UserRefreshTokenView(APIView):
    """토큰 갱신 API

    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.
    액세스 토큰이 만료되었을 때 사용합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """토큰 갱신 처리

        Args:
            request: HTTP 요청 객체 (쿠키에서 refresh_token 읽음)

        Returns:
            APIResponse:
                - 200: 토큰 갱신 성공, 새로운 토큰들을 쿠키로 설정
                - 400: 리프레시 토큰 없음 또는 만료
                - 500: 서버 오류
        """
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if not refresh_token:
                return APIResponse.bad_request(message="리프레시 토큰이 필요합니다.")

            access_token, new_refresh_token = AuthenticationService.refresh_token(
                refresh_token
            )

            response = APIResponse.success(message="토큰이 갱신되었습니다.")

            # 쿠키 설정
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                secure=not settings.DEBUG,
                samesite="Lax",
            )
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                secure=not settings.DEBUG,
                samesite="Lax",
            )

            return response
        except ValueError as e:
            return APIResponse.from_exception(
                e, message="토큰 갱신에 실패했습니다.", log_error=False
            )
        except Exception as e:
            return APIResponse.from_exception(
                e, message="토큰 갱신 중 오류가 발생했습니다."
            )


class UserLogoutView(APIView):
    """사용자 로그아웃 API

    로그아웃하고 토큰을 무효화합니다.
    블랙리스트 기능이 활성화된 경우 토큰을 블랙리스트에 추가합니다.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Any) -> APIResponse:
        """로그아웃 처리

        Args:
            request: HTTP 요청 객체 (쿠키에서 refresh_token 읽음)

        Returns:
            APIResponse:
                - 200: 로그아웃 성공, 쿠키 삭제
                - 400: 리프레시 토큰 없음
                - 500: 서버 오류
        """
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if not refresh_token:
                return APIResponse.bad_request(message="리프레시 토큰이 필요합니다.")

            AuthenticationService.logout(refresh_token)

            response = APIResponse.success(message="로그아웃되었습니다.")

            # 쿠키 삭제
            response.delete_cookie("refresh_token")
            response.delete_cookie("access_token")

            return response
        except ValueError as e:
            return APIResponse.from_exception(
                e, message="로그아웃에 실패했습니다.", log_error=False
            )
        except Exception as e:
            return APIResponse.from_exception(
                e, message="로그아웃 중 오류가 발생했습니다."
            )


class PasswordResetView(APIView):
    """비밀번호 재설정 API (이메일 인증 후)

    비밀번호 찾기에서 이메일 인증이 완료된 후 새 비밀번호를 설정합니다.
    PasswordResetEmailCodeView로 인증번호를 받고,
    VerifyPasswordResetCodeView로 인증을 완료한 후 사용합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """이메일 인증 후 비밀번호 재설정

        Args:
            request: HTTP 요청 객체
                - email (str): 인증 완료된 이메일
                - password (str): 새 비밀번호
                - confirm_password (str): 비밀번호 확인

        Returns:
            APIResponse:
                - 200: 비밀번호 변경 성공
                - 400: 이메일 인증 필요 또는 비밀번호 불일치
                - 500: 서버 오류
        """
        try:
            email = request.data.get("email")
            password = request.data.get("password")
            confirm_password = request.data.get("confirm_password")

            if not email or not password or not confirm_password:
                return APIResponse.bad_request(
                    message="이메일, 비밀번호, 비밀번호 확인을 모두 입력해주세요."
                )

            if password != confirm_password:
                return APIResponse.bad_request(message="비밀번호가 일치하지 않습니다.")

            # 비밀번호 유효성 검증
            import re
            
            if len(password) < 8:
                return APIResponse.bad_request(message="비밀번호는 8자 이상이어야 합니다.")
            
            if len(password) > 50:
                return APIResponse.bad_request(message="비밀번호는 50자를 초과할 수 없습니다.")
            
            if ' ' in password:
                return APIResponse.bad_request(message="비밀번호에는 공백이 포함될 수 없습니다.")
            
            if not re.search(r'[a-zA-Z]', password):
                return APIResponse.bad_request(message="비밀번호에는 영문자가 포함되어야 합니다.")
            
            if not re.search(r'[0-9]', password):
                return APIResponse.bad_request(message="비밀번호에는 숫자가 포함되어야 합니다.")
            
            if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?`~]', password):
                return APIResponse.bad_request(message="비밀번호에는 특수문자가 포함되어야 합니다.")
            
            if re.search(r'(.)\1{2,}', password):
                return APIResponse.bad_request(message="동일한 문자를 3개 이상 연속으로 사용할 수 없습니다.")

            AuthenticationService.reset_password_after_verification(email, password)
            return APIResponse.success(message="비밀번호가 성공적으로 변경되었습니다.")

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(
                e, message="비밀번호 변경 중 오류가 발생했습니다."
            )
