import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class CustomCookieAuthentication(JWTAuthentication):
    """커스텀 쿠키 기반 JWT 인증

    쿠키에서 access_token을 읽어 JWT 인증을 처리합니다.
    - access_token을 쿠키에서 읽어 인증 처리
    - 토큰이 없으면 None 반환 (인증하지 않음)
    - 토큰이 유효하지 않으면 None 반환하여 401 응답
    """

    def authenticate(self, request):
        """쿠키에서 JWT 토큰을 추출하여 사용자를 인증합니다.

        Args:
            request (HttpRequest): HTTP 요청 객체

        Returns:
            tuple: (User, ValidatedToken) 튜플 또는 None
                - 인증 성공 시: (사용자 객체, 검증된 토큰)
                - 인증 실패 시: None
        """
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
    """API 요청에 대해 세션 저장을 비활성화하는 미들웨어

    /api/로 시작하는 경로에 대해 세션 저장을 무효화합니다.
    """

    def __init__(self, get_response):
        """미들웨어를 초기화합니다.

        Args:
            get_response (callable): Django view 또는 다음 미들웨어
        """
        self.get_response = get_response

    def __call__(self, request):
        """요청을 처리하고 API 경로의 경우 세션 저장을 비활성화합니다.

        Args:
            request (HttpRequest): HTTP 요청 객체

        Returns:
            HttpResponse: HTTP 응답 객체
        """
        if request.path.startswith("/api/"):
            request.session.save = lambda *args, **kwargs: None  # 세션 저장 무효화
        return self.get_response(request)
