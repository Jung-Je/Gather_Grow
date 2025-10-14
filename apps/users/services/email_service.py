import logging
import random
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """이메일 인증 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    CACHE_TIMEOUT = 300  # 5분
    RESEND_TIMEOUT = 30  # 30초

    @staticmethod
    def generate_code() -> str:
        """6자리 인증번호 생성"""
        return f"{random.randint(100000, 999999)}"

    @staticmethod
    def can_resend_email(email: str, purpose: str) -> bool:
        """이메일 재전송 가능 여부 확인

        Args:
            email: 이메일 주소
            purpose: 용도 ('signup' 또는 'password_reset')

        Returns:
            재전송 가능 여부
        """
        resend_flag_key = f"{purpose}_resend_flag:{email}"
        return not cache.get(resend_flag_key)

    @staticmethod
    def send_verification_code(
        email: str, purpose: str, subject: str, template_context: dict = None
    ) -> tuple[bool, Optional[str]]:
        """인증번호 이메일 발송

        Args:
            email: 수신자 이메일
            purpose: 용도 ('signup' 또는 'password_reset')
            subject: 이메일 제목
            template_context: 템플릿 추가 컨텍스트

        Returns:
            (성공 여부, 에러 메시지)
        """
        # 재전송 제한 확인
        if not EmailVerificationService.can_resend_email(email, purpose):
            return (
                False,
                f"인증번호는 {EmailVerificationService.RESEND_TIMEOUT}초에 한 번만 재전송할 수 있습니다.",
            )

        # 인증번호 생성
        code = EmailVerificationService.generate_code()

        # 캐시에 저장
        code_key = f"{purpose}_verify_code:{email}"
        cache.set(code_key, code, timeout=EmailVerificationService.CACHE_TIMEOUT)

        # 이메일 발송
        try:
            from_email = settings.EMAIL_HOST_USER
            to = [email]

            # 템플릿 컨텍스트 준비
            context = template_context or {}
            context["code"] = code

            # 템플릿 선택
            if purpose == "signup":
                template_name = "email_template.html"
                context["purpose"] = "회원가입"
            else:  # password_reset
                template_name = "password_reset_email.html"
                context["purpose"] = "비밀번호 재설정"

            html_content = render_to_string(template_name, context)

            msg = EmailMultiAlternatives(subject, "", from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # 재전송 제한 플래그 설정
            resend_flag_key = f"{purpose}_resend_flag:{email}"
            cache.set(resend_flag_key, True, timeout=EmailVerificationService.RESEND_TIMEOUT)

            logger.info(f"Verification code sent to {email} for {purpose}")
            return True, None

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            return False, "인증번호 발송 중 오류가 발생했습니다."

    @staticmethod
    def verify_code(email: str, code: str, purpose: str) -> tuple[bool, Optional[str]]:
        """인증번호 확인

        Args:
            email: 이메일 주소
            code: 인증번호
            purpose: 용도 ('signup' 또는 'password_reset')

        Returns:
            (성공 여부, 에러 메시지)
        """
        # 캐시에서 인증번호 확인
        code_key = f"{purpose}_verify_code:{email}"
        cached_code = cache.get(code_key)

        if not cached_code:
            return False, "인증번호가 만료되었습니다. 다시 요청해주세요."

        if cached_code != code:
            return False, "인증번호가 일치하지 않습니다."

        # 인증 성공시 캐시에서 삭제
        cache.delete(code_key)

        # 인증 성공 표시 (5분간 유효)
        verified_key = f"{purpose}_verified:{email}"
        cache.set(verified_key, True, timeout=EmailVerificationService.CACHE_TIMEOUT)

        return True, None

    @staticmethod
    def is_email_verified(email: str, purpose: str) -> bool:
        """이메일 인증 완료 여부 확인

        Args:
            email: 이메일 주소
            purpose: 용도 ('signup' 또는 'password_reset')

        Returns:
            인증 완료 여부
        """
        verified_key = f"{purpose}_verified:{email}"
        return bool(cache.get(verified_key))

    @staticmethod
    def clear_verification_status(email: str, purpose: str) -> None:
        """이메일 인증 상태 삭제

        Args:
            email: 이메일 주소
            purpose: 용도 ('signup' 또는 'password_reset')
        """
        verified_key = f"{purpose}_verified:{email}"
        cache.delete(verified_key)
