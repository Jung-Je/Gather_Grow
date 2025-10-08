import logging

import requests
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.naver.views import NaverOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings

from apps.common.responses import APIResponse
from apps.users.adapters.kakao_adapter import CustomKakaoOAuth2Adapter
from apps.users.adapters.oauth_client import CustomOAuth2Client

logger = logging.getLogger(__name__)


class BaseSocialLoginView(SocialLoginView):
    """소셜 로그인 기본 클래스

    모든 소셜 로그인의 공통 기능을 제공합니다.
    토큰을 쿠키로 설정하고 통일된 응답 형식을 제공합니다.
    """

    adapter_class = None
    client_class = None
    callback_url = None

    def format_response(self, response):
        """응답을 통일된 형식으로 변환

        Args:
            response: 원본 응답 객체

        Returns:
            APIResponse: 통일된 형식의 응답
        """
        if response.status_code == 200:
            # 쿠키 설정
            access_token = response.data.get("access_token")
            refresh_token = response.data.get("refresh_token")

            # 사용자 정보 추출
            user_data = response.data.get("user", {})

            # 통일된 응답 형식으로 새 Response 생성
            formatted_response = APIResponse.success(
                message="소셜 로그인에 성공했습니다.", data=user_data
            )

            # 쿠키 설정
            if access_token:
                formatted_response.set_cookie(
                    key="access_token",
                    value=access_token,
                    httponly=True,
                    max_age=settings.SIMPLE_JWT[
                        "ACCESS_TOKEN_LIFETIME"
                    ].total_seconds(),
                    secure=not settings.DEBUG,
                    samesite="Lax",
                )

            if refresh_token:
                formatted_response.set_cookie(
                    key="refresh_token",
                    value=refresh_token,
                    httponly=True,
                    max_age=settings.SIMPLE_JWT[
                        "REFRESH_TOKEN_LIFETIME"
                    ].total_seconds(),
                    secure=not settings.DEBUG,
                    samesite="Lax",
                )

            return formatted_response

        # 에러 응답
        error_data = response.data if hasattr(response, "data") else {}

        if response.status_code == 400:
            return APIResponse.bad_request(
                message="소셜 로그인에 실패했습니다.", data=error_data
            )
        elif response.status_code == 401:
            return APIResponse.unauthorized(
                message="소셜 로그인에 실패했습니다.", data=error_data
            )
        else:
            return APIResponse(
                message="소셜 로그인에 실패했습니다.",
                data=error_data,
                status_code=response.status_code,
            )

    def post(self, request, *args, **kwargs):
        """소셜 로그인 처리

        Args:
            request: HTTP 요청 객체
                - code (str): OAuth 인증 코드
                - access_token (str): 또는 소셜 플랫폼에서 받은 액세스 토큰

        Returns:
            APIResponse: 로그인 처리 결과
        """
        try:
            # code가 있으면 access_token으로 교환
            if 'code' in request.data and 'access_token' not in request.data:
                # code와 state를 함께 전달
                request.data['state'] = request.data.get('state', '')
                
            response = super().post(request, *args, **kwargs)
            return self.format_response(response)
        except ValueError as e:
            return APIResponse.from_exception(
                e, message="소셜 로그인에 실패했습니다.", log_error=False
            )
        except Exception as e:
            return APIResponse.from_exception(
                e, message="소셜 로그인 중 오류가 발생했습니다."
            )


class NaverLoginView(BaseSocialLoginView):
    """네이버 소셜 로그인 API

    네이버 OAuth2 인증을 통해 로그인합니다.
    """

    adapter_class = NaverOAuth2Adapter
    client_class = CustomOAuth2Client
    callback_url = settings.SOCIAL_AUTH_CONFIG["NAVER"]["REDIRECT_URI"]

    def post(self, request, *args, **kwargs):
        """네이버 로그인 처리

        Args:
            request: HTTP 요청 객체
                - access_token (str): 네이버에서 받은 액세스 토큰

        Returns:
            APIResponse:
                - 200: 로그인 성공, 쿠키로 JWT 토큰 설정
                - 400: 잘못된 토큰 또는 인증 실패
        """
        return super().post(request, *args, **kwargs)


class KakaoLoginView(BaseSocialLoginView):
    """카카오 소셜 로그인 API

    카카오 OAuth2 인증을 통해 로그인합니다.
    Client Secret을 사용하는 보안 강화 모드를 지원합니다.
    """

    adapter_class = CustomKakaoOAuth2Adapter
    client_class = CustomOAuth2Client
    callback_url = settings.SOCIAL_AUTH_CONFIG["KAKAO"]["REDIRECT_URI"]

    def post(self, request, *args, **kwargs):
        """카카오 로그인 처리

        Args:
            request: HTTP 요청 객체
                - code (str): 카카오에서 받은 인증 코드
                - access_token (str): 또는 카카오에서 받은 액세스 토큰

        Returns:
            APIResponse:
                - 200: 로그인 성공, 쿠키로 JWT 토큰 설정
                - 400: 잘못된 토큰 또는 인증 실패
        """
        # request.data가 QueryDict인 경우 dict로 변환
        data = dict(request.data) if hasattr(request.data, 'dict') else request.data
        
        # code를 받았을 경우 액세스 토큰으로 교환
        if isinstance(data, dict) and 'code' in data and 'access_token' not in data:
            token_url = "https://kauth.kakao.com/oauth/token"
            code = data.get('code')
            if isinstance(code, list):
                code = code[0]
                
            token_data = {
                "grant_type": "authorization_code",
                "client_id": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["CLIENT_ID"],
                "client_secret": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["SECRET_KEY"],
                "redirect_uri": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["REDIRECT_URI"],
                "code": code,
            }
            
            try:
                token_response = requests.post(token_url, data=token_data)
                
                # 에러 응답 상세 로깅
                if token_response.status_code != 200:
                    error_detail = token_response.json() if token_response.text else {}
                    logger.error(f"카카오 토큰 교환 실패: {token_response.status_code} - {error_detail}")
                    return APIResponse.bad_request(
                        message="카카오 인증 코드를 토큰으로 교환하는데 실패했습니다.",
                        data={
                            "error": f"{token_response.status_code} - {error_detail}",
                            "redirect_uri_used": settings.SOCIAL_AUTH_CONFIG["KAKAO"]["REDIRECT_URI"]
                        }
                    )
                    
                token_json = token_response.json()
                
                # 액세스 토큰을 request.data에 추가
                request.data['access_token'] = token_json.get('access_token')
                
            except Exception as e:
                logger.error(f"카카오 토큰 교환 실패: {e}")
                return APIResponse.bad_request(
                    message="카카오 인증 코드를 토큰으로 교환하는데 실패했습니다.",
                    data={"error": str(e)}
                )
                
        return super().post(request, *args, **kwargs)


class GoogleLoginView(BaseSocialLoginView):
    """구글 소셜 로그인 API

    구글 OAuth2 인증을 통해 로그인합니다.
    """

    adapter_class = GoogleOAuth2Adapter
    client_class = CustomOAuth2Client
    callback_url = settings.SOCIAL_AUTH_CONFIG["GOOGLE"]["REDIRECT_URI"]

    def post(self, request, *args, **kwargs):
        """구글 로그인 처리

        Args:
            request: HTTP 요청 객체
                - code (str): 구글에서 받은 인증 코드
                - access_token (str): 또는 구글에서 받은 액세스 토큰

        Returns:
            APIResponse:
                - 200: 로그인 성공, 쿠키로 JWT 토큰 설정
                - 400: 잘못된 토큰 또는 인증 실패
        """
        from rest_framework.request import Request
        from django.http import HttpRequest
        
        try:
            # request.data가 QueryDict인 경우 dict로 변환
            data = dict(request.data) if hasattr(request.data, 'dict') else request.data
            
            # code를 받았을 경우 액세스 토큰으로 교환
            if isinstance(data, dict) and 'code' in data and 'access_token' not in data:
                token_url = "https://oauth2.googleapis.com/token"
                code = data.get('code')
                if isinstance(code, list):
                    code = code[0]
                    
                token_data = {
                    "code": code,
                    "client_id": settings.SOCIAL_AUTH_CONFIG["GOOGLE"]["CLIENT_ID"],
                    "client_secret": settings.SOCIAL_AUTH_CONFIG["GOOGLE"]["SECRET_KEY"],
                    "redirect_uri": settings.SOCIAL_AUTH_CONFIG["GOOGLE"]["REDIRECT_URI"],
                    "grant_type": "authorization_code",
                }
                
                try:
                    token_response = requests.post(token_url, data=token_data)
                
                    # 에러 응답 상세 로깅
                    if token_response.status_code != 200:
                        error_detail = token_response.json() if token_response.text else {}
                        logger.error(f"구글 토큰 교환 실패: {token_response.status_code} - {error_detail}")
                        return APIResponse.bad_request(
                            message="구글 인증 코드를 토큰으로 교환하는데 실패했습니다.",
                            data={
                                "error": f"{token_response.status_code} - {error_detail}",
                                "redirect_uri_used": settings.SOCIAL_AUTH_CONFIG["GOOGLE"]["REDIRECT_URI"]
                            }
                        )
                        
                    token_json = token_response.json()
                    
                    # 기존 request의 _request를 사용하여 session 유지
                    new_request = request._request
                    
                    # DRF Request 객체 생성 (기존 request의 속성들 유지)
                    new_request = Request(new_request)
                    new_request._data = {
                        'access_token': token_json.get('access_token'),
                    }
                    if token_json.get('id_token'):
                        new_request._data['id_token'] = token_json.get('id_token')
                    new_request._full_data = new_request._data
                    
                    # authenticators와 기타 속성들 복사
                    new_request.authenticators = getattr(request, 'authenticators', None)
                    new_request.user = request.user
                    new_request.auth = getattr(request, 'auth', None)
                    
                    # 새로운 request로 super().post() 호출
                    return super().post(new_request, *args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"구글 토큰 교환 실패: {e}")
                    return APIResponse.bad_request(
                        message="구글 인증 코드를 토큰으로 교환하는데 실패했습니다.",
                        data={"error": str(e)}
                    )
                    
            # access_token이 이미 있는 경우 그대로 처리
            return super().post(request, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"구글 로그인 처리 중 오류: {e}", exc_info=True)
            return APIResponse.from_exception(
                e, message="소셜 로그인 중 오류가 발생했습니다."
            )
