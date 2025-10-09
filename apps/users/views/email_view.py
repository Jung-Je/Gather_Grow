import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.users.services.email_service import EmailVerificationService

logger = logging.getLogger(__name__)
User = get_user_model()


class SignUpEmailCodeView(APIView):
    """회원가입용 이메일 인증번호 발송 API

    회원가입을 위한 6자리 인증번호를 이메일로 발송합니다.
    인증번호는 5분간 유효하며, 30초에 한 번만 재전송 가능합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """회원가입 인증번호 발송 처리

        Args:
            request: HTTP 요청 객체
                - email (str): 인증받을 이메일 주소

        Returns:
            APIResponse:
                - 200: 인증번호 발송 성공
                - 400: 이메일 주소 누락 또는 이미 존재하는 이메일
                - 429: 30초 재전송 제한
                - 500: 서버 오류
        """
        email = request.data.get("email")
        if not email:
            return APIResponse.bad_request(message="이메일은 필수입니다.")

        # 이미 가입된 이메일인지 확인
        if User.objects.filter(email=email).exists():
            return APIResponse.bad_request(message="이미 사용 중인 이메일입니다.")

        # 인증번호 발송
        success, error_message = EmailVerificationService.send_verification_code(
            email=email, purpose="signup", subject="[GatherGrow] 회원가입 인증번호"
        )

        if success:
            return APIResponse.success(message="회원가입 인증번호가 전송되었습니다.")
        elif "30초" in (error_message or ""):
            return APIResponse.too_many_requests(message=error_message)
        else:
            return APIResponse.bad_request(message=error_message)


class VerifySignUpCodeView(APIView):
    """회원가입용 이메일 인증번호 확인 API

    회원가입을 위해 발송된 6자리 인증번호를 확인합니다.
    인증 성공 시 5분간 회원가입 가능 상태가 유지됩니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """회원가입 인증번호 확인 처리

        Args:
            request: HTTP 요청 객체
                - email (str): 인증할 이메일 주소
                - code (str): 6자리 인증번호

        Returns:
            APIResponse:
                - 200: 인증 성공
                - 400: 잘못된 인증번호 또는 만료된 인증번호
        """
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return APIResponse.bad_request(message="이메일과 인증번호는 필수입니다.")

        # 인증번호 확인
        success, error_message = EmailVerificationService.verify_code(
            email=email, code=code, purpose="signup"
        )

        if success:
            # signup_email_verified 키 설정 (기존 코드와의 호환성 유지)
            cache.set(f"signup_email_verified:{email}", True, timeout=300)

            return APIResponse.success(
                message="이메일 인증이 완료되었습니다. 회원가입을 계속해주세요."
            )
        else:
            return APIResponse.bad_request(message=error_message)


class PasswordResetEmailCodeView(APIView):
    """비밀번호 찾기용 이메일 인증번호 발송 API

    비밀번호를 잊어버린 경우 가입한 이메일로 인증번호를 발송합니다.
    인증번호는 5분간 유효하며, 30초에 한 번만 재전송 가능합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """비밀번호 찾기 인증번호 발송 처리

        Args:
            request: HTTP 요청 객체
                - email (str): 가입한 이메일 주소

        Returns:
            APIResponse:
                - 200: 인증번호 발송 완료 (보안상 이메일 존재 여부와 무관)
                - 400: 이메일 주소 누락
                - 429: 30초 재전송 제한
        """
        email = request.data.get("email")
        if not email:
            return APIResponse.bad_request(message="이메일을 입력해주세요.")

        # 이메일이 존재하는지 확인 (보안상 결과는 노출하지 않음)
        user_exists = User.objects.filter(email=email).exists()

        if user_exists:
            # 인증번호 발송
            success, error_message = EmailVerificationService.send_verification_code(
                email=email,
                purpose="password_reset",
                subject="[GatherGrow] 비밀번호 재설정 인증번호",
            )

            if not success and "30초" in (error_message or ""):
                return APIResponse.too_many_requests(message=error_message)
        else:
            # 존재하지 않는 이메일이어도 로그만 남기고 동일한 응답
            logger.info(f"Password reset requested for non-existent email: {email}")

        # 보안을 위해 이메일 존재 여부와 관계없이 동일한 응답
        return APIResponse.success(
            message="입력하신 이메일로 인증번호를 발송했습니다. 이메일을 확인해주세요."
        )


class VerifyPasswordResetCodeView(APIView):
    """비밀번호 찾기용 이메일 인증번호 확인 API

    비밀번호 재설정을 위해 발송된 인증번호를 확인합니다.
    인증 성공 시 5분간 비밀번호 재설정 가능 상태가 됩니다.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """비밀번호 찾기 인증번호 확인 처리

        Args:
            request: HTTP 요청 객체
                - email (str): 이메일 주소
                - code (str): 6자리 인증번호

        Returns:
            APIResponse:
                - 200: 인증 성공
                - 400: 잘못된 인증번호 또는 만료
        """
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return APIResponse.bad_request(message="이메일과 인증번호를 입력해주세요.")

        # 인증번호 확인
        success, error_message = EmailVerificationService.verify_code(
            email=email, code=code, purpose="password_reset"
        )

        if success:
            # password_reset_verified 키 설정 (기존 코드와의 호환성 유지)
            cache.set(f"password_reset_verified:{email}", True, timeout=300)

            return APIResponse.success(
                message="이메일 인증이 완료되었습니다. 새 비밀번호를 설정해주세요."
            )
        else:
            return APIResponse.bad_request(message=error_message)
