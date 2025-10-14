from functools import wraps
from typing import Callable

from django.core.cache import cache
from django.utils import timezone

from apps.common.responses import APIResponse


def rate_limit(key_prefix: str, rate: str, method: str = "POST") -> Callable:
    """Rate limiting 데코레이터

    Args:
        key_prefix: 캐시 키 prefix (예: 'login', 'email_send')
        rate: 제한 규칙 (예: '5/m', '10/h', '100/d')
        method: HTTP 메서드 (기본값: POST)

    Returns:
        데코레이터 함수

    Usage:
        @rate_limit(key_prefix='login', rate='5/m')
        def post(self, request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # 해당 메서드가 아니면 rate limiting 적용 안함
            if request.method != method:
                return func(self, request, *args, **kwargs)

            # rate 파싱 (예: '5/m' -> 5회, 60초)
            try:
                limit, period = rate.split("/")
                limit = int(limit)

                if period == "m":  # minute
                    seconds = 60
                elif period == "h":  # hour
                    seconds = 3600
                elif period == "d":  # day
                    seconds = 86400
                else:
                    seconds = 60  # 기본값 1분
            except (ValueError, AttributeError):
                # 파싱 실패시 기본값
                limit = 10
                seconds = 60

            # IP 주소 또는 사용자 식별
            if hasattr(request, "user") and request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if x_forwarded_for:
                    ip = x_forwarded_for.split(",")[0]
                else:
                    ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
                identifier = f"ip_{ip}"

            # 캐시 키 생성
            cache_key = f"rate_limit:{key_prefix}:{identifier}"

            # 현재 요청 횟수 확인
            attempts = cache.get(cache_key, [])
            now = timezone.now()

            # 시간이 지난 요청 제거
            cutoff_time = now - timezone.timedelta(seconds=seconds)
            attempts = [t for t in attempts if t > cutoff_time]

            # 제한 확인
            if len(attempts) >= limit:
                remaining_time = int((attempts[0] + timezone.timedelta(seconds=seconds) - now).total_seconds())
                return APIResponse.too_many_requests(
                    message=f"너무 많은 요청입니다. {remaining_time}초 후에 다시 시도해주세요."
                )

            # 새 요청 추가
            attempts.append(now)
            cache.set(cache_key, attempts, seconds)

            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def login_rate_limit(func: Callable) -> Callable:
    """로그인 전용 rate limiting (5회/분)"""
    return rate_limit(key_prefix="login", rate="5/m")(func)


def email_rate_limit(func: Callable) -> Callable:
    """이메일 발송 전용 rate limiting (3회/시간)"""
    return rate_limit(key_prefix="email", rate="3/h")(func)


def password_reset_rate_limit(func: Callable) -> Callable:
    """비밀번호 재설정 전용 rate limiting (5회/시간)"""
    return rate_limit(key_prefix="password_reset", rate="5/h")(func)
