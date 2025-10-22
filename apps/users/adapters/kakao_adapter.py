import logging
from typing import Any, Dict

import requests
from allauth.socialaccount.providers.kakao.views import KakaoOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from django.conf import settings

logger = logging.getLogger(__name__)


class CustomKakaoOAuth2Adapter(KakaoOAuth2Adapter):
    """카카오 OAuth2 커스텀 어댑터

    Client Secret을 사용하는 카카오 OAuth2 인증을 처리합니다.
    """

    def get_access_token(self, request, code):
        """인증 코드를 액세스 토큰으로 교환 (Client Secret 포함)"""
        url = "https://kauth.kakao.com/oauth/token"

        # Client Secret 포함한 요청 데이터
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["CLIENT_ID"],
            "client_secret": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["SECRET_KEY"],
            "redirect_uri": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["REDIRECT_URI"],
            "code": code,
        }

        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()

            if "error" in token_data:
                error_msg = token_data.get("error_description", token_data["error"])
                logger.error(f"카카오 토큰 교환 실패: {error_msg}")
                raise OAuth2Error(f"카카오 인증 실패: {error_msg}")

            return token_data

        except requests.RequestException as e:
            logger.error(f"카카오 API 요청 실패: {e}")
            raise OAuth2Error(f"카카오 서버 연결 실패: {str(e)}")

    def complete_login(self, request, app, token, **kwargs):
        """카카오 로그인 완료 처리

        토큰을 사용하여 사용자 정보를 가져옵니다.
        """
        try:
            return super().complete_login(request, app, token, **kwargs)
        except Exception as e:
            logger.error(f"카카오 로그인 실패: {e}")
            raise
