import logging
import random
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import APIResponse

logger = logging.getLogger(__name__)


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
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return APIResponse.bad_request(message="이미 사용 중인 이메일입니다.")

        # 30초 이내 재전송 막기 위한 키 체크
        resend_flag_key = f"signup_resend_flag:{email}"
        if cache.get(resend_flag_key):
            return APIResponse.too_many_requests(
                message="인증번호는 30초에 한 번만 재전송할 수 있습니다."
            )

        code = f"{random.randint(100000, 999999)}"

        # 5분간 인증번호 저장 (회원가입용)
        cache.set(f"signup_verify_code:{email}", code, timeout=300)  # 5분 유효

        try:
            subject = "[GatherGrow] 회원가입 인증번호"
            from_email = settings.EMAIL_HOST_USER
            to = [email]

            html_content = render_to_string(
                "email_template.html", {"code": code, "purpose": "회원가입"}
            )

            msg = EmailMultiAlternatives(subject, "", from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # 재전송 제한용 플래그 30초 설정
            cache.set(resend_flag_key, True, timeout=30)

            return APIResponse.success(message="회원가입 인증번호가 전송되었습니다.")

        except Exception as e:
            return APIResponse.from_exception(
                e, message="인증번호 발송 중 오류가 발생했습니다."
            )


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

        # 캐시에서 회원가입용 인증번호 확인
        cached_code = cache.get(f"signup_verify_code:{email}")

        if not cached_code:
            return APIResponse.bad_request(
                message="인증번호가 만료되었습니다. 다시 요청해주세요."
            )

        if cached_code != code:
            return APIResponse.bad_request(message="인증번호가 일치하지 않습니다.")

        # 인증 성공시 캐시에서 삭제
        cache.delete(f"signup_verify_code:{email}")

        # 회원가입 인증 성공 표시 (5분간 유효)
        cache.set(f"signup_email_verified:{email}", True, timeout=300)

        return APIResponse.success(
            message="이메일 인증이 완료되었습니다. 회원가입을 계속해주세요."
        )


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

        # 30초 이내 재전송 막기
        resend_flag_key = f"password_reset_resend_flag:{email}"
        if cache.get(resend_flag_key):
            return APIResponse.too_many_requests(
                message="인증번호는 30초에 한 번만 재전송할 수 있습니다."
            )

        # 이메일이 존재하는지 확인 (보안상 결과는 노출하지 않음)
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user_exists = User.objects.filter(email=email).exists()

        if user_exists:
            code = f"{random.randint(100000, 999999)}"
            # 5분간 인증번호 저장 (비밀번호 찾기용)
            cache.set(f"password_reset_code:{email}", code, timeout=300)

            try:
                subject = "[GatherGrow] 비밀번호 재설정 인증번호"
                from_email = settings.EMAIL_HOST_USER
                to = [email]

                html_content = render_to_string(
                    "password_reset_email.html",
                    {"code": code, "purpose": "비밀번호 재설정"},
                )

                msg = EmailMultiAlternatives(subject, "", from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                logger.info(f"Password reset code sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")
        else:
            # 존재하지 않는 이메일이어도 로그만 남기고 동일한 응답
            logger.info(f"Password reset requested for non-existent email: {email}")

        # 재전송 제한 설정 (이메일 존재 여부와 무관)
        cache.set(resend_flag_key, True, timeout=30)

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

        # 캐시에서 비밀번호 재설정용 인증번호 확인
        cached_code = cache.get(f"password_reset_code:{email}")

        if not cached_code:
            return APIResponse.bad_request(
                message="인증번호가 만료되었습니다. 다시 요청해주세요."
            )

        if cached_code != code:
            return APIResponse.bad_request(message="인증번호가 일치하지 않습니다.")

        # 인증 성공시 캐시에서 삭제
        cache.delete(f"password_reset_code:{email}")

        # 비밀번호 재설정 가능 상태 표시 (5분간 유효)
        cache.set(f"password_reset_verified:{email}", True, timeout=300)

        return APIResponse.success(
            message="이메일 인증이 완료되었습니다. 새 비밀번호를 설정해주세요."
        )
