import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class CustomCookieAuthentication(JWTAuthentication):
    """
    커스텀 쿠키 기반 JWT 인증
    - access_token을 쿠키에서 읽어 인증 처리
    - 토큰이 없으면 None 반환 (인증하지 않음)
    - 토큰이 유효하지 않으면 None 반환하여 401 응답
    """

    def authenticate(self, request):
        # 쿠키에서 access_token 추출
        token = request.COOKIES.get("access_token")
        if not token:
            # 토큰이 없으면 인증하지 않음 (다른 인증 방식이나 익명 접근 허용)
            return None

        try:
            # 토큰 검증
            validated_token = self.get_validated_token(token)
            user = self.get_user(validated_token)
            return (user, validated_token)

        except TokenError as e:
            # 토큰이 만료되었거나 형식이 잘못된 경우
            logger.warning(f"Token validation failed: {str(e)}")
            return None

        except InvalidToken as e:
            # 토큰이 유효하지 않은 경우
            logger.warning(f"Invalid token provided: {str(e)}")
            return None

        except Exception as e:
            # 예상치 못한 오류
            logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
            return None


class DisableDBSessionForAPI:
    """
    세션 아예 저장 안되게 하는 미들웨어
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            request.session.save = lambda *args, **kwargs: None  # 세션 저장 무효화
        return self.get_response(request)
