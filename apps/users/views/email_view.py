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


class SendHtmlEmailCodeView(APIView):
    """이메일 인증번호 발송 API
    
    회원가입을 위한 6자리 인증번호를 이메일로 발송합니다.
    인증번호는 5분간 유효하며, 30초에 한 번만 재전송 가능합니다.
    """
    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """인증번호 발송 처리
        
        Args:
            request: HTTP 요청 객체
                - email (str): 인증받을 이메일 주소
        
        Returns:
            APIResponse:
                - 200: 인증번호 발송 성공
                - 400: 이메일 주소 누락
                - 429: 30초 재전송 제한
                - 500: 서버 오류
        """
        email = request.data.get("email")
        if not email:
            return APIResponse.bad_request(message="이메일은 필수입니다.")

        # 30초 이내 재전송 막기 위한 키 체크
        resend_flag_key = f"verify_code_resend_flag:{email}"
        if cache.get(resend_flag_key):
            return APIResponse.too_many_requests(message="인증번호는 30초에 한 번만 재전송할 수 있습니다.")

        code = f"{random.randint(100000, 999999)}"

        # 5분간 인증번호 저장
        cache.set(f"verify_code:{email}", code, timeout=300)  # 5분 유효

        try:
            subject = "[GatherGrow] 이메일 인증번호"
            from_email = settings.EMAIL_HOST_USER
            to = [email]

            html_content = render_to_string("template.html", {"code": code})

            msg = EmailMultiAlternatives(subject, "", from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # 재전송 제한용 플래그 30초 설정
            cache.set(resend_flag_key, True, timeout=30)

            return APIResponse.success(message="인증번호가 전송되었습니다.")

        except Exception as e:
            return APIResponse.from_exception(e, message="인증번호 발송 중 오류가 발생했습니다.")


class VerifyEmailCodeView(APIView):
    """이메일 인증번호 확인 API
    
    발송된 6자리 인증번호를 확인하여 이메일을 인증합니다.
    인증 성공 시 5분간 인증 상태가 유지됩니다.
    """
    permission_classes = [AllowAny]

    def post(self, request: Any) -> APIResponse:
        """인증번호 확인 처리
        
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

        # 캐시에서 인증번호 확인
        cached_code = cache.get(f"verify_code:{email}")

        if not cached_code:
            return APIResponse.bad_request(message="인증번호가 만료되었습니다. 다시 요청해주세요.")

        if cached_code != code:
            return APIResponse.bad_request(message="인증번호가 일치하지 않습니다.")

        # 인증 성공시 캐시에서 삭제
        cache.delete(f"verify_code:{email}")

        # 인증 성공 표시 (5분간 유효)
        cache.set(f"email_verified:{email}", True, timeout=300)

        return APIResponse.success(message="이메일 인증이 완료되었습니다.")
